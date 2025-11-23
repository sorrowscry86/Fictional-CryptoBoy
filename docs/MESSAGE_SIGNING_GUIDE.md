# 🔏 Message Signing & Authentication Guide

**CryptoBoy Trading Bot - Internal Message Security**
**VoidCat RDC Security Standards**

---

## 📋 **Threat Model**

### Current State
- RabbitMQ messages are **NOT signed**
- Any service with RabbitMQ credentials can publish to any queue
- **Spoofing Risk:** Malicious service could publish fake sentiment signals → bad trades
- **Tampering Risk:** Messages could be modified in transit (less likely with TLS)
- **Replay Risk:** Old messages could be republished out of context

### Why This Matters
```
Scenario: Compromised News Poller Service
┌──────────────────────────────────────────────────────────┐
│ Attacker publishes fake "Bitcoin banned" news article    │
│ ↓                                                        │
│ Sentiment Processor analyzes (-0.95 bearish)            │
│ ↓                                                        │
│ Trading Bot receives signal, SELLS all BTC positions     │
│ ↓                                                        │
│ Result: Attacker profits from manufactured sell pressure│
└──────────────────────────────────────────────────────────┘
```

**With Message Signing:**
- Fake messages rejected (invalid signature)
- Only authorized services can publish valid messages
- Tampering detected immediately

---

## 🔐 **HMAC Signature Implementation**

### Architecture Overview

```
┌─────────────────┐
│  News Poller    │
│                 │
│  1. Create msg  │
│  2. Sign msg    │ ← HMAC-SHA256(msg + secret)
│  3. Publish     │
└────────┬────────┘
         │ RabbitMQ Queue
         ↓
┌─────────────────┐
│ Sentiment Proc  │
│                 │
│  1. Receive msg │
│  2. Verify sig  │ ← Recompute HMAC, compare
│  3. Process     │ ← Only if signature valid
└─────────────────┘
```

### Shared Secret Management

**Option 1: Environment Variable (Simple)**
```bash
# .env
MESSAGE_SIGNING_SECRET=your-256-bit-random-secret-here
```

**Option 2: Vault Integration (Production)**
```python
from services.common.vault_client import VaultClient

vault = VaultClient()
signing_secret = vault.get_secret("cryptoboy/signing", "secret_key")
```

---

## 💻 **Implementation: Message Signing Module**

Create `services/common/message_signing.py`:

```python
"""
Message Signing Module - HMAC-based authentication for internal messages
Prevents spoofing and tampering of RabbitMQ messages
"""

import hashlib
import hmac
import json
import os
from typing import Any, Dict, Optional
from datetime import datetime, timedelta


class MessageSigner:
    """
    HMAC-SHA256 message signing and verification.

    Security properties:
    - Authenticity: Only services with secret can create valid signatures
    - Integrity: Any modification to message invalidates signature
    - Replay protection: Timestamp prevents old message reuse
    """

    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize message signer.

        Args:
            secret_key: HMAC secret (256-bit recommended).
                       If None, reads from MESSAGE_SIGNING_SECRET env var.

        Raises:
            ValueError: If secret_key not provided and env var not set
        """
        self.secret_key = secret_key or os.getenv("MESSAGE_SIGNING_SECRET")

        if not self.secret_key:
            raise ValueError(
                "MESSAGE_SIGNING_SECRET not set. "
                "Generate with: openssl rand -hex 32"
            )

        if len(self.secret_key) < 32:  # 256 bits = 32 bytes hex
            raise ValueError(
                f"Secret key too short ({len(self.secret_key)} chars). "
                f"Use at least 32 hex characters (256 bits)"
            )

        self.secret_bytes = self.secret_key.encode("utf-8")

    def sign_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign a message with HMAC-SHA256.

        Adds signature and timestamp to message:
        {
            ...original message fields...,
            "_signature": "hex_hmac_value",
            "_signed_at": "2025-11-22T10:30:00Z"
        }

        Args:
            message: Original message dictionary

        Returns:
            Message with signature and timestamp added
        """
        # Add timestamp (for replay protection)
        signed_message = message.copy()
        signed_message["_signed_at"] = datetime.utcnow().isoformat() + "Z"

        # Compute signature over canonical JSON (sorted keys for consistency)
        canonical_json = json.dumps(signed_message, sort_keys=True)
        signature = hmac.new(
            self.secret_bytes,
            canonical_json.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # Add signature to message
        signed_message["_signature"] = signature

        return signed_message

    def verify_message(
        self,
        message: Dict[str, Any],
        max_age_seconds: int = 300
    ) -> tuple[bool, Optional[str]]:
        """
        Verify message signature and freshness.

        Args:
            message: Message to verify (must contain _signature and _signed_at)
            max_age_seconds: Maximum message age (default 5 minutes)

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])

        Examples:
            >>> signer = MessageSigner()
            >>> valid, error = signer.verify_message(msg)
            >>> if not valid:
            >>>     logger.error(f"Invalid message: {error}")
        """
        # Check required fields
        if "_signature" not in message:
            return False, "Missing _signature field"
        if "_signed_at" not in message:
            return False, "Missing _signed_at timestamp"

        # Extract and remove signature (to recompute)
        received_signature = message.pop("_signature")
        signed_at_str = message.get("_signed_at")

        # Recompute signature
        canonical_json = json.dumps(message, sort_keys=True)
        expected_signature = hmac.new(
            self.secret_bytes,
            canonical_json.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

        # Constant-time comparison (prevent timing attacks)
        if not hmac.compare_digest(received_signature, expected_signature):
            return False, "Signature verification failed"

        # Check message age (replay protection)
        try:
            signed_at = datetime.fromisoformat(signed_at_str.rstrip("Z"))
            age_seconds = (datetime.utcnow() - signed_at).total_seconds()

            if age_seconds > max_age_seconds:
                return False, f"Message too old ({int(age_seconds)}s > {max_age_seconds}s)"

            if age_seconds < -60:  # Allow 1 min clock skew
                return False, "Message timestamp in future (clock skew)"

        except (ValueError, AttributeError) as e:
            return False, f"Invalid timestamp format: {e}"

        # Signature valid and message fresh
        return True, None


# Global signer instance (lazy initialization)
_signer_instance: Optional[MessageSigner] = None


def get_message_signer() -> MessageSigner:
    """Get or create global message signer instance"""
    global _signer_instance
    if _signer_instance is None:
        _signer_instance = MessageSigner()
    return _signer_instance


def sign(message: Dict[str, Any]) -> Dict[str, Any]:
    """Convenience function to sign a message"""
    return get_message_signer().sign_message(message)


def verify(message: Dict[str, Any], max_age_seconds: int = 300) -> tuple[bool, Optional[str]]:
    """Convenience function to verify a message"""
    return get_message_signer().verify_message(message, max_age_seconds)
```

