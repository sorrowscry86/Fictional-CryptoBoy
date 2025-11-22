# 🔐 API Credentials Security Guide

**CryptoBoy Trading Bot - Credential Management Best Practices**
**VoidCat RDC Security Standards**

---

## 📋 **Current State Assessment**

### What We Have Now ✅
- Environment variables via `.env` file
- `.env` excluded from git (`.gitignore`)
- `.env.example` template for documentation
- Environment variable validation at service startup
- No hardcoded credentials in code

### Security Risks ⚠️
1. **`.env` files in plaintext** on disk
2. **Credentials visible** in process environment (`ps aux`, `/proc/<pid>/environ`)
3. **No rotation mechanism** - credentials remain static
4. **No audit trail** - can't track who accessed what/when
5. **Shared secrets** - same `.env` file for all services

---

## 🎯 **Production-Ready Solutions**

### Option 1: HashiCorp Vault (Recommended for Production)

**Best for:** Enterprises, multi-service deployments, compliance requirements

#### Setup Steps:

1. **Install Vault:**
   ```bash
   # Docker-based Vault (development)
   docker run -d --name=vault \
     -p 8200:8200 \
     --cap-add=IPC_LOCK \
     vault server -dev

   # Export Vault address
   export VAULT_ADDR='http://localhost:8200'
   ```

2. **Store Secrets:**
   ```bash
   # Store exchange API credentials
   vault kv put secret/cryptoboy/binance \
     api_key="YOUR_API_KEY" \
     api_secret="YOUR_API_SECRET"

   # Store RabbitMQ credentials
   vault kv put secret/cryptoboy/rabbitmq \
     user="admin" \
     password="STRONG_PASSWORD_HERE"
   ```

3. **Integrate with Python:**
   ```python
   # services/common/vault_client.py
   import hvac
   import os

   class VaultClient:
       def __init__(self):
           self.client = hvac.Client(
               url=os.getenv("VAULT_ADDR", "http://localhost:8200"),
               token=os.getenv("VAULT_TOKEN")
           )

       def get_secret(self, path: str, key: str) -> str:
           """Retrieve secret from Vault"""
           response = self.client.secrets.kv.v2.read_secret_version(
               path=path
           )
           return response["data"]["data"][key]

   # Usage in services
   vault = VaultClient()
   binance_key = vault.get_secret("cryptoboy/binance", "api_key")
   binance_secret = vault.get_secret("cryptoboy/binance", "api_secret")
   ```

4. **Add to requirements:**
   ```txt
   hvac>=1.2.0  # HashiCorp Vault client
   ```

**Pros:**
- ✅ Industry-standard secret management
- ✅ Audit logging built-in
- ✅ Dynamic secret rotation
- ✅ Fine-grained access control
- ✅ Encryption at rest and in transit

**Cons:**
- ❌ Additional infrastructure to maintain
- ❌ Complexity for small deployments
- ❌ Requires learning curve

---

### Option 2: AWS Secrets Manager

**Best for:** AWS-hosted deployments, cloud-native applications

#### Setup Steps:

1. **Create Secrets in AWS Console:**
   ```bash
   # Using AWS CLI
   aws secretsmanager create-secret \
     --name cryptoboy/binance \
     --secret-string '{"api_key":"YOUR_KEY","api_secret":"YOUR_SECRET"}'
   ```

2. **Integrate with Python:**
   ```python
   # services/common/aws_secrets.py
   import boto3
   import json
   from botocore.exceptions import ClientError

   class AWSSecretsManager:
       def __init__(self, region_name="us-east-1"):
           self.client = boto3.client(
               "secretsmanager",
               region_name=region_name
           )

       def get_secret(self, secret_name: str) -> dict:
           """Retrieve secret from AWS Secrets Manager"""
           try:
               response = self.client.get_secret_value(
                   SecretId=secret_name
               )
               return json.loads(response["SecretString"])
           except ClientError as e:
               raise Exception(f"Failed to retrieve secret: {e}")

   # Usage
   secrets = AWSSecretsManager()
   binance_creds = secrets.get_secret("cryptoboy/binance")
   api_key = binance_creds["api_key"]
   api_secret = binance_creds["api_secret"]
   ```

3. **IAM Permissions:**
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "secretsmanager:GetSecretValue",
           "secretsmanager:DescribeSecret"
         ],
         "Resource": "arn:aws:secretsmanager:*:*:secret:cryptoboy/*"
       }
     ]
   }
   ```

**Pros:**
- ✅ Fully managed (no infrastructure)
- ✅ Automatic rotation support
- ✅ Integrated with AWS IAM
- ✅ Pay-per-secret pricing ($0.40/month + API calls)

**Cons:**
- ❌ AWS-specific (vendor lock-in)
- ❌ Requires AWS account
- ❌ Additional cost

---

### Option 3: Docker Secrets (Docker Swarm)

**Best for:** Docker Swarm deployments

#### Setup Steps:

1. **Create Docker Secrets:**
   ```bash
   echo "YOUR_API_KEY" | docker secret create binance_api_key -
   echo "YOUR_API_SECRET" | docker secret create binance_api_secret -
   ```

2. **Mount in docker-compose:**
   ```yaml
   version: '3.8'
   services:
     trading-bot:
       image: cryptoboy:latest
       secrets:
         - binance_api_key
         - binance_api_secret

   secrets:
     binance_api_key:
       external: true
     binance_api_secret:
       external: true
   ```

3. **Read in Application:**
   ```python
   def read_docker_secret(secret_name: str) -> str:
       """Read secret from Docker mounted file"""
       secret_path = f"/run/secrets/{secret_name}"
       try:
           with open(secret_path, "r") as f:
               return f.read().strip()
       except FileNotFoundError:
           # Fallback to environment variable
           return os.getenv(secret_name.upper(), "")

   # Usage
   binance_key = read_docker_secret("binance_api_key")
   binance_secret = read_docker_secret("binance_api_secret")
   ```

**Pros:**
- ✅ Native Docker integration
- ✅ Secrets encrypted at rest
- ✅ No external dependencies

**Cons:**
- ❌ Requires Docker Swarm (not Compose)
- ❌ Limited rotation capabilities
- ❌ Basic secret management

---

## 🛡️ **Interim Security Measures** (Until Vault Deployed)

### 1. Encrypt .env Files

```bash
# Encrypt .env with GPG
gpg --symmetric --cipher-algo AES256 .env
# Creates .env.gpg

