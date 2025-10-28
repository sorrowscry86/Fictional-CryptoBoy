# ============================================================================
# CryptoBoy Trading System Launcher (PowerShell)
# VoidCat RDC - Excellence in Automated Trading
# ============================================================================

# Set window title and colors
$Host.UI.RawUI.WindowTitle = "CryptoBoy Trading System - VoidCat RDC"

function Write-Header {
    Write-Host "`n================================================================================" -ForegroundColor Cyan
    Write-Host "                  CRYPTOBOY TRADING SYSTEM - VOIDCAT RDC" -ForegroundColor White
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host "[$Step] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Success {
    param([string]$Message)
    Write-Host "[OK] " -ForegroundColor Green -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] " -ForegroundColor Red -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] " -ForegroundColor Yellow -NoNewline
    Write-Host $Message -ForegroundColor White
}

function Write-Info {
    param([string]$Message)
    Write-Host "[*] " -ForegroundColor Cyan -NoNewline
    Write-Host $Message -ForegroundColor White
}

# ============================================================================
# Main Execution
# ============================================================================

Clear-Host
Write-Header

# Navigate to script directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptPath
Write-Info "Project Directory: $scriptPath"
Write-Host ""

# ============================================================================
# STEP 1: Check Docker
# ============================================================================
Write-Step "STEP 1/6" "Checking Docker..."
try {
    $dockerVersion = docker version 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Docker is running"
        $dockerInfo = docker info --format "{{.ServerVersion}}" 2>$null
        Write-Host "  Docker version: $dockerInfo" -ForegroundColor Gray
    } else {
        throw "Docker not responding"
    }
} catch {
    Write-Error "Docker is not running! Please start Docker Desktop and try again."
    Write-Host ""
    pause
    exit 1
}
Write-Host ""

# ============================================================================
# STEP 2: Check Python Environment
# ============================================================================
Write-Step "STEP 2/6" "Checking Python..."
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Python is available"
        Write-Host "  $pythonVersion" -ForegroundColor Gray
    } else {
        throw "Python not found"
    }
} catch {
    Write-Error "Python is not installed or not in PATH!"
    Write-Host ""
    pause
    exit 1
}
Write-Host ""

# ============================================================================
# STEP 3: Start Trading Bot
# ============================================================================
Write-Step "STEP 3/6" "Starting Trading Bot..."

# Check if container exists and is running
$containerStatus = docker ps -a --filter "name=trading-bot-app" --format "{{.Status}}" 2>$null

if ($containerStatus -match "Up") {
    Write-Success "Trading bot is already running"
    $uptime = docker ps --filter "name=trading-bot-app" --format "{{.Status}}" 2>$null
    Write-Host "  Status: $uptime" -ForegroundColor Gray
} elseif ($containerStatus) {
    Write-Info "Starting existing container..."
    docker start trading-bot-app >$null 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Trading bot started successfully"
    } else {
        Write-Error "Failed to start container!"
        pause
        exit 1
    }
} else {
    Write-Info "Creating new trading bot container..."
    docker-compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Trading bot created and started"
    } else {
        Write-Error "Failed to create container!"
        pause
        exit 1
    }
}

Write-Info "Waiting for bot initialization..."
Start-Sleep -Seconds 5
Write-Host ""

# ============================================================================
# STEP 4: Verify Bot Health
# ============================================================================
Write-Step "STEP 4/6" "Checking Bot Health..."

$botLogs = docker logs trading-bot-app --tail 30 2>$null
if ($botLogs -match "RUNNING") {
    Write-Success "Bot is healthy and running"
    
    # Extract key info
    if ($botLogs -match "Loaded (\d+) sentiment records") {
        $sentimentCount = $matches[1]
        Write-Host "  Sentiment signals loaded: $sentimentCount" -ForegroundColor Gray
    }
    if ($botLogs -match "Whitelist with (\d+) pairs") {
        $pairCount = $matches[1]
        Write-Host "  Trading pairs: $pairCount" -ForegroundColor Gray
    }
} else {
    Write-Warning "Bot may still be initializing..."
}
Write-Host ""

