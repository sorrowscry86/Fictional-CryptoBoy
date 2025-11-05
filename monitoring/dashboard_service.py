#!/usr/bin/env python3
"""
VoidCat RDC - CryptoBoy Trading System
Real-Time Monitoring Dashboard Service
Author: Wykeve Freeman (Sorrow Eternal)

Collects metrics from all 8 services and exposes via WebSocket for real-time dashboard.
NO SIMULATIONS LAW: All metrics from real system state only.
"""

import asyncio
import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
import docker
import redis
from aiohttp import web

# Ensure we can import project-local modules whether run as module or script
try:
    from services.common.logging_config import setup_logging

    project_root = Path(__file__).parent.parent
except ImportError:  # noqa: E402
    import sys  # noqa: E402

    project_root = Path(__file__).parent.parent  # noqa: E402
    sys.path.insert(0, str(project_root))  # noqa: E402
    from services.common.logging_config import setup_logging  # noqa: E402

logger = setup_logging("dashboard-service")


class DashboardMetricsCollector:
    """Collects real-time metrics from all CryptoBoy services"""

    SERVICES = [
        "trading-rabbitmq-prod",
        "trading-redis-prod",
        "trading-bot-ollama-prod",
        "trading-market-streamer",
        "trading-news-poller",
        "trading-sentiment-processor",
        "trading-signal-cacher",
        "trading-bot-app",
    ]

    def __init__(self):
        """Initialize metrics collector"""
        self.redis_client = None
        self.docker_client = None
        try:
            self.docker_client = docker.from_env()
            logger.info("Connected to Docker daemon")
        except Exception as e:
            logger.error(f"Failed to connect to Docker: {e}")

        self.websocket_clients = set()
        self.metrics_cache = {}
        self.alert_thresholds = {
            "sentiment_stale_hours": 4,
            "queue_backlog_threshold": 1000,
            "high_latency_ms": 5000,
            "service_restart_count": 3,
        }

        # Initialize Redis connection
        self._connect_redis()

        logger.info("Dashboard Metrics Collector initialized")

    def _connect_redis(self):
        """Connect to Redis cache"""
        try:
            self.redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "redis"),
                port=int(os.getenv("REDIS_PORT", 6379)),
                decode_responses=True,
                socket_connect_timeout=5,
            )
            self.redis_client.ping()
            logger.info("Connected to Redis for metrics collection")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None

    async def collect_docker_stats(self) -> Dict[str, Any]:
        """Collect Docker container statistics using Docker SDK"""
        try:
            if not self.docker_client:
                return {"error": "Docker client not connected"}

            # Get all containers
            all_containers = self.docker_client.containers.list(all=True)

            containers = {}
            for container in all_containers:
                name = container.name
                if name in self.SERVICES:
                    # Get container status
                    status = container.status  # running, exited, etc.
                    health_status = "none"

                    # Try to get health check status
                    if container.attrs.get("State", {}).get("Health"):
                        health_status = container.attrs["State"]["Health"].get("Status", "none")

                    containers[name] = {
                        "state": status,
                        "status": container.attrs.get("State", {}).get("Status", ""),
                        "health": health_status,
                        "running": status == "running",
                        "ports": str(container.ports) if container.ports else "",
                    }

            # Calculate overall health
            running_count = sum(1 for c in containers.values() if c.get("running", False))
            total_count = len(self.SERVICES)
            health_percentage = (running_count / total_count * 100) if total_count > 0 else 0

            return {
                "containers": containers,
                "summary": {
                    "running": running_count,
                    "total": total_count,
                    "health_percentage": round(health_percentage, 1),
                },
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to collect Docker stats: {e}")
            return {"error": str(e)}

    async def collect_redis_metrics(self) -> Dict[str, Any]:
        """Collect Redis cache metrics"""
        if not self.redis_client:
            return {"error": "Redis not connected"}

        try:
            # Get cache size
            db_size = self.redis_client.dbsize()

            # Get sentiment data for all pairs
            sentiment_data = {}
            pairs = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "XRP/USDT", "ADA/USDT"]

            for pair in pairs:
                key = f"sentiment:{pair}"
                data = self.redis_client.hgetall(key)

                if data:
                    score = float(data.get("score", 0.0))
                    timestamp_str = data.get("timestamp", "")

                    # Calculate age (handle both naive and timezone-aware datetimes)
                    try:
                        ts = datetime.fromisoformat(timestamp_str)
                        # Handle both naive and aware timestamps
                        if ts.tzinfo is None:
                            now = datetime.now()
                        else:
                            now = datetime.now(ts.tzinfo)
                        age_hours = (now - ts).total_seconds() / 3600
                    except (ValueError, TypeError):
                        age_hours = 999

                    sentiment_data[pair] = {
                        "score": score,
                        "timestamp": timestamp_str,
                        "age_hours": round(age_hours, 2),
                        "stale": age_hours > self.alert_thresholds["sentiment_stale_hours"],
                        "headline": data.get("headline", "")[:100],
                    }

            return {
                "db_size": db_size,
                "sentiment_cache": sentiment_data,
                "connected": True,
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to collect Redis metrics: {e}")
            return {"error": str(e), "connected": False}

    async def collect_rabbitmq_metrics(self) -> Dict[str, Any]:
        """Collect RabbitMQ queue metrics using Docker SDK"""
        try:
            if not self.docker_client:
                return {"error": "Docker client not connected"}

            # Get RabbitMQ container
            try:
                container = self.docker_client.containers.get("trading-rabbitmq-prod")
            except docker.errors.NotFound:
                return {"error": "RabbitMQ container not found"}

            # Execute rabbitmqctl command
            exit_code, output = container.exec_run(
                ["rabbitmqctl", "list_queues", "name", "messages", "messages_ready", "messages_unacknowledged"],
                demux=False,
            )

            if exit_code != 0:
                logger.error(f"RabbitMQ command failed with exit code {exit_code}")
                return {"error": "Failed to get queue stats"}

            queues = {}
            lines = output.decode("utf-8").strip().split("\n")

            for line in lines:
                parts = line.split()
                # Skip header lines and ensure we have numeric data
                if len(parts) >= 4 and parts[1].isdigit():
                    queue_name = parts[0]
                    total_msgs = int(parts[1])
                    ready = int(parts[2])
                    unacked = int(parts[3])

                    queues[queue_name] = {
                        "total_messages": total_msgs,
                        "ready": ready,
                        "unacknowledged": unacked,
                        "backlog": total_msgs > self.alert_thresholds["queue_backlog_threshold"],
                    }

            return {"queues": queues, "connected": True, "timestamp": datetime.utcnow().isoformat()}

        except Exception as e:
            logger.error(f"Failed to collect RabbitMQ metrics: {e}")
            return {"error": str(e), "connected": False}

    async def collect_trading_metrics(self) -> Dict[str, Any]:
        """Collect trading bot metrics from SQLite database"""
        try:
            db_path = project_root / "tradesv3.dryrun.sqlite"

            if not db_path.exists():
                return {"error": "Database not found"}

            conn = sqlite3.connect(str(db_path))
            cursor = conn.cursor()

            # Get total trades
            cursor.execute("SELECT COUNT(*) FROM trades")
            total_trades = cursor.fetchone()[0]

            # Get recent trades (last 24 hours)
            cursor.execute(
                """
                SELECT COUNT(*) FROM trades
                WHERE open_date >= datetime('now', '-1 day')
            """
            )
            recent_trades = cursor.fetchone()[0]

            # Get open trades
            cursor.execute("SELECT COUNT(*) FROM trades WHERE is_open = 1")
            open_trades = cursor.fetchone()[0]

            # Get trade statistics
            cursor.execute(
                """
                SELECT
                    COUNT(*) as count,
                    AVG(close_profit) as avg_profit,
                    SUM(CASE WHEN close_profit > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN close_profit < 0 THEN 1 ELSE 0 END) as losses
                FROM trades
                WHERE is_open = 0
            """
            )
            stats = cursor.fetchone()

            conn.close()

            closed_trades = stats[0] if stats[0] else 0
            avg_profit = stats[1] if stats[1] else 0.0
            wins = stats[2] if stats[2] else 0
            losses = stats[3] if stats[3] else 0
            win_rate = (wins / closed_trades * 100) if closed_trades > 0 else 0.0

            return {
                "total_trades": total_trades,
                "recent_trades_24h": recent_trades,
                "open_trades": open_trades,
                "closed_trades": closed_trades,
                "average_profit_pct": round(avg_profit, 2),
                "wins": wins,
                "losses": losses,
                "win_rate_pct": round(win_rate, 1),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            logger.error(f"Failed to collect trading metrics: {e}")
            return {"error": str(e)}

    async def collect_all_metrics(self) -> Dict[str, Any]:
        """Collect all metrics from all sources"""
        logger.debug("Collecting all metrics...")

        metrics = {
            "docker": await self.collect_docker_stats(),
            "redis": await self.collect_redis_metrics(),
            "rabbitmq": await self.collect_rabbitmq_metrics(),
            "trading": await self.collect_trading_metrics(),
            "collection_timestamp": datetime.utcnow().isoformat(),
        }

        # Generate alerts
        metrics["alerts"] = self._generate_alerts(metrics)

        # Cache metrics
        self.metrics_cache = metrics

        return metrics

    def _generate_alerts(self, metrics: Dict[str, Any]) -> List[Dict[str, str]]:
        """Generate alerts based on metrics"""
        alerts = []

        # Check Docker service health
        docker_data = metrics.get("docker", {})
        if "summary" in docker_data:
            health_pct = docker_data["summary"].get("health_percentage", 0)
            if health_pct < 100:
                alerts.append(
                    {
                        "level": "warning" if health_pct >= 80 else "critical",
                        "service": "docker",
                        "message": f"Service health at {health_pct}% - some services not running",
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )

        # Check stale sentiment
        redis_data = metrics.get("redis", {})
        if "sentiment_cache" in redis_data:
            for pair, data in redis_data["sentiment_cache"].items():
                if data.get("stale", False):
                    alerts.append(
                        {
                            "level": "warning",
                            "service": "redis",
                            "message": f"Stale sentiment for {pair} (age: {data['age_hours']:.1f}h)",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

        # Check RabbitMQ queue backlog
        rabbitmq_data = metrics.get("rabbitmq", {})
        if "queues" in rabbitmq_data:
            for queue_name, queue_data in rabbitmq_data["queues"].items():
                if queue_data.get("backlog", False):
                    alerts.append(
                        {
                            "level": "critical",
                            "service": "rabbitmq",
                            "message": f"Queue '{queue_name}' has {queue_data['total_messages']} messages (backlog)",
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    )

        return alerts

    async def broadcast_to_clients(self, message: Dict[str, Any]):
        """Broadcast metrics to all connected WebSocket clients"""
        if not self.websocket_clients:
            return

        dead_clients = set()
        message_json = json.dumps(message)

        for ws in self.websocket_clients:
            try:
                await ws.send_str(message_json)
            except Exception as e:
                logger.error(f"Failed to send to client: {e}")
                dead_clients.add(ws)

        # Remove dead clients
        self.websocket_clients -= dead_clients


class DashboardServer:
    """WebSocket server for real-time dashboard"""

    def __init__(self, collector: DashboardMetricsCollector, port: int = 8081):
        """Initialize dashboard server"""
        self.collector = collector
        self.port = port
        self.app = web.Application()
        self.setup_routes()

        logger.info(f"Dashboard server initialized on port {port}")

    def setup_routes(self):
        """Setup HTTP routes"""
        self.app.router.add_get("/", self.handle_index)
        self.app.router.add_get("/ws", self.handle_websocket)
        self.app.router.add_get("/metrics", self.handle_metrics)

    async def handle_index(self, request):
        """Serve dashboard HTML"""
        html_path = project_root / "monitoring" / "dashboard.html"

        if not html_path.exists():
            return web.Response(text="Dashboard HTML not found", status=404)

        with open(html_path, "r") as f:
            html = f.read()

        return web.Response(text=html, content_type="text/html")

    async def handle_metrics(self, request):
        """REST endpoint for current metrics"""
        metrics = await self.collector.collect_all_metrics()
        return web.json_response(metrics)

    async def handle_websocket(self, request):
        """WebSocket handler for real-time updates"""
        ws = web.WebSocketResponse()
        await ws.prepare(request)

        self.collector.websocket_clients.add(ws)
        logger.info(f"WebSocket client connected (total: {len(self.collector.websocket_clients)})")

        try:
            # Send initial metrics
            metrics = await self.collector.collect_all_metrics()
            await ws.send_json(metrics)

            # Keep connection alive
            async for msg in ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    if msg.data == "close":
                        await ws.close()
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
        finally:
            self.collector.websocket_clients.discard(ws)
            logger.info(f"WebSocket client disconnected (remaining: {len(self.collector.websocket_clients)})")

        return ws

    async def metrics_broadcast_loop(self):
        """Background task to broadcast metrics every 5 seconds"""
        while True:
            try:
                await asyncio.sleep(5)

                if self.collector.websocket_clients:
                    metrics = await self.collector.collect_all_metrics()
                    await self.collector.broadcast_to_clients(metrics)

            except Exception as e:
                logger.error(f"Error in metrics broadcast loop: {e}")

    async def start_background_tasks(self, app):
        """Start background tasks"""
        app["metrics_broadcast"] = asyncio.create_task(self.metrics_broadcast_loop())

    async def cleanup_background_tasks(self, app):
        """Cleanup background tasks"""
        app["metrics_broadcast"].cancel()
        await app["metrics_broadcast"]

    def run(self):
        """Run the dashboard server"""
        self.app.on_startup.append(self.start_background_tasks)
        self.app.on_cleanup.append(self.cleanup_background_tasks)

        logger.info(f"Starting dashboard server on http://0.0.0.0:{self.port}")
        logger.info(f"Dashboard will be available at http://localhost:{self.port}")

        web.run_app(self.app, host="0.0.0.0", port=self.port)


def main():
    """Main entry point"""
    logger.info("=== VoidCat RDC - CryptoBoy Monitoring Dashboard ===")
    logger.info("NO SIMULATIONS LAW: All metrics from real system state")

    # Initialize collector
    collector = DashboardMetricsCollector()

    # Initialize server
    server = DashboardServer(collector, port=8081)

    # Run server
    server.run()


if __name__ == "__main__":
    main()