# Decrypt at runtime
gpg --quiet --decrypt .env.gpg > .env

# Add to .gitignore
echo ".env.gpg" >> .gitignore
```

### 2. Restrict File Permissions

```bash
# Owner read/write only
chmod 600 .env

# Verify
ls -l .env
# Output: -rw------- 1 user user 245 Nov 22 10:00 .env
```

### 3. Use Environment-Specific .env Files

```bash
# Separate files per environment
.env.development  # Testnet credentials
.env.staging      # Staging API keys
.env.production   # Production secrets (NEVER commit)

# Load appropriate file
docker-compose --env-file .env.production up
```

### 4. Implement Secret Rotation

```python
# scripts/rotate_api_keys.py
"""
Manual script to rotate API keys
Run monthly or after suspected compromise
"""

def rotate_binance_keys():
    # 1. Generate new API key in Binance
    # 2. Update .env file
    # 3. Restart services
    # 4. Revoke old API key after verification
    pass
```

### 5. Add Secret Scanning Pre-Commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

# Detect potential secrets in staged files
if git diff --cached | grep -E "(api_key|api_secret|password).*=.*[a-zA-Z0-9]{20,}"; then
    echo "❌ ERROR: Potential secret detected in commit!"
    echo "Please use environment variables instead."
    exit 1
fi
```

---

## 📊 **Comparison Matrix**

| Feature | `.env` Files | Docker Secrets | AWS Secrets | HashiCorp Vault |
|---------|-------------|----------------|-------------|-----------------|
| **Setup Time** | 5 min | 15 min | 30 min | 1-2 hours |
| **Cost** | Free | Free | ~$0.40/secret/month | Free (self-hosted) |
| **Rotation** | Manual | Manual | Automatic | Automatic |
| **Audit Logs** | ❌ | ❌ | ✅ | ✅ |
| **Encryption at Rest** | ❌ | ✅ | ✅ | ✅ |
| **Access Control** | File permissions | Docker RBAC | AWS IAM | Policy-based |
| **Production Ready** | ⚠️ (with encryption) | ✅ | ✅ | ✅ |

---

## 🎯 **Recommended Implementation Path**

### Phase 1: Immediate (Today)
1. ✅ Restrict `.env` file permissions (`chmod 600`)
2. ✅ Verify `.env` in `.gitignore`
3. ✅ Add secret scanning pre-commit hook
4. ✅ Document credential rotation procedure

### Phase 2: Short-term (1-2 weeks)
1. Encrypt `.env` files with GPG
2. Implement environment-specific `.env` files
3. Add monthly key rotation reminders
4. Enable 2FA on exchange accounts

### Phase 3: Production (Before Live Trading)
1. **Deploy HashiCorp Vault** (recommended) or AWS Secrets Manager
2. Migrate all credentials to vault
3. Implement automatic secret rotation
4. Enable audit logging
5. Set up monitoring alerts for secret access

---

## 🚨 **Security Incident Response**

### If API Keys Compromised:

1. **Immediately Disable Keys** in exchange dashboard
2. **Generate New Keys** with read-only permissions initially
3. **Check Trading History** for unauthorized trades
4. **Rotate ALL Secrets** (RabbitMQ, Redis, etc.)
5. **Enable IP Whitelisting** on new API keys
6. **Investigate** how compromise occurred
7. **Update `.env`** with new credentials
8. **Restart Services** with new keys

---

## 📝 **Compliance Checklist**

For production deployments requiring compliance (PCI-DSS, SOC 2, etc.):

- [ ] Secrets encrypted at rest
- [ ] Secrets encrypted in transit (TLS)
- [ ] Access audit logs enabled
- [ ] Secret rotation implemented (90-day max)
- [ ] Least-privilege access control
- [ ] Secrets never logged or printed
- [ ] No secrets in error messages
- [ ] Secrets not visible in process list
- [ ] Backup secrets encrypted
- [ ] Secret scanning in CI/CD

---

## 🔗 **Additional Resources**

- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)
- [HashiCorp Vault Documentation](https://www.vaultproject.io/docs)
- [AWS Secrets Manager Guide](https://docs.aws.amazon.com/secretsmanager/)
- [Docker Secrets Documentation](https://docs.docker.com/engine/swarm/secrets/)
- [git-secrets Tool](https://github.com/awslabs/git-secrets)

---

**Last Updated:** 2025-11-22
**Maintainer:** VoidCat RDC Security Team
**Status:** Active guidance for CryptoBoy deployments