# ============================================================================
# STEP 5: System Status Overview
# ============================================================================
Write-Step "STEP 5/6" "System Status Overview..."
Write-Host ""

Write-Host "  --- Trading Bot Container ---" -ForegroundColor Cyan
docker ps --filter "name=trading-bot-app" --format "    Name: {{.Names}}`n    Status: {{.Status}}`n    Ports: {{.Ports}}" 2>$null
Write-Host ""

Write-Host "  --- Data Files ---" -ForegroundColor Cyan
if (Test-Path "data\sentiment_signals.csv") {
    $fileInfo = Get-Item "data\sentiment_signals.csv"
    Write-Success "Sentiment data available"
    Write-Host "    Last modified: $($fileInfo.LastWriteTime)" -ForegroundColor Gray
    $lineCount = (Get-Content "data\sentiment_signals.csv" | Measure-Object -Line).Lines - 1
    Write-Host "    Signals: $lineCount" -ForegroundColor Gray
} else {
    Write-Warning "Sentiment data not found - run data pipeline first"
}

if (Test-Path "data\ohlcv_data") {
    $ohlcvFiles = Get-ChildItem "data\ohlcv_data\*.csv" -ErrorAction SilentlyContinue
    if ($ohlcvFiles) {
        Write-Success "Market data available ($($ohlcvFiles.Count) files)"
    }
}
Write-Host ""

# ============================================================================
# STEP 6: Launch Monitoring Dashboard
# ============================================================================
Write-Step "STEP 6/6" "Launching Trading Monitor..."
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Info "Starting live trading monitor in 3 seconds..."
Write-Host ""
Write-Host "  Monitor Features:" -ForegroundColor Yellow
Write-Host "    - Real-time balance tracking with P/L" -ForegroundColor White
Write-Host "    - Live trade entry/exit notifications" -ForegroundColor White
Write-Host "    - Performance statistics by pair" -ForegroundColor White
Write-Host "    - Recent activity feed (2-hour window)" -ForegroundColor White
Write-Host "    - Sentiment headline ticker" -ForegroundColor White
Write-Host "    - Color-coded indicators" -ForegroundColor White
Write-Host "    - Auto-refresh every 15 seconds" -ForegroundColor White
Write-Host ""
Write-Host "  Press Ctrl+C to stop monitoring" -ForegroundColor Magenta
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""

Start-Sleep -Seconds 3

# Sync database from container
Write-Info "Syncing database from container..."
docker cp trading-bot-app:/app/tradesv3.dryrun.sqlite . >$null 2>&1

# Launch monitor
python scripts/monitor_trading.py --interval 15

# ============================================================================
# Cleanup Message
# ============================================================================
Write-Host ""
Write-Host ""
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host "Monitor stopped. Trading bot is still running in background." -ForegroundColor Yellow
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Quick Commands:" -ForegroundColor White
Write-Host "  View logs:       " -ForegroundColor Gray -NoNewline
Write-Host "docker logs trading-bot-app --tail 50" -ForegroundColor Cyan
Write-Host "  Restart bot:     " -ForegroundColor Gray -NoNewline
Write-Host "docker restart trading-bot-app" -ForegroundColor Cyan
Write-Host "  Stop bot:        " -ForegroundColor Gray -NoNewline
Write-Host "docker stop trading-bot-app" -ForegroundColor Cyan
Write-Host "  Start monitor:   " -ForegroundColor Gray -NoNewline
Write-Host ".\start_monitor.bat" -ForegroundColor Cyan
Write-Host "  Restart system:  " -ForegroundColor Gray -NoNewline
Write-Host ".\start_cryptoboy.ps1" -ForegroundColor Cyan
Write-Host ""
Write-Host "VoidCat RDC - Excellence in Automated Trading" -ForegroundColor Green
Write-Host "================================================================================" -ForegroundColor Cyan
Write-Host ""
pause
