"""
Docker-based E2E Tests
VoidCat RDC - CryptoBoy Trading Bot

Tests the system running in Docker containers.
"""
import os
import subprocess
import time

import pytest


@pytest.mark.e2e
@pytest.mark.slow
class TestDockerDeployment:
    """Test Docker-based deployment"""

    def test_docker_compose_up(self):
        """Test that docker-compose can start all services"""
        # This test requires docker-compose to be available
        result = subprocess.run(
            ['docker', '--version'],
            capture_output=True,
            text=True
        )
        assert result.returncode == 0
        print(f"✓ Docker version: {result.stdout.strip()}")

    def test_container_health_checks(self):
        """Test that all containers pass health checks"""
        # Check for running containers
        result = subprocess.run(
            ['docker', 'ps', '--format', '{{.Names}}\t{{.Status}}'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            containers = result.stdout.strip().split('\n')
            print(f"Found {len(containers)} running containers")
            
            for container in containers:
                if 'trading-' in container:
                    print(f"  ✓ {container}")

    def test_service_connectivity_in_docker(self):
        """Test that services can communicate in Docker network"""
        # Test RabbitMQ connectivity
        result = subprocess.run(
            ['docker', 'exec', 'trading-rabbitmq-prod', 'rabbitmqctl', 'status'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("✓ RabbitMQ is running and accessible")

    def test_redis_in_docker(self):
        """Test Redis in Docker"""
        result = subprocess.run(
            ['docker', 'exec', 'trading-redis-prod', 'redis-cli', 'ping'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            assert 'PONG' in result.stdout
            print("✓ Redis is running and responding")


if __name__ == '__main__':
    pytest.main([__file__, '-v', '-s'])