---

## 🔧 **Integration Guide**

### Step 1: Generate Signing Secret

```bash
# Generate 256-bit secret
openssl rand -hex 32
# Output: a4f3c2b1e9d8f7a6... (64 hex characters)

# Add to .env
echo "MESSAGE_SIGNING_SECRET=<generated_secret>" >> .env
```

### Step 2: Update RabbitMQ Client

Modify `services/common/rabbitmq_client.py`:

```python
from services.common.message_signing import sign, verify

class RabbitMQClient:
    # ... existing code ...

    def publish(self, queue_name: str, message: dict, **kwargs):
        """Publish message with signature"""
        # Sign message before publishing
        signed_message = sign(message)

        # Convert to JSON and publish
        message_bytes = json.dumps(signed_message).encode("utf-8")
        # ... rest of publish logic ...

    def consume(self, queue_name: str, callback, **kwargs):
        """Consume messages with signature verification"""

        def verified_callback(ch, method, properties, body):
            # Parse message
            message = json.loads(body.decode("utf-8"))

            # Verify signature
            is_valid, error = verify(message, max_age_seconds=300)

            if not is_valid:
                logger.error(
                    f"SECURITY: Invalid message signature from queue '{queue_name}': {error}",
                    extra={"queue": queue_name, "error": error}
                )
                # Reject message (don't requeue - likely malicious)
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
                return

            # Signature valid - process message
            callback(ch, method, properties, message)

        # ... rest of consume logic with verified_callback ...
```

### Step 3: Update All Services

**News Poller:**
```python
# services/data_ingestor/news_poller.py
# No changes needed - publish() automatically signs
self.rabbitmq.publish("raw_news_data", article_data)
```

**Sentiment Processor:**
```python
# services/sentiment_analyzer/sentiment_processor.py
# No changes needed - consume() automatically verifies
self.rabbitmq.consume("raw_news_data", callback)
```

**All other services inherit signing automatically!**

---

## ⚡ **Performance Considerations**

### Overhead Analysis

```python
import timeit

# Benchmark HMAC signing
def benchmark():
    signer = MessageSigner("test_secret_key_256_bits_long_hex")
    message = {"pair": "BTC/USDT", "score": 0.75, "headline": "..."}

    # Signing
    sign_time = timeit.timeit(
        lambda: signer.sign_message(message),
        number=10000
    )
    print(f"Signing: {sign_time/10000*1000:.3f} ms per message")

    # Verification
    signed = signer.sign_message(message)
    verify_time = timeit.timeit(
        lambda: signer.verify_message(signed.copy()),
        number=10000
    )
    print(f"Verification: {verify_time/10000*1000:.3f} ms per message")

# Expected output:
# Signing: 0.05-0.1 ms per message
# Verification: 0.05-0.1 ms per message
```

**Impact:**
- **Negligible** for CryptoBoy's message rate (~10-100 messages/minute)
- **HMAC-SHA256 is fast:** Millions of operations/second on modern CPUs
- **Acceptable** even for high-frequency trading (1000s messages/second)

---

## 🛡️ **Security Best Practices**

### 1. Secret Rotation

