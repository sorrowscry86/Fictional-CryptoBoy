# CryptoBoy Architecture Diagrams
**VoidCat RDC - System Architecture Visualization**

## Table of Contents
1. [High-Level System Overview](#high-level-system-overview)
2. [Microservices Data Flow](#microservices-data-flow)
3. [Sentiment Analysis Pipeline](#sentiment-analysis-pipeline)
4. [Trading Decision Engine](#trading-decision-engine)
5. [Message Queue Architecture](#message-queue-architecture)
6. [Deployment Architecture](#deployment-architecture)

---

## High-Level System Overview

```mermaid
graph TB
    subgraph External["External Data Sources"]
        RSS[RSS News Feeds]
        Exchange[Binance Exchange]
    end

    subgraph Infrastructure["Infrastructure Layer"]
        RMQ[RabbitMQ<br/>Message Broker]
        Redis[(Redis Cache<br/>Sentiment Store)]
        Ollama[Ollama LLM<br/>Mistral 7B]
    end

    subgraph Ingestion["Data Ingestion Layer"]
        NP[News Poller<br/>RSS Aggregation]
        MS[Market Streamer<br/>WebSocket OHLCV]
    end

    subgraph Processing["Processing Layer"]
        SP[Sentiment Processor<br/>FinBERT Analysis]
        SC[Signal Cacher<br/>Redis Writer]
    end

    subgraph Trading["Trading Layer"]
        Bot[Freqtrade Bot<br/>LLM Strategy]
        Dashboard[Monitoring<br/>Dashboard]
    end

    RSS --> NP
    Exchange --> MS
    NP --> RMQ
    MS --> RMQ
    RMQ --> SP
    SP --> Ollama
    SP --> RMQ
    RMQ --> SC
    SC --> Redis
    Redis --> Bot
    Bot --> Exchange
    Redis --> Dashboard
    RMQ --> Dashboard

    style Infrastructure fill:#f9f,stroke:#333,stroke-width:2px
    style Processing fill:#bbf,stroke:#333,stroke-width:2px
    style Trading fill:#bfb,stroke:#333,stroke-width:2px
```

---

## Microservices Data Flow

```mermaid
sequenceDiagram
    participant RSS as RSS Feeds
    participant NP as News Poller
    participant Q1 as raw_news_data
    participant SP as Sentiment Processor
    participant FB as FinBERT Model
    participant Q2 as sentiment_signals
    participant SC as Signal Cacher
    participant Redis as Redis Cache
    participant Bot as Trading Bot
    participant Binance as Exchange

    RSS->>NP: Fetch articles (5 min poll)
    NP->>Q1: Publish news message
    Q1->>SP: Consume news
    SP->>FB: Analyze sentiment
    FB-->>SP: Score: -1.0 to +1.0
    SP->>Q2: Publish sentiment signal
    Q2->>SC: Consume signal
    SC->>Redis: Cache sentiment (4h TTL)
    
    loop Every 1 hour candle
        Bot->>Redis: Fetch sentiment for pair
        Redis-->>Bot: Return cached score
        Bot->>Bot: Evaluate entry conditions
        alt Sentiment > 0.7 + Tech Indicators
            Bot->>Binance: Place BUY order
            Binance-->>Bot: Order filled
        else Exit conditions met
            Bot->>Binance: Place SELL order
        end
    end
```

---

## Sentiment Analysis Pipeline

```mermaid
flowchart LR
    subgraph Input["Input Sources"]
        CD[CoinDesk RSS]
        CT[CoinTelegraph]
        DY[Decrypt]
        BM[Bitcoin Magazine]
    end

    subgraph Aggregation["News Aggregation"]
        NP[News Poller]
        Dedup[Deduplication]
        Filter[Relevance Filter]
    end

    subgraph Analysis["Sentiment Analysis"]
        FinBERT[FinBERT<br/>ProsusAI/finbert]
        Fallback1[LM Studio<br/>Fast Inference]
        Fallback2[Ollama<br/>Local LLM]
    end

    subgraph Output["Sentiment Output"]
        Score[Score: -1.0 to +1.0]
        Cache[Redis Cache]
    end

    CD --> NP
    CT --> NP
    DY --> NP
    BM --> NP
    NP --> Dedup
    Dedup --> Filter
    Filter --> FinBERT
    FinBERT -.Fallback.-> Fallback1
    Fallback1 -.Fallback.-> Fallback2
    FinBERT --> Score
    Score --> Cache

    style FinBERT fill:#9f9,stroke:#333,stroke-width:3px
    style Cache fill:#ff9,stroke:#333,stroke-width:2px
```

---

## Trading Decision Engine

```mermaid
flowchart TD
    Start([New 1h Candle]) --> FetchSentiment[Fetch Sentiment from Redis]
    FetchSentiment --> CheckStale{Sentiment < 4h old?}
    
    CheckStale -->|No| Skip[Skip Entry]
    CheckStale -->|Yes| CheckScore{Score > 0.7?}
    
    CheckScore -->|No| Skip
    CheckScore -->|Yes| TechIndicators[Calculate Technical Indicators]
    
    TechIndicators --> EMA[EMA 12 > EMA 26?]
    EMA -->|No| Skip
    EMA -->|Yes| RSI[30 < RSI < 70?]
    
    RSI -->|No| Skip
    RSI -->|Yes| MACD[MACD > Signal?]
    
    MACD -->|No| Skip
    MACD -->|Yes| Volume[Volume > Avg?]
    
    Volume -->|No| Skip
    Volume -->|Yes| BB[Price < Upper BB?]
    
    BB -->|No| Skip
    BB -->|Yes| Entry[✓ ENTER LONG POSITION]
    
    Entry --> MonitorExit[Monitor Exit Conditions]
    MonitorExit --> ExitCheck{Exit Trigger?}
    
    ExitCheck -->|Sentiment < -0.5| Exit[✓ EXIT POSITION]
    ExitCheck -->|ROI Target Met| Exit
    ExitCheck -->|Stop Loss -3%| Exit
    ExitCheck -->|Tech Signal| Exit
    ExitCheck -->|None| MonitorExit
    
    Exit --> End([Position Closed])
    Skip --> End

    style Entry fill:#9f9,stroke:#333,stroke-width:3px
    style Exit fill:#f99,stroke:#333,stroke-width:3px
    style Skip fill:#ccc,stroke:#333,stroke-width:1px
```

---

## Message Queue Architecture

```mermaid
graph TB
    subgraph Publishers["Message Publishers"]
        NP[News Poller]
        MS[Market Streamer]
        SP[Sentiment Processor]
    end

    subgraph RabbitMQ["RabbitMQ Broker"]
        Q1[Queue: raw_news_data<br/>Durable: Yes<br/>TTL: 24h]
        Q2[Queue: raw_market_data<br/>Durable: Yes<br/>TTL: 1h]
        Q3[Queue: sentiment_signals<br/>Durable: Yes<br/>TTL: 12h]
    end

    subgraph Consumers["Message Consumers"]
        SP2[Sentiment Processor]
        Bot[Trading Bot]
        SC[Signal Cacher]
    end

    NP -->|Publish| Q1
    MS -->|Publish| Q2
    SP -->|Publish| Q3
    
    Q1 -->|Consume| SP2
    Q2 -->|Consume| Bot
    Q3 -->|Consume| SC

    style Q1 fill:#bbf,stroke:#333,stroke-width:2px
    style Q2 fill:#bbf,stroke:#333,stroke-width:2px
    style Q3 fill:#bbf,stroke:#333,stroke-width:2px
```

**Message Schemas:**

| Queue | Schema | Example |
|-------|--------|---------|
| `raw_news_data` | `{timestamp, source, title, url, content}` | News article from RSS |
| `raw_market_data` | `{timestamp, pair, open, high, low, close, volume}` | OHLCV candle data |
| `sentiment_signals` | `{timestamp, pair, score, headline, source, confidence}` | Sentiment analysis result |

---

## Deployment Architecture

```mermaid
graph TB
    subgraph Docker["Docker Compose Production"]
        subgraph Network["trading-network (Bridge)"]
            
            subgraph Infra["Infrastructure Containers"]
                RMQ[rabbitmq:3-alpine<br/>Port: 5672, 15672<br/>Volume: rabbitmq_data]
                RedisC[redis:alpine<br/>Port: 6379<br/>Volume: redis_data]
                OllamaC[ollama/ollama<br/>Port: 11434<br/>Volume: ollama_models]
            end
            
            subgraph Services["Microservice Containers"]
                NPod[news-poller<br/>Python Service]
                MStream[market-streamer<br/>CCXT.pro WebSocket]
                SProc[sentiment-processor<br/>FinBERT Analysis]
                SCache[signal-cacher<br/>Redis Writer]
            end
            
            subgraph App["Application Containers"]
                BotC[trading-bot<br/>Freqtrade<br/>Port: 8080]
                DashC[dashboard<br/>Monitoring UI<br/>Port: 8081]
            end
        end
    end

    RMQ -.-> NPod
    RMQ -.-> MStream
    RMQ -.-> SProc
    RMQ -.-> SCache
    RedisC -.-> SCache
    RedisC -.-> BotC
    RedisC -.-> DashC
    OllamaC -.-> SProc
    
    style Infra fill:#f9f,stroke:#333,stroke-width:2px
    style Services fill:#bbf,stroke:#333,stroke-width:2px
    style App fill:#bfb,stroke:#333,stroke-width:2px
```

**Container Resource Limits:**

| Container | CPU | Memory | Storage |
|-----------|-----|--------|---------|
| RabbitMQ | 1 core | 512MB | 1GB (data) |
| Redis | 1 core | 256MB | 500MB (cache) |
| Ollama | 2 cores | 4GB | 5GB (models) |
| Sentiment Processor | 2 cores | 2GB | - |
| Trading Bot | 1 core | 512MB | 1GB (logs) |
| Dashboard | 0.5 core | 256MB | - |

---

## Security Architecture

```mermaid
flowchart TB
    subgraph External["External Threats"]
        Attacker[Potential Attacker]
    end

    subgraph Perimeter["Security Perimeter"]
        FW[Firewall<br/>Ports: 5672, 6379, 8080]
        Auth[Authentication<br/>API Keys, Passwords]
    end

    subgraph AppLayer["Application Layer"]
        Validation[Input Validation<br/>Pydantic Schemas]
        Encryption[TLS/SSL<br/>RabbitMQ, Redis]
        Secrets[Secrets Management<br/>Environment Variables]
    end

    subgraph DataLayer["Data Layer"]
        Redis[(Redis<br/>No Docker Socket)]
        RMQ[(RabbitMQ<br/>Credentials Required)]
    end

    Attacker -->|❌ Blocked| FW
    FW --> Auth
    Auth --> Validation
    Validation --> Encryption
    Encryption --> Secrets
    Secrets --> Redis
    Secrets --> RMQ

    style Perimeter fill:#f99,stroke:#333,stroke-width:3px
    style AppLayer fill:#ff9,stroke:#333,stroke-width:2px
    style DataLayer fill:#9f9,stroke:#333,stroke-width:2px
```

**Security Measures:**
- ✅ No hardcoded credentials (enforced via ValueError)
- ✅ Docker socket removed (container escape prevention)
- ✅ Input validation with Pydantic schemas
- ✅ TLS/SSL for external communications
- ✅ API authentication with JWT tokens
- ✅ Rate limiting on public endpoints
- ❌ TODO: Secrets management (Vault integration)
- ❌ TODO: Network policies (restrict inter-container traffic)

---

## Performance Characteristics

| Component | Latency | Throughput | Bottleneck |
|-----------|---------|------------|------------|
| News Poller | 5 min cycle | 50 articles/min | RSS feed limits |
| Sentiment Analysis | 200ms/article | 300 articles/min | FinBERT inference |
| Redis Cache | 5-10ms | 10K ops/sec | Network I/O |
| RabbitMQ | 10-50ms | 1K msg/sec | Message size |
| Trading Bot | 1 hour cycle | 3 pairs | Freqtrade strategy |

**Optimization Targets:**
1. **Sentiment Analysis:** Batch processing (5x speedup)
2. **Redis:** Connection pooling (2x throughput)
3. **RabbitMQ:** Prefetch tuning (30% improvement)
4. **News Polling:** Async fetching (5x faster)

---

## Monitoring & Observability

```mermaid
graph LR
    subgraph Apps["Application Layer"]
        Bot[Trading Bot]
        Services[Microservices]
    end

    subgraph Metrics["Metrics Collection"]
        Prom[Prometheus]
        Graf[Grafana]
    end

    subgraph Logs["Log Aggregation"]
        ELK[ELK Stack]
        Loki[Loki]
    end

    subgraph Alerts["Alerting"]
        TG[Telegram Bot]
        Email[Email Alerts]
    end

    Bot --> Prom
    Services --> Prom
    Prom --> Graf
    
    Bot --> ELK
    Services --> ELK
    ELK --> Loki
    
    Prom --> TG
    ELK --> Email

    style Prom fill:#f99,stroke:#333,stroke-width:2px
    style Graf fill:#9f9,stroke:#333,stroke-width:2px
    style TG fill:#bbf,stroke:#333,stroke-width:2px
```

**Key Metrics:**
- Trading: Win rate, Sharpe ratio, drawdown, P&L
- System: CPU, memory, disk I/O, network
- Services: Message queue depth, cache hit rate, latency
- Errors: Exception rate, failed trades, connection errors

---

## Disaster Recovery Plan

| Scenario | Impact | Recovery Time | Strategy |
|----------|--------|---------------|----------|
| Redis failure | No new trades | < 5 minutes | Auto-restart + backup restore |
| RabbitMQ failure | Data loss | < 10 minutes | Durable queues + consumer restart |
| Trading bot crash | Missed signals | < 2 minutes | Docker auto-restart |
| Exchange outage | Cannot trade | Variable | Switch to backup exchange |
| LLM service down | No new sentiment | < 30 minutes | Fallback to cached signals |

**Backup Schedule:**
- Redis: Every 6 hours → JSON dump
- RabbitMQ: Persistent queues (disk)
- Logs: Daily rotation + 30-day retention
- Config: Git version control

---

**Generated by:** The High Evolutionary  
**Date:** November 20, 2025  
**Status:** Phase 6 - Documentation Enhancement
