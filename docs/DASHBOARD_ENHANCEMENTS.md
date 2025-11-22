# 🎛️ Trading Dashboard Enhancement Plan

**CryptoBoy Trading Bot - Dashboard Improvements**
**VoidCat RDC - Phase 5: Higher Functions**

---

## 🎯 **User Requirements**

**Problem:** Bot made no trades during paper trading, no visibility into WHY
**Needs:**
1. Manual trade triggering capability
2. Real-time strategy state visibility (why no trades?)
3. Entry condition debugging
4. Dashboard improvements for monitoring

---

## 📋 **Current Dashboard Limitations**

**Existing:** `monitoring/dashboard_service.py`
- ✅ Real-time sentiment display
- ✅ Trading pair monitoring
- ✅ Basic statistics
- ❌ **No entry condition visibility**
- ❌ **No manual trade controls**
- ❌ **No "why no trade" explanation**
- ❌ **No Redis cache inspection**
- ❌ **No technical indicator display**

---

## 🚀 **Enhancement 1: Strategy State Monitor**

### **Feature: Real-Time Entry Condition Checklist**

Display ALL 6 entry conditions with current status:

```
╔═══════════════════════════════════════════════════════════════╗
║           BTC/USDT Entry Conditions (Last Check)              ║
╠═══════════════════════════════════════════════════════════════╣
║ ✅ 1. Sentiment Score: 0.85 > 0.7 threshold ✓                 ║
║ ❌ 2. EMA Trend: EMA(12)=49,800 < EMA(26)=50,100 ✗            ║
║ ✅ 3. RSI: 45 (healthy range 30-70) ✓                         ║
║ ❌ 4. MACD: -50 < Signal=-30 (bearish) ✗                      ║
║ ✅ 5. Volume: 1,250 > Avg=800 ✓                               ║
║ ✅ 6. Price: 49,900 < BB_Upper=51,000 ✓                       ║
╠═══════════════════════════════════════════════════════════════╣
║ ENTRY SIGNAL: ❌ NO TRADE (2/6 conditions failed)             ║
║ BLOCKING: EMA trend bearish, MACD bearish                     ║
╚═══════════════════════════════════════════════════════════════╝
```

**Implementation:**