```python
# Rotate signing secret quarterly
# scripts/rotate_signing_secret.py

def rotate_secret():
    """
    1. Generate new secret
    2. Update MESSAGE_SIGNING_SECRET in .env
    3. Restart all services simultaneously (brief downtime)
    4. Old messages in queues will be rejected (acceptable)
    """
    new_secret = secrets.token_hex(32)  # 256 bits
    # Update .env, restart services
```

### 2. Monitoring Signature Failures

```python
# Add metrics
SIGNATURE_FAILURES = Counter(
    "message_signature_failures_total",
    "Messages rejected due to invalid signatures",
    ["queue", "service"]
)

# Alert if > 5 failures/minute (possible attack)
if signature_failures > 5:
    send_alert("Possible message spoofing attack detected!")
```

### 3. Key Separation

```bash
# Different keys per environment
MESSAGE_SIGNING_SECRET_DEV=...
MESSAGE_SIGNING_SECRET_STAGING=...
MESSAGE_SIGNING_SECRET_PROD=...
```

---

## 📊 **Deployment Checklist**

- [ ] Generate 256-bit signing secret (`openssl rand -hex 32`)
- [ ] Add `MESSAGE_SIGNING_SECRET` to `.env` (all services)
- [ ] Deploy `services/common/message_signing.py`
- [ ] Update `RabbitMQClient.publish()` to sign messages
- [ ] Update `RabbitMQClient.consume()` to verify signatures
- [ ] Test with one service (news poller → sentiment processor)
- [ ] Roll out to all services simultaneously
- [ ] Monitor signature failure metrics
- [ ] Document secret rotation procedure
- [ ] Add signature verification to CI/CD tests

---

## 🔗 **Testing**

```python
# tests/test_message_signing.py

import pytest
from services.common.message_signing import MessageSigner

def test_sign_and_verify():
    """Test basic signing and verification"""
    signer = MessageSigner("test_secret_key_with_256_bits_hex")

    message = {"pair": "BTC/USDT", "score": 0.75}
    signed = signer.sign_message(message)

    # Should verify successfully
    is_valid, error = signer.verify_message(signed)
    assert is_valid
    assert error is None

def test_tampered_message_rejected():
    """Test that tampered messages are rejected"""
    signer = MessageSigner("test_secret_key_with_256_bits_hex")

    message = {"pair": "BTC/USDT", "score": 0.75}
    signed = signer.sign_message(message)

    # Tamper with message
    signed["score"] = -0.95  # Change bullish to bearish!

    # Verification should fail
    is_valid, error = signer.verify_message(signed)
    assert not is_valid
    assert "Signature verification failed" in error

def test_old_message_rejected():
    """Test replay protection (old messages rejected)"""
    signer = MessageSigner("test_secret_key_with_256_bits_hex")

    message = {"pair": "BTC/USDT", "score": 0.75}
    signed = signer.sign_message(message)

    # Modify timestamp to 10 minutes ago
    from datetime import datetime, timedelta
    old_time = datetime.utcnow() - timedelta(minutes=10)
    signed["_signed_at"] = old_time.isoformat() + "Z"

    # Should be rejected (> 5 minute max_age)
    is_valid, error = signer.verify_message(signed, max_age_seconds=300)
    assert not is_valid
    assert "too old" in error
```

---

## 🎯 **Implementation Phases**

### Phase 1: Foundation (1-2 days)
1. ✅ Create `message_signing.py` module
2. ✅ Generate signing secret
3. ✅ Write unit tests
4. ✅ Benchmark performance

### Phase 2: Integration (2-3 days)
1. Update `RabbitMQClient` with signing/verification
2. Test with one service pair (news poller → sentiment processor)
3. Add monitoring for signature failures
4. Document rollout procedure

### Phase 3: Deployment (1 day)
1. Deploy to staging environment
2. Monitor for 24 hours
3. Roll out to production (all services simultaneously)
4. Enable alerting for signature failures

---

## ⚠️ **Alternatives & Trade-offs**

### Option 1: RabbitMQ TLS Client Certificates
**Pros:** Service authentication built into RabbitMQ
**Cons:** Doesn't prevent compromised service from publishing fake data

### Option 2: Service Mesh (Istio/Linkerd)
**Pros:** mTLS for all inter-service communication
**Cons:** Significant infrastructure complexity

### Option 3: Message Signing (This Guide)
**Pros:** Application-level security, simple implementation, portable
**Cons:** Requires secret distribution

**Recommendation:** Use message signing (this guide) + RabbitMQ TLS for defense in depth.

---

## 📚 **References**

- [HMAC-SHA256 Specification (RFC 2104)](https://datatracker.ietf.org/doc/html/rfc2104)
- [OWASP API Security - Message Integrity](https://owasp.org/www-project-api-security/)
- [Python HMAC Module Documentation](https://docs.python.org/3/library/hmac.html)
- [RabbitMQ Security Best Practices](https://www.rabbitmq.com/security.html)

---

**Last Updated:** 2025-11-22
**Maintainer:** VoidCat RDC Security Team
**Status:** Ready for implementation
