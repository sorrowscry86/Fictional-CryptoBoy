# Health Check Fix Proposal
**Date**: October 31, 2025  
**Issue**: Docker health check failing with 401 Unauthorized  
**Status**: READY FOR APPROVAL  
**Priority**: CRITICAL 🔴

---

## Root Cause Analysis

**Problem**: `trading-bot-app` container reports "unhealthy" despite operational status

**Technical Cause**:
```
Error: curl: (22) The requested URL returned error: 401
Endpoint: http://localhost:8080/api/v1/ping
Failing Streak: 74+ consecutive failures
```

**Why It's Failing**:
1. Freqtrade REST API requires authentication (username/password)
2. API credentials (`API_USERNAME`, `API_PASSWORD`, `JWT_SECRET_KEY`) NOT configured in `.env`
3. Health check curl command doesn't provide authentication
4. Result: HTTP 401 Unauthorized on every health check attempt

---

## Impact Assessment

**Current State**:
- ❌ Docker reports container as "unhealthy"
- ✅ Bot is actually running correctly (heartbeats, data collection active)
- ⚠️ False negative prevents reliable monitoring
- 🚫 Blocks Task 1.2 (Coinbase API validation)
- 🚫 Blocks all Tier 2 monitoring tasks

**Risk Level**: MEDIUM
- No immediate operational impact (bot functions normally)
- Long-term risk: Can't distinguish real failures from false alarms
- Monitoring infrastructure unreliable until fixed

---

## Proposed Solution Options

### **Option 1: Add API Credentials + Authenticated Health Check** (RECOMMENDED)
**Approach**: Configure proper API security with authenticated health check

**Changes Required**:
1. Add to `.env`:
```bash
# Freqtrade API Security
API_USERNAME=cryptoboy_admin
API_PASSWORD=<generate_secure_password>
JWT_SECRET_KEY=<generate_jwt_secret>
```

2. Update `docker-compose.production.yml` (trading-bot service):
```yaml
environment:
  - API_USERNAME=${API_USERNAME:?API username not set}
  - API_PASSWORD=${API_PASSWORD:?API password not set}
  - JWT_SECRET_KEY=${JWT_SECRET_KEY:?JWT secret not set}
```

3. Update health check with authentication:
```yaml
healthcheck:
  test: ["CMD", "sh", "-c", "curl -f -u \"$${API_USERNAME}:$${API_PASSWORD}\" http://localhost:8080/api/v1/ping || exit 1"]
  interval: 60s
  timeout: 10s
  retries: 3
  start_period: 120s
```

**Pros**:
- ✅ Maintains API security
- ✅ Accurate health reporting
- ✅ Production-ready solution

**Cons**:
- ⏱️ Requires generating secure credentials
- ⏱️ Requires container restart

**Effort**: 15 minutes  
**Risk**: LOW (environment variable addition only)

---

### **Option 2: Simplified TCP Health Check**
**Approach**: Check if API port is listening (no authentication needed)

**Changes Required**:
Update `docker-compose.production.yml` health check:
```yaml
healthcheck:
  test: ["CMD-SHELL", "nc -z localhost 8080 || exit 1"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 60s
```

**Pros**:
- ✅ Quick fix (5 minutes)
- ✅ No credential management
- ✅ Simple and reliable

**Cons**:
- ⚠️ Less precise (only checks port, not API functionality)
- ⚠️ Won't catch API-specific failures

**Effort**: 5 minutes  
**Risk**: LOW

---

### **Option 3: Process-Based Health Check**
**Approach**: Check if Freqtrade process is running

**Changes Required**:
Update `docker-compose.production.yml` health check:
```yaml
healthcheck:
  test: ["CMD-SHELL", "pgrep -f freqtrade || exit 1"]
  interval: 30s
  timeout: 5s
  retries: 3
  start_period: 60s
```

**Pros**:
- ✅ Very simple
- ✅ Direct process verification

**Cons**:
- ⚠️ Won't catch hung processes
- ⚠️ Doesn't verify API functionality

**Effort**: 5 minutes  
**Risk**: LOW

---

## Recommendation

**PRIMARY**: Option 1 (Authenticated Health Check)
- Production-grade security
- Accurate health monitoring
- Scalable for future features

**FALLBACK**: Option 2 (TCP Health Check)
- If credentials cannot be generated immediately
- Temporary solution until Option 1 implemented

---

## Implementation Steps (Option 1)

### Step 1: Generate Credentials (5 min)
```bash
# Generate secure API password (32 characters)
openssl rand -base64 32

# Generate JWT secret key (64 characters)
openssl rand -base64 64
```

### Step 2: Update .env (2 min)
Add credentials to `.env` file (secured by `.gitignore`)

### Step 3: Update docker-compose.production.yml (3 min)
- Add environment variables to trading-bot service
- Update healthcheck with authentication

### Step 4: Restart Container (5 min)
```bash
docker-compose -f docker-compose.production.yml down trading-bot-app
docker-compose -f docker-compose.production.yml up -d trading-bot-app
```

### Step 5: Verify Fix (2 min)
```bash
docker ps --filter "name=trading-bot-app" --format "{{.Status}}"
# Should show: Up X minutes (healthy)
```

**Total Time**: 15 minutes  
**Downtime**: ~30 seconds (container restart)

---

## Security Considerations

✅ **Credentials Storage**: `.env` file protected by `.gitignore`  
✅ **Environment Variables**: Passed securely via Docker environment  
✅ **No Hardcoding**: Credentials never in source code  
⚠️ **Action Required**: Verify `.gitignore` includes `.env`  
⚠️ **Recommendation**: Use strong passwords (32+ characters)

---

## Validation Criteria

**Success Metrics**:
- ✅ Docker health check returns "healthy" status
- ✅ `docker ps` shows green health indicator
- ✅ Health check logs show HTTP 200 responses
- ✅ No 401 errors in health check output
- ✅ Trading bot continues normal operation

**Test Commands**:
```bash
# Check health status
docker ps -a --filter "name=trading-bot-app"

# Verify health check logs
docker inspect trading-bot-app --format='{{json .State.Health}}' | jq

# Test endpoint manually with credentials
docker exec trading-bot-app curl -f -u "username:password" http://localhost:8080/api/v1/ping
```

---

## Rollback Plan

If issues occur:
1. Revert to previous docker-compose.production.yml (git checkout)
2. Remove added environment variables from .env
3. Restart container
4. Report issues to Wykeve/Beatrice

**Rollback Time**: <5 minutes

---

## Approval Required

**Wykeve** - Confirm approach and authorize implementation  
**Beatrice** - Review security implications

**Status**: ⏳ AWAITING APPROVAL

---

**Next Steps After Approval**:
1. Implement chosen option
2. Validate health check success
3. Update operational baseline documentation
4. Proceed to Task 1.2 (Coinbase API validation)