```python
# monitoring/strategy_monitor.py

import redis
from typing import Dict, Any

class StrategyStateMonitor:
    """
    Monitor strategy entry conditions in real-time.
    Shows exactly why trades are/aren't executing.
    """

    def __init__(self, redis_client):
        self.redis = redis_client

    def get_entry_conditions(self, pair: str) -> Dict[str, Any]:
        """
        Retrieve all entry condition states for a trading pair.

        Returns:
            {
                "pair": "BTC/USDT",
                "conditions": [
                    {"id": 1, "name": "Sentiment", "value": 0.85, "threshold": 0.7, "met": True},
                    {"id": 2, "name": "EMA Trend", "value": "bearish", "met": False, "reason": "EMA12 < EMA26"},
                    ...
                ],
                "can_enter": False,
                "blocking_reasons": ["EMA trend bearish", "MACD bearish"]
            }
        """
        # Read from Redis keys that trading bot should populate
        # Format: strategy_state:BTC/USDT
        state = self.redis.hgetall(f"strategy_state:{pair}")

        conditions = [
            {
                "id": 1,
                "name": "Sentiment Score",
                "value": float(state.get("sentiment_score", 0)),
                "threshold": "> 0.7",
                "met": float(state.get("sentiment_score", 0)) > 0.7,
                "symbol": "✅" if float(state.get("sentiment_score", 0)) > 0.7 else "❌"
            },
            {
                "id": 2,
                "name": "EMA Trend",
                "value": f"EMA12={state.get('ema12')} vs EMA26={state.get('ema26')}",
                "threshold": "EMA12 > EMA26",
                "met": state.get("ema_trend") == "bullish",
                "symbol": "✅" if state.get("ema_trend") == "bullish" else "❌"
            },
            {
                "id": 3,
                "name": "RSI",
                "value": int(state.get("rsi", 0)),
                "threshold": "30-70",
                "met": 30 < int(state.get("rsi", 0)) < 70,
                "symbol": "✅" if 30 < int(state.get("rsi", 0)) < 70 else "❌"
            },
            {
                "id": 4,
                "name": "MACD",
                "value": f"{state.get('macd')} vs Signal={state.get('macd_signal')}",
                "threshold": "MACD > Signal",
                "met": float(state.get("macd", 0)) > float(state.get("macd_signal", 0)),
                "symbol": "✅" if float(state.get("macd", 0)) > float(state.get("macd_signal", 0)) else "❌"
            },
            {
                "id": 5,
                "name": "Volume",
                "value": f"{state.get('volume')} > Avg={state.get('avg_volume')}",
                "threshold": "Above Average",
                "met": float(state.get("volume", 0)) > float(state.get("avg_volume", 1)),
                "symbol": "✅" if float(state.get("volume", 0)) > float(state.get("avg_volume", 1)) else "❌"
            },
            {
                "id": 6,
                "name": "Bollinger Bands",
                "value": f"Price={state.get('price')} < Upper={state.get('bb_upper')}",
                "threshold": "Below Upper Band",
                "met": float(state.get("price", 0)) < float(state.get("bb_upper", 999999)),
                "symbol": "✅" if float(state.get("price", 0)) < float(state.get("bb_upper", 999999)) else "❌"
            }
        ]

        met_count = sum(1 for c in conditions if c["met"])
        can_enter = met_count == 6

        blocking_reasons = [c["name"] for c in conditions if not c["met"]]

        return {
            "pair": pair,
            "conditions": conditions,
            "met_count": met_count,
            "total_count": 6,
            "can_enter": can_enter,
            "blocking_reasons": blocking_reasons,
            "last_updated": state.get("last_updated", "Never")
        }
```

---

## 🚀 **Enhancement 2: Manual Trade Injection**

### **Feature: Force Trade Execution (Testing)**

**Dashboard Button:** "Force Buy" / "Force Sell"

**Security:** Only works in DRY_RUN mode + requires confirmation

```python
# monitoring/manual_trade_controller.py

import os
import requests
from datetime import datetime

class ManualTradeController:
    """
    Manually trigger trades via Freqtrade API.
    ONLY works in DRY_RUN mode for safety.
    """

    def __init__(self, freqtrade_url: str = "http://localhost:8080"):
        self.api_url = freqtrade_url
        self.api_username = os.getenv("API_USERNAME")
        self.api_password = os.getenv("API_PASSWORD")

        # Verify DRY_RUN mode
        if os.getenv("DRY_RUN", "false").lower() != "true":
            raise ValueError("Manual trades ONLY allowed in DRY_RUN mode!")

    def force_buy(self, pair: str, amount_usdt: float = 100) -> Dict[str, Any]:
        """
        Manually force a buy order (DRY_RUN only).

        Args:
            pair: Trading pair (e.g., "BTC/USDT")
            amount_usdt: Amount in USDT to spend

        Returns:
            Trade result dictionary
        """
        # Call Freqtrade API to force entry
        response = requests.post(
            f"{self.api_url}/api/v1/forcebuy",
            json={
                "pair": pair,
                "price": None  # Use current market price
            },
            auth=(self.api_username, self.api_password)
        )

        if response.status_code == 200:
            result = response.json()
            return {
                "success": True,
                "trade_id": result.get("trade_id"),
                "pair": pair,
                "entry_price": result.get("open_rate"),
                "amount": result.get("amount"),
                "timestamp": datetime.utcnow().isoformat()
            }
        else:
            return {
                "success": False,
                "error": response.text
            }

    def force_sell(self, trade_id: int) -> Dict[str, Any]:
        """
        Manually force sell an open trade.

        Args:
            trade_id: ID of trade to close

        Returns:
            Result dictionary
        """
        response = requests.post(
            f"{self.api_url}/api/v1/forcesell",
            json={"tradeid": str(trade_id)},
            auth=(self.api_username, self.api_password)
        )

        if response.status_code == 200:
            return {"success": True, "trade_id": trade_id}
        else:
            return {"success": False, "error": response.text}

    def inject_test_sentiment(self, pair: str, score: float) -> None:
        """
        Inject fake sentiment score into Redis for testing.
        Allows testing strategy with known sentiment values.

        Args:
            pair: Trading pair
            score: Sentiment score (-1.0 to +1.0)
        """
        import redis

        redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            decode_responses=True
        )

        sentiment_data = {
            "score": str(score),
            "timestamp": datetime.utcnow().isoformat(),
            "headline": "[MANUAL TEST] Simulated sentiment",
            "source": "manual_injection",
            "model": "manual"
        }

        redis_client.hset(f"sentiment:{pair}", mapping=sentiment_data)
        print(f"✅ Injected sentiment {score:+.2f} for {pair}")
```

