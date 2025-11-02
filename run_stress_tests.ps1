# CryptoBoy Stress Test Suite - PowerShell Runner
# Runs comprehensive performance and reliability tests

$ErrorActionPreference = "Continue"

# Create results directory
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$resultsDir = "tests\stress_tests\results_$timestamp"
New-Item -ItemType Directory -Force -Path $resultsDir | Out-Null

Write-Host "`n========================================"  -ForegroundColor Green
Write-Host "CryptoBoy Stress Test Suite" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Results will be saved to: $resultsDir`n" -ForegroundColor Yellow

# Counter for test results
$testsPassed = 0
$testsFailed = 0

# Set environment variables for localhost access
$env:RABBITMQ_HOST = "localhost"
$env:REDIS_HOST = "localhost"
$env:OLLAMA_HOST = "http://localhost:11434"

# Function to run a test
function Run-Test {
    param(
        [string]$TestName,
        [string]$TestCommand,
        [string]$LogFile
    )
    
    Write-Host "`nRunning: $TestName" -ForegroundColor Yellow
    "Started at: $(Get-Date)" | Out-File -FilePath $LogFile
    
    try {
        Invoke-Expression $TestCommand *>&1 | Tee-Object -FilePath $LogFile -Append
        if ($LASTEXITCODE -eq 0) {
            Write-Host "✓ $TestName completed successfully" -ForegroundColor Green
            return $true
        } else {
            Write-Host "✗ $TestName failed (exit code: $LASTEXITCODE)" -ForegroundColor Red
            return $false
        }
    } catch {
        Write-Host "✗ $TestName failed with exception: $_" -ForegroundColor Red
        $_ | Out-File -FilePath $LogFile -Append
        return $false
    }
}

Write-Host "1. RabbitMQ Load Test" -ForegroundColor Green
Write-Host "   Testing message queue with 10,000 messages..."
if (Run-Test -TestName "rabbitmq_load_test" `
             -TestCommand "python tests/stress_tests/rabbitmq_load_test.py --messages 10000 --mode parallel" `
             -LogFile "$resultsDir\rabbitmq_load_test.log") {
    $testsPassed++
} else {
    $testsFailed++
}

Write-Host "`n2. Redis Stress Test" -ForegroundColor Green
Write-Host "   Testing cache with rapid sentiment updates..."
if (Run-Test -TestName "redis_stress_test" `
             -TestCommand "python tests/stress_tests/redis_stress_test.py --operations 10000 --mode parallel" `
             -LogFile "$resultsDir\redis_stress_test.log") {
    $testsPassed++
} else {
    $testsFailed++
}

Write-Host "`n3. Sentiment Processing Load Test" -ForegroundColor Green
Write-Host "   Testing LLM with 100 concurrent articles..."
if (Run-Test -TestName "sentiment_load_test" `
             -TestCommand "python tests/stress_tests/sentiment_load_test.py --articles 100 --mode parallel --workers 4" `
             -LogFile "$resultsDir\sentiment_load_test.log") {
    $testsPassed++
} else {
    $testsFailed++
}

Write-Host "`n4. End-to-End Latency Test" -ForegroundColor Green
Write-Host "   Measuring pipeline latency (RSS → LLM → Redis)..."
if (Run-Test -TestName "latency_measurement" `
             -TestCommand "python tests/monitoring/latency_monitor.py --measurements 20 --interval 10" `
             -LogFile "$resultsDir\latency_measurement.log") {
    $testsPassed++
} else {
    $testsFailed++
}

# Copy JSON reports to results directory
Write-Host "`nCopying test reports..."
Get-ChildItem -Path "tests\stress_tests\*.json" -ErrorAction SilentlyContinue | Copy-Item -Destination $resultsDir
Get-ChildItem -Path "tests\monitoring\*.json" -ErrorAction SilentlyContinue | Copy-Item -Destination $resultsDir

# Generate summary report
Write-Host "`n========================================"  -ForegroundColor Green
Write-Host "Test Summary" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "Tests Passed: $testsPassed" -ForegroundColor Green
Write-Host "Tests Failed: $testsFailed" -ForegroundColor Red
Write-Host "Results Directory: $resultsDir`n" -ForegroundColor Yellow

# Check if all tests passed
if ($testsFailed -eq 0) {
    Write-Host "✓ All stress tests passed!" -ForegroundColor Green
    exit 0
} else {
    Write-Host "✗ Some tests failed. Check logs in $resultsDir" -ForegroundColor Red
    exit 1
}
