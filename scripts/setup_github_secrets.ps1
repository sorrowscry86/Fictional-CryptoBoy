# ============================================================================
# VoidCat RDC - CryptoBoy Trading System
# GitHub Secrets Setup Script
# Author: Wykeve Freeman (Sorrow Eternal)
# Date: November 1, 2025
# ============================================================================

Write-Host "=== VoidCat RDC - GitHub Secrets Setup ===" -ForegroundColor Cyan
Write-Host "Adding secrets to GitHub repository..." -ForegroundColor Yellow
Write-Host ""

# Repository information
$repo = "sorrowscry86/Fictional-CryptoBoy"

# Load .env file
if (-not (Test-Path ".env")) {
    Write-Host "ERROR: .env file not found!" -ForegroundColor Red
    exit 1
}

Write-Host "Reading secrets from .env file..." -ForegroundColor Green

# Parse .env file
$envContent = Get-Content ".env"
$secrets = @{}

foreach ($line in $envContent) {
    # Skip comments and empty lines
    if ($line -match '^\s*#' -or $line -match '^\s*$') {
        continue
    }
    
    # Parse key=value pairs
    if ($line -match '^([^=]+)=(.*)$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim()
        
        # Remove quotes if present
        $value = $value -replace '^"(.*)"$', '$1'
        $value = $value -replace "^'(.*)'$", '$1'
        
        $secrets[$key] = $value
    }
}

Write-Host "Found $($secrets.Count) environment variables" -ForegroundColor Green
Write-Host ""

# Critical secrets to add to GitHub
$criticalSecrets = @(
    "RABBITMQ_USER",
    "RABBITMQ_PASS",
    "COINBASE_API_KEY",
    "COINBASE_API_SECRET",
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "API_USERNAME",
    "API_PASSWORD",
    "JWT_SECRET_KEY"
)

Write-Host "Adding critical secrets to GitHub repository: $repo" -ForegroundColor Cyan
Write-Host ""

$successCount = 0
$failCount = 0

foreach ($secretName in $criticalSecrets) {
    if ($secrets.ContainsKey($secretName)) {
        $secretValue = $secrets[$secretName]
        
        # Skip empty values
        if ([string]::IsNullOrWhiteSpace($secretValue)) {
            Write-Host "  [SKIP] $secretName (empty value)" -ForegroundColor Yellow
            continue
        }
        
        Write-Host "  [ADD] $secretName..." -NoNewline
        
        try {
            # Use gh CLI to set secret
            $secretValue | gh secret set $secretName --repo $repo 2>&1 | Out-Null
            
            if ($LASTEXITCODE -eq 0) {
                Write-Host " ✓" -ForegroundColor Green
                $successCount++
            } else {
                Write-Host " ✗ (Failed)" -ForegroundColor Red
                $failCount++
            }
        } catch {
            Write-Host " ✗ (Error: $_)" -ForegroundColor Red
            $failCount++
        }
    } else {
        Write-Host "  [SKIP] $secretName (not found in .env)" -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "=== Summary ===" -ForegroundColor Cyan
Write-Host "  Successfully added: $successCount secrets" -ForegroundColor Green
Write-Host "  Failed: $failCount secrets" -ForegroundColor $(if ($failCount -gt 0) { "Red" } else { "Green" })
Write-Host ""

# Optional: Add all non-sensitive configuration as secrets too
Write-Host "Do you want to add all configuration variables? (y/N): " -NoNewline -ForegroundColor Yellow
$response = Read-Host

if ($response -eq 'y' -or $response -eq 'Y') {
    Write-Host ""
    Write-Host "Adding all configuration variables..." -ForegroundColor Cyan
    
    $configSecrets = @(
        "STAKE_CURRENCY",
        "STAKE_AMOUNT",
        "DRY_RUN",
        "MAX_OPEN_TRADES",
        "TIMEFRAME",
        "TRADING_PAIRS",
        "USE_HUGGINGFACE",
        "HUGGINGFACE_MODEL",
        "SENTIMENT_BUY_THRESHOLD",
        "SENTIMENT_SELL_THRESHOLD",
        "STOP_LOSS_PERCENTAGE",
        "TAKE_PROFIT_PERCENTAGE",
        "MAX_DAILY_TRADES",
        "RISK_PER_TRADE_PERCENTAGE",
        "PROJECT_NAME",
        "PROJECT_VERSION",
        "ORGANIZATION",
        "CONTACT_EMAIL",
        "DEVELOPER",
        "SUPPORT_CASHAPP"
    )
    
    foreach ($secretName in $configSecrets) {
        if ($secrets.ContainsKey($secretName)) {
            $secretValue = $secrets[$secretName]
            
            if ([string]::IsNullOrWhiteSpace($secretValue)) {
                continue
            }
            
            Write-Host "  [ADD] $secretName..." -NoNewline
            
            try {
                $secretValue | gh secret set $secretName --repo $repo 2>&1 | Out-Null
                
                if ($LASTEXITCODE -eq 0) {
                    Write-Host " ✓" -ForegroundColor Green
                } else {
                    Write-Host " ✗" -ForegroundColor Red
                }
            } catch {
                Write-Host " ✗" -ForegroundColor Red
            }
        }
    }
}

Write-Host ""
Write-Host "=== GitHub Secrets Setup Complete ===" -ForegroundColor Green
Write-Host ""
Write-Host "View secrets at: https://github.com/$repo/settings/secrets/actions" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Verify secrets in GitHub repository settings" -ForegroundColor White
Write-Host "  2. Update GitHub Actions workflows to use these secrets" -ForegroundColor White
Write-Host "  3. Never commit .env file to version control" -ForegroundColor White
Write-Host ""