---

## 🚀 **Enhancement 3: Dashboard UI Updates**

### **New Dashboard Sections:**

```
┌─────────────────────────────────────────────────────────────┐
│               CryptoBoy Trading Dashboard                   │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│ [1] STRATEGY STATE                                          │
│     ┌─ BTC/USDT Entry Conditions ──────────────────────┐   │
│     │ ✅ Sentiment: 0.85 > 0.7                         │   │
│     │ ❌ EMA Trend: Bearish (EMA12 < EMA26)            │   │
│     │ ✅ RSI: 45 (healthy)                             │   │
│     │ ❌ MACD: Bearish (-50 < -30)                     │   │
│     │ ✅ Volume: Above average                         │   │
│     │ ✅ Bollinger: Not overextended                   │   │
│     │                                                  │   │
│     │ STATUS: ❌ NO ENTRY (2/6 failed)                 │   │
│     │ BLOCKING: EMA bearish, MACD bearish              │   │
│     └──────────────────────────────────────────────────┘   │
│                                                             │
│ [2] MANUAL CONTROLS (DRY_RUN MODE ONLY)                     │
│     ┌─────────────────────────────────────────────────┐    │
│     │ [Force Buy BTC/USDT]  Amount: [100] USDT       │    │
│     │ [Force Sell Trade #5]                           │    │
│     │ [Inject Sentiment]  Pair: [BTC/USDT] Score: [0.9] │ │
│     └─────────────────────────────────────────────────┘    │
│                                                             │
│ [3] REDIS CACHE MONITOR                                     │
│     ┌─ Sentiment Signals ──────────────────────────────┐   │
│     │ BTC/USDT: 0.85 (2 min ago) ✅ FRESH              │   │
│     │ ETH/USDT: 0.62 (10 min ago) ⚠️ STALE             │   │
│     │ BNB/USDT: N/A ❌ NO DATA                         │   │
│     └──────────────────────────────────────────────────┘   │
│                                                             │
│ [4] OPEN TRADES                                             │
│     No open trades                                          │
│                                                             │
│ [5] RECENT ACTIVITY LOG                                     │
│     [10:30:15] BTC/USDT: Entry conditions checked (2/6)    │
│     [10:29:45] Sentiment updated: BTC/USDT = 0.85          │
│     [10:28:30] ETH/USDT: No entry (sentiment too low)      │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 🚀 **Enhancement 4: Trading Bot Modifications**

**Modify:** `strategies/llm_sentiment_strategy.py`

Add state publishing to Redis:

```python
def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
    """Calculate indicators AND publish state to Redis for dashboard"""

    # ... existing indicator calculations ...

    # NEW: Publish strategy state to Redis for dashboard visibility
    pair = metadata['pair']

    # Get latest values
    latest = dataframe.iloc[-1]

    state = {
        "sentiment_score": str(self._get_sentiment_score(pair, latest['date'])),
        "ema12": str(latest['ema12']),
        "ema26": str(latest['ema26']),
        "ema_trend": "bullish" if latest['ema12'] > latest['ema26'] else "bearish",
        "rsi": str(latest['rsi']),
        "macd": str(latest['macd']),
        "macd_signal": str(latest['macdsignal']),
        "volume": str(latest['volume']),
        "avg_volume": str(dataframe['volume'].rolling(20).mean().iloc[-1]),
        "price": str(latest['close']),
        "bb_upper": str(latest['bb_upperband']),
        "last_updated": datetime.utcnow().isoformat()
    }

    # Publish to Redis
    try:
        self.redis_client.hset(f"strategy_state:{pair}", mapping=state)
    except Exception as e:
        logger.error(f"Failed to publish strategy state: {e}")

    return dataframe
