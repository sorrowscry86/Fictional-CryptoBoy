# LM Studio Setup Guide
**VoidCat RDC - CryptoBoy Trading Bot**

## Overview

LM Studio is a powerful alternative to Ollama that provides:
- **Better GPU acceleration** (up to 3x faster inference)
- **OpenAI-compatible API** (easy integration)
- **User-friendly GUI** for model management
- **GGUF quantized models** (smaller, faster)
- **Better memory management**

---

## Installation

### 1. Download LM Studio

Visit: [https://lmstudio.ai/](https://lmstudio.ai/)

- Windows: Download and run installer
- macOS: Download .dmg and install
- Linux: AppImage available

### 2. Download Mistral 7B Model

1. Open LM Studio
2. Click **"Search"** tab
3. Search for: `mistral-7b-instruct`
4. Recommended models:
   - `TheBloke/Mistral-7B-Instruct-v0.2-GGUF` (Q4_K_M) - Best balance
   - `TheBloke/Mistral-7B-Instruct-v0.2-GGUF` (Q5_K_M) - Better quality
   - `TheBloke/Mistral-7B-Instruct-v0.2-GGUF` (Q8_0) - Highest quality

5. Click **Download**
6. Wait for download to complete (~4-6 GB)

### 3. Load the Model

1. Click **"Chat"** tab
2. Select your downloaded model from dropdown
3. Click **"Load Model"**
4. Wait for model to load into memory

### 4. Start Local Server

1. Click **"Local Server"** tab (or Developer → Local Server)
2. Click **"Start Server"**
3. Default port: **1234**
4. Server URL: `http://localhost:1234`

**Important:** Keep LM Studio running in the background while the bot operates.

---

## Configuration

### Option 1: Use LM Studio Exclusively

Edit `.env` file:

```bash
# LM Studio Configuration
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=mistral-7b-instruct
USE_LMSTUDIO=true

# Disable Ollama (optional)
# OLLAMA_HOST=http://localhost:11434
# OLLAMA_MODEL=mistral:7b
```

### Option 2: Use Both (Fallback)

Keep both configured:

```bash
# Primary: LM Studio
LMSTUDIO_HOST=http://localhost:1234
LMSTUDIO_MODEL=mistral-7b-instruct
USE_LMSTUDIO=true

# Fallback: Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=mistral:7b
```

The system will automatically fall back to Ollama if LM Studio is unavailable.

---

## Testing

### Test LM Studio Connection

```bash
python -c "from llm.lmstudio_adapter import test_lmstudio; test_lmstudio()"
```

Expected output:
```
Testing LM Studio Adapter...
============================================================

1. Testing connection...
✓ LM Studio is running

2. Available models:
  - mistral-7b-instruct

3. Testing sentiment analysis...

  🟢 Text: Bitcoin hits new all-time high as institutions...
     Score: +0.85

  🔴 Text: Major exchange hacked, millions in crypto stolen...
     Score: -0.92

  🟢 Text: SEC approves Bitcoin ETF, marking historic regul...
     Score: +0.78

============================================================
Test complete!
```

### Test Unified Client

```python
from llm.lmstudio_adapter import UnifiedLLMClient

# Initialize (prefers LM Studio)
client = UnifiedLLMClient(prefer_lmstudio=True)

# Analyze sentiment
text = "Bitcoin price surges after ETF approval"
sentiment = client.analyze_sentiment(text)
print(f"Sentiment: {sentiment}")
```

---

## Performance Comparison

| Metric | Ollama | LM Studio |
|--------|--------|-----------|
| **Inference Speed** | ~2-3 sec | ~0.5-1 sec |
| **GPU Utilization** | ~60-70% | ~85-95% |
| **Memory Usage** | ~6 GB | ~4-5 GB |
| **Startup Time** | ~3-5 sec | ~1-2 sec |
| **API Format** | Custom | OpenAI |

**Recommendation:** Use LM Studio for production, Ollama for development.

---

## Integration with Trading Bot

### Update Sentiment Analyzer

Edit `llm/sentiment_analyzer.py`:

```python
from llm.lmstudio_adapter import UnifiedLLMClient

# Initialize once at module level
llm_client = UnifiedLLMClient(prefer_lmstudio=True)

def analyze_sentiment(text: str) -> float:
    """Analyze sentiment using LM Studio or Ollama."""
    return llm_client.analyze_sentiment(text) or 0.0
```

### No Other Changes Needed

The `UnifiedLLMClient` is a drop-in replacement. All existing code continues to work.

---

## Advanced Configuration

### Custom System Prompts

```python
from llm.lmstudio_adapter import LMStudioAdapter

adapter = LMStudioAdapter()

custom_prompt = """You are an expert crypto analyst.
Analyze sentiment with focus on:
1. Price action predictions
2. Regulatory impact
3. Institutional sentiment
4. Technical developments
"""

sentiment = adapter.generate(
    prompt="Bitcoin ETF approved",
    system_prompt=custom_prompt,
    temperature=0.5
)
```

### Adjust Model Parameters

In LM Studio GUI:
1. Click **"Settings"** → **"Model Parameters"**
2. Adjust:
   - **Temperature**: 0.3 (consistent) to 0.9 (creative)
   - **Context Length**: 4096 (default) to 8192 (longer memory)
   - **GPU Layers**: Max (full GPU) or adjust for VRAM

---

## Troubleshooting

### LM Studio Not Responding

```bash
# Check if server is running
curl http://localhost:1234/v1/models

# Expected: JSON list of models
```

**Solutions:**
1. Restart LM Studio
2. Check port 1234 is not in use
3. Reload the model in LM Studio

### Model Not Loaded

**Error:** `No models loaded`

**Solution:**
1. Open LM Studio
2. Go to **Chat** tab
3. Select model and click **Load Model**
4. Wait for loading to complete

### Slow Inference

**Causes:**
- Running on CPU instead of GPU
- Model too large for VRAM
- Other GPU-intensive apps running

**Solutions:**
1. Use smaller quantization (Q4_K_M instead of Q8_0)
2. Close other GPU apps
3. Check GPU drivers updated
4. Enable **GPU Acceleration** in LM Studio settings

### Connection Refused

**Error:** `Connection refused to localhost:1234`

**Solution:**
1. Ensure **Local Server** is started in LM Studio
2. Check firewall not blocking port 1234
3. Try restarting LM Studio

---

## Best Practices

### Production Deployment

1. **Auto-start LM Studio** on system boot
2. **Pre-load model** on startup (use CLI mode)
3. **Monitor server health** (health check endpoint)
4. **Set up fallback to Ollama** for redundancy

### Model Selection

| Use Case | Recommended Model | Quantization |
|----------|------------------|--------------|
| **Fast Trading** | Mistral 7B | Q4_K_M |
| **Balanced** | Mistral 7B | Q5_K_M |
| **High Accuracy** | Mistral 7B | Q8_0 |
| **Low Memory** | Phi-2 | Q4_K_M |

### Resource Allocation

**Minimum:**
- 8 GB RAM
- 4 GB VRAM (GPU)
- 10 GB disk space

**Recommended:**
- 16 GB RAM
- 8 GB VRAM (GPU)
- 20 GB disk space

---

## Alternative Models

### For Faster Inference

```
# Smaller models (1-2 GB)
- microsoft/phi-2
- TinyLlama/TinyLlama-1.1B

# Load in LM Studio, update .env:
LMSTUDIO_MODEL=phi-2
```

### For Better Accuracy

```
# Larger models (7-13 GB)
- mistralai/Mixtral-8x7B-Instruct
- meta-llama/Llama-2-13B-Chat

# Requires 16+ GB VRAM
LMSTUDIO_MODEL=mixtral-8x7b-instruct
```

---

## Monitoring

### Check Active Backend

```python
from llm.lmstudio_adapter import UnifiedLLMClient

client = UnifiedLLMClient()
print(f"Active backend: {client.active_backend[0]}")
```

### Health Check Endpoint

```bash
# LM Studio health check
curl http://localhost:1234/v1/models

# Ollama health check
curl http://localhost:11434/api/tags
```

---

## CLI Control (Advanced)

LM Studio can be controlled via CLI for automation:

```bash
# Windows: LM Studio CLI not yet available
# macOS/Linux: Use API for automation

# Auto-load model on startup
curl -X POST http://localhost:1234/v1/models/load \
  -H "Content-Type: application/json" \
  -d '{"model": "mistral-7b-instruct"}'
```

---

## Migration from Ollama

### Step 1: Install and Test LM Studio

```bash
# Test LM Studio
python -c "from llm.lmstudio_adapter import test_lmstudio; test_lmstudio()"
```

### Step 2: Update Environment

```bash
# Edit .env
USE_LMSTUDIO=true
```

### Step 3: Restart Bot

```bash
docker-compose down
docker-compose up -d
```

### Step 4: Monitor Performance

```bash
# Check logs
docker-compose logs -f trading-bot

# Look for: "✓ Using LM Studio as LLM backend"
```

---

## Support

**LM Studio Issues:**
- [LM Studio Discord](https://discord.gg/lmstudio)
- [GitHub Issues](https://github.com/lmstudio-ai/lmstudio/issues)

**CryptoBoy Integration:**
- GitHub Issues: [Fictional-CryptoBoy/issues](https://github.com/sorrowscry86/Fictional-CryptoBoy/issues)
- Developer: SorrowsCry86@voidcat.org

---

**Built with ❤️ by VoidCat RDC**

*LM Studio integration provides superior performance for production trading.*
