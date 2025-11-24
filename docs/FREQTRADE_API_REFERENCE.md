# Freqtrade REST API Reference
**VoidCat RDC - CryptoBoy Trading System**

This document provides comprehensive documentation for Freqtrade REST API endpoints used by the CryptoBoy monitoring dashboard and manual trade controller.

---

## Table of Contents
1. [API Configuration](#api-configuration)
2. [Authentication](#authentication)
3. [Core Endpoints](#core-endpoints)
4. [Manual Trade Control](#manual-trade-control)
5. [Status & Monitoring](#status--monitoring)
6. [Error Handling](#error-handling)

---

## API Configuration

### Server Settings

**Default Configuration** (`config/live_config.json`):
```json
{
    "api_server": {
        "enabled": true,
        "listen_ip_address": "0.0.0.0",
        "listen_port": 8080,
        "verbosity": "info",
        "enable_openapi": true,
        "jwt_secret_key": "changeme",
        "CORS_origins": [],
        "username": "freqtrader",
        "password": ""
    }
}
```

### Environment Variables

```bash
FREQTRADE_API_URL=http://localhost:8080  # API base URL
FREQTRADE_API_USER=freqtrader            # HTTP Basic Auth username
FREQTRADE_API_PASSWORD=                  # HTTP Basic Auth password (if set)
```

### Base URL

```
http://localhost:8080
```

**Docker Container**:
```
http://trading-bot-app:8080  # Internal container network
```

---

## Authentication

### HTTP Basic Authentication

All API requests require HTTP Basic Authentication.

**Python Example**:
```python
import requests
from requests.auth import HTTPBasicAuth

response = requests.get(
    "http://localhost:8080/api/v1/status",
    auth=HTTPBasicAuth("freqtrader", "")
)
```

**curl Example**:
```bash
curl -X GET http://localhost:8080/api/v1/status \
  -u freqtrader:
```

---

## Core Endpoints

### GET /api/v1/status

Get current bot status and running state.

**Response**:
```json
{
    "state": "RUNNING",
    "dry_run": true,
    "strategy": "LLMSentimentStrategy",
    "strategy_version": "1.0.0"
}
```

**Fields**:
- `state`: Bot state (RUNNING, STOPPED, RELOAD_CONFIG)
- `dry_run`: Paper trading mode (true/false)
- `strategy`: Active trading strategy name
- `strategy_version`: Strategy version

**Used By**: Dashboard status monitoring

---

### GET /api/v1/show_config

Get bot configuration details.

**Response**:
```json
{
    "dry_run": true,
    "stake_currency": "USDT",
    "stake_amount": 50.0,
    "max_open_trades": 3,
    "timeframe": "1h",
    "exchange": "coinbase",
    "strategy": "LLMSentimentStrategy",
    "minimal_roi": {
        "0": 0.05,
        "30": 0.03,
        "60": 0.02,
        "120": 0.01
    },
    "stoploss": -0.03,
    "trailing_stop": true
}
```

**Security Use**: Manual Trade Controller validates DRY_RUN mode before allowing forced trades.

---

### GET /api/v1/balance

Get account balance and wallet status.

**Response**:
```json
{
    "currencies": [
        {
            "currency": "USDT",
            "free": 950.00,
            "balance": 1000.00,
            "used": 50.00,
            "est_stake": 950.00
        }
    ],
    "total": 1000.00,
    "symbol": "USDT",
    "value": 1000.00,
    "stake": "USDT",
    "starting_capital": 1000.00,
    "starting_capital_ratio": 1.0
}
```

**Fields**:
- `free`: Available balance
- `balance`: Total balance
- `used`: Balance in open trades
- `est_stake`: Estimated stake value

---

### GET /api/v1/profit

Get profit/loss summary.

**Response**:
```json
{
    "profit_closed_coin": 25.50,
    "profit_closed_percent": 2.55,
    "profit_closed_ratio": 0.0255,
    "profit_all_coin": 30.75,
    "profit_all_percent": 3.075,
    "profit_all_ratio": 0.03075,
    "trade_count": 15,
    "closed_trade_count": 12,
    "first_trade_date": "2025-11-01 08:00:00",
    "latest_trade_date": "2025-11-23 10:30:00",
    "avg_duration": "2:15:00",
    "best_pair": "BTC/USDT",
    "best_rate": 0.0850,
    "winning_trades": 9,
    "losing_trades": 3
}
```

**Used By**: Dashboard profit metrics display

---

### GET /api/v1/trades

Get trade history (closed and open trades).

**Query Parameters**:
- `limit`: Max trades to return (default: 500)

**Response**:
```json
{
    "trades": [
        {
            "trade_id": 123,
            "pair": "BTC/USDT",
            "is_open": false,
            "open_date": "2025-11-23 08:00:00",
            "close_date": "2025-11-23 10:30:00",
            "open_rate": 95000.00,
            "close_rate": 95500.00,
            "amount": 0.001,
            "stake_amount": 50.00,
            "close_profit": 0.0052,
            "close_profit_abs": 0.26,
            "sell_reason": "roi",
            "strategy": "LLMSentimentStrategy"
        }
    ],
    "trades_count": 1
}
```

**Used By**: Dashboard trade history, performance analysis

---

### GET /api/v1/status

Get open trades with detailed information.

**Response**:
```json
[
    {
        "trade_id": 124,
        "pair": "ETH/USDT",
        "is_open": true,
        "open_date": "2025-11-23 10:00:00",
        "open_rate": 3200.00,
        "amount": 0.015,
        "stake_amount": 50.00,
        "current_rate": 3250.00,
        "current_profit": 0.0156,
        "current_profit_abs": 0.78,
        "stop_loss_abs": 3104.00,
        "stop_loss_pct": -0.03,
        "initial_stop_loss_abs": 3104.00,
        "stoploss_order_id": null,
        "open_order_id": null
    }
]
```

**Used By**: Dashboard open positions monitoring

---

## Manual Trade Control

### POST /api/v1/forcebuy

**⚠️ CRITICAL SAFETY**: Only works in DRY_RUN mode (paper trading)

Force the bot to create a buy order for a specific trading pair.

**Request Body**:
```json
{
    "pair": "BTC/USDT",
    "price": 95000.00  // Optional: specific entry price
}
```

**Response (Success)**:
```json
{
    "status": "success",
    "trade_id": 125,
    "pair": "BTC/USDT",
    "amount": 0.001,
    "stake_amount": 50.00,
    "open_rate": 95000.00
}
```

**Response (Error)**:
```json
{
    "status": "error",
    "error": "Max open trades reached"
}
```

**Safety Checks**:
1. DRY_RUN must be enabled
2. Max open trades not exceeded
3. Sufficient balance available
4. Pair must be in whitelist

**Dashboard Implementation** (`monitoring/manual_trade_controller.py`):
```python
def force_buy(self, pair: str, sentiment_score: float = 0.8) -> Dict[str, Any]:
    # Inject sentiment into Redis
    self.redis.hset(f"sentiment:{pair}", mapping={
        "score": sentiment_score,
        "timestamp": datetime.now().isoformat(),
        "headline": "Manual trade trigger",
        "source": "manual"
    })

    # Call Freqtrade API
    response = requests.post(
        f"{self.api_url}/api/v1/forcebuy",
        json={"pair": pair},
        auth=HTTPBasicAuth(self.api_username, self.api_password)
    )

    # Log to audit trail
    self._log_manual_action("FORCE_BUY", pair, sentiment_score)

    return response.json()
```

---

### POST /api/v1/forcesell

**⚠️ CRITICAL SAFETY**: Only works in DRY_RUN mode (paper trading)

Force the bot to sell (close) an open trade.

**Request Body**:
```json
{
    "tradeid": 125
}
```

**Response (Success)**:
```json
{
    "status": "success",
    "trade_id": 125,
    "pair": "BTC/USDT",
    "close_rate": 95500.00,
    "profit": 0.0052,
    "profit_abs": 0.26
}
```

**Response (Error)**:
```json
{
    "status": "error",
    "error": "Trade ID 125 not found"
}
```

**Dashboard Implementation**:
```python
def force_sell(self, trade_id: int) -> Dict[str, Any]:
    response = requests.post(
        f"{self.api_url}/api/v1/forcesell",
        json={"tradeid": trade_id},
        auth=HTTPBasicAuth(self.api_username, self.api_password)
    )

    # Log to audit trail
    self._log_manual_action("FORCE_SELL", f"trade_id:{trade_id}", None)

    return response.json()
```

---

### GET /api/v1/whitelist

Get current trading pair whitelist.

**Response**:
```json
{
    "whitelist": ["BTC/USDT", "ETH/USDT", "SOL/USDT"],
    "method": "StaticPairList"
}
```

**Used By**: Manual trade controller pair validation

---

## Status & Monitoring

### GET /api/v1/sysinfo

Get system information and performance metrics.

**Response**:
```json
{
    "cpu_pct": 15.5,
    "ram_pct": 45.2,
    "num_open_trades": 2,
    "num_trades": 15
}
```

---

### GET /api/v1/logs

Get recent bot logs.

**Query Parameters**:
- `limit`: Number of log lines (default: 50)

**Response**:
```json
{
    "logs": [
        "[2025-11-23 10:30:00] INFO - Bot heartbeat",
        "[2025-11-23 10:25:00] INFO - Buy signal for BTC/USDT"
    ]
}
```

---

### GET /api/v1/health

Health check endpoint.

**Response**:
```json
{
    "status": "ok",
    "uptime": 86400
}
```

**HTTP Status**: 200 (healthy), 503 (unhealthy)

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Example |
|------|---------|---------|
| 200 | Success | Request completed |
| 400 | Bad Request | Invalid pair format |
| 401 | Unauthorized | Invalid credentials |
| 403 | Forbidden | Live trading attempted in DRY_RUN-only endpoint |
| 404 | Not Found | Trade ID doesn't exist |
| 500 | Server Error | Internal bot error |
| 503 | Service Unavailable | Bot not running |

### Error Response Format

```json
{
    "status": "error",
    "error": "Descriptive error message",
    "code": "ERROR_CODE"
}
```

### Common Errors

**"Max open trades reached"**:
- Cause: Attempting to open trade when limit reached
- Solution: Close existing trades or increase `max_open_trades`

**"Insufficient balance"**:
- Cause: Not enough funds for stake amount
- Solution: Check balance, adjust stake amount

**"Pair not in whitelist"**:
- Cause: Attempting to trade non-whitelisted pair
- Solution: Add pair to whitelist in config

**"Trade ID not found"**:
- Cause: Invalid trade_id in forcesell
- Solution: Use GET /api/v1/status to get valid trade IDs

---

## Rate Limiting

**No rate limiting** in current configuration.

**Recommended for production**:
- Max 60 requests per minute per IP
- Implement using nginx reverse proxy

---

## Dashboard Integration

### DashboardService Implementation

**File**: `monitoring/dashboard_service.py`

**Key Methods**:
- `handle_force_buy()` (line 475): Force buy API handler
- `handle_force_sell()` (line 524): Force sell API handler
- `handle_get_open_trades()` (line 567): Open trades list
- `handle_get_audit_log()` (line 586): Manual action history

### Manual Trade Controller

**File**: `monitoring/manual_trade_controller.py`

**Features**:
- DRY_RUN validation on initialization
- Sentiment injection for forced buys
- Audit logging in Redis
- Safety confirmations

---

## Security Best Practices

1. **Always use DRY_RUN for manual trades**
   - Prevents accidental real money trades
   - Validated at controller init

2. **Audit all manual actions**
   - Logged to Redis with timestamps
   - Includes user, action, parameters

3. **Restrict API access**
   - Use strong passwords
   - Consider IP whitelisting
   - Enable HTTPS in production

4. **Monitor for abuse**
   - Track forcebuy/forcesell frequency
   - Alert on excessive manual trades

---

## Code Examples

### Python Client

```python
import requests
from requests.auth import HTTPBasicAuth

class FreqtradeClient:
    def __init__(self, base_url="http://localhost:8080", username="freqtrader", password=""):
        self.base_url = base_url
        self.auth = HTTPBasicAuth(username, password)

    def get_status(self):
        response = requests.get(
            f"{self.base_url}/api/v1/status",
            auth=self.auth
        )
        return response.json()

    def force_buy(self, pair: str):
        response = requests.post(
            f"{self.base_url}/api/v1/forcebuy",
            json={"pair": pair},
            auth=self.auth
        )
        return response.json()

    def get_open_trades(self):
        response = requests.get(
            f"{self.base_url}/api/v1/status",
            auth=self.auth
        )
        return response.json()

# Usage
client = FreqtradeClient()
status = client.get_status()
print(f"Bot state: {status['state']}, Dry run: {status['dry_run']}")
```

### JavaScript/Node.js Client

```javascript
const axios = require('axios');

const client = axios.create({
    baseURL: 'http://localhost:8080/api/v1',
    auth: {
        username: 'freqtrader',
        password: ''
    }
});

// Get status
client.get('/status')
    .then(response => {
        console.log('Bot state:', response.data.state);
        console.log('Dry run:', response.data.dry_run);
    });

// Force buy
client.post('/forcebuy', { pair: 'BTC/USDT' })
    .then(response => {
        console.log('Trade created:', response.data.trade_id);
    })
    .catch(error => {
        console.error('Error:', error.response.data.error);
    });
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0.0 | 2025-11-23 | Initial API documentation |

---

**VoidCat RDC - Excellence in Trading Automation**
**API Version: Freqtrade 2025.6**