```

---

## 📦 **Implementation Plan**

### **Phase 1: Core Monitoring (1-2 days)**
1. ✅ Create `monitoring/strategy_monitor.py`
2. ✅ Modify trading strategy to publish state to Redis
3. ✅ Create `monitoring/manual_trade_controller.py`
4. ✅ Add Redis cache monitor

### **Phase 2: Dashboard UI (1-2 days)**
1. Update `monitoring/dashboard_service.py` with new sections
2. Add manual control buttons (only in DRY_RUN)
3. Add entry condition checklist display
4. Add real-time log streaming

### **Phase 3: Testing (1 day)**
1. Test manual trade injection
2. Test sentiment injection
3. Verify state monitoring accuracy
4. Document usage

---

## 🎯 **Usage Examples**

### **Scenario 1: Debugging No Trades**

```bash
# Start dashboard
python monitoring/dashboard_service.py

# Check strategy state
# Dashboard shows:
# ❌ NO ENTRY (3/6 failed)
# BLOCKING: EMA bearish, MACD bearish, Volume low

# Conclusion: Market conditions not favorable
```

### **Scenario 2: Force Test Trade**

```bash
# In dashboard:
1. Click "Inject Sentiment"
2. Set BTC/USDT = 0.95 (very bullish)
3. Wait for next candle
4. If still no trade, check other 5 conditions
5. If all conditions met, trade executes
6. If not, dashboard shows what's blocking
```

### **Scenario 3: Manual Entry**

```bash
# Dashboard DRY_RUN controls:
1. Click "Force Buy BTC/USDT"
2. Confirm: "Manual entry for testing - 100 USDT"
3. Trade opens immediately
4. Monitor in "Open Trades" section
5. Click "Force Sell" when ready to close
```

---

## 🔒 **Safety Measures**

1. **DRY_RUN Only:** Manual controls ONLY work when `DRY_RUN=true`
2. **Confirmation Required:** All manual actions require confirmation popup
3. **Audit Logging:** All manual actions logged to `logs/manual_trades.log`
4. **Warning Banner:** Dashboard shows "PAPER TRADING MODE" prominently
5. **Disable in Production:** Manual controls hidden when `DRY_RUN=false`

---

## 📊 **Expected Benefits**

**Before:**
- ❌ No trades executed, no idea why
- ❌ Must read logs to understand strategy state
- ❌ Can't test individual conditions
- ❌ No visibility into Redis cache

**After:**
- ✅ Real-time "why no trade" explanation
- ✅ Visual entry condition checklist
- ✅ Manual trade testing capability
- ✅ Sentiment injection for testing
- ✅ Complete visibility into strategy state

---

## 📝 **Files to Create/Modify**

**New Files:**
1. `monitoring/strategy_monitor.py` (150 lines)
2. `monitoring/manual_trade_controller.py` (200 lines)
3. `docs/DASHBOARD_USER_GUIDE.md` (user documentation)

**Modified Files:**
1. `monitoring/dashboard_service.py` (add new UI sections)
2. `strategies/llm_sentiment_strategy.py` (publish state to Redis)

**Total Estimated Lines:** ~500 lines of new code

---

**Status:** Ready for Implementation
**Priority:** HIGH (addresses critical user need for trade debugging)
**Phase:** 5 (Higher Functions - New Capabilities)
