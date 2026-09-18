# Subscription Abuse Hardening Guide

> Defense-in-depth for developers and subscription platforms against IAP abuse. By #napster.

---

## 1. Layered defense model

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: Client protections (StoreKit 2 + app security)    │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Server-side verification (App Store Server API)   │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Subscription-platform risk (RevenueCat/managed)   │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: Account & behavioral analytics (anomaly + prof)   │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Layer 1: Client protections

### 2.1 StoreKit 2 verification

```swift
// Always use VerificationResult
let result = try await product.purchase()
switch result {
case .success(let verification):
    switch verification {
    case .verified(let transaction):
        // ✅ signature valid, continue
    case .unverified(_, let error):
        // ❌ signature invalid, reject
        return
    }
}
```

**Keys**:
- StoreKit 2 verifies JWS signatures automatically (system API, not skippable)
- `unverified` results must always be rejected

### 2.2 SSL pinning

```swift
let session = URLSession(configuration: .default, delegate: self, delegateQueue: nil)

func urlSession(
    _ session: URLSession,
    didReceive challenge: URLAuthenticationChallenge
) async -> (URLSession.AuthChallengeDisposition, URLCredential?) {
    guard let serverTrust = challenge.protectionSpace.serverTrust,
          let cert = SecTrustGetCertificateAtIndex(serverTrust, 0) else {
        return (.cancelAuthenticationChallenge, nil)
    }
    let data = SecCertificateCopyData(cert) as Data
    // compare against pinned fingerprint; mismatch → cancel
    if data != expectedPinnedFingerprint {
        return (.cancelAuthenticationChallenge, nil)
    }
    return (.useCredential, URLCredential(trust: serverTrust))
}
```

**Note**: SSL pinning can be bypassed on jailbroken devices (SSL Kill Switch 3). Never rely on it alone.

### 2.3 Jailbreak detection (optional)

```swift
func isDeviceJailbroken() -> Bool {
    let paths = ["/Applications/Cydia.app", "/usr/sbin/sshd", "/etc/apt", "/private/var/lib/apt/"]
    if paths.contains(where: { FileManager.default.fileExists(atPath: $0) }) { return true }
    // writable system dir test
    let test = "/private/jailbreak_test.txt"
    do { try "x".write(toFile: test, atomically: true, encoding: .utf8)
         try FileManager.default.removeItem(atPath: test)
         return true } catch { return false }
}
```

Jailbreak detection raises attacker cost but is not 100% reliable.

---

## 3. Layer 2: Server-side verification

### 3.1 App Store Server API flow

```python
import requests

def verify_app_store_receipt(receipt_data: str, apple_issuer: str, apple_key_id: str, apple_private_key: bytes) -> dict:
    """Verify a receipt server-side with the App Store Server API."""
    # 1. build a signed JWT for App Store Connect API
    # 2. call status endpoint with transactionId
    # 3. check bundleId, environment, expiry, product
    # 4. ensure transactionId is unique in your DB
    ...
```

### 3.2 Critical checks

| Check | Purpose | Defends against |
|-------|---------|-----------------|
| Certificate chain | Verify against Apple Root CA | Forged receipts |
| Signature | Verify JWS/receipt signature | Tampering |
| Transaction ID uniqueness | One-time use only | Receipt replay |
| Bundle ID | Receipt belongs to this app | Cross-app mixing |
| Environment | Production vs Sandbox | Test tokens in prod |
| Purchase date sanity | Reasonable recency | Time manipulation |

### 3.3 Sample verification service

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ReceiptBody(BaseModel):
    receipt_data: str
    user_id: str
    product_id: str

@app.post("/verify-receipt")
async def verify_receipt(req: ReceiptBody):
    verification = await call_app_store_server(req.receipt_data)
    if not verification.valid:
        raise HTTPException(400, "Invalid receipt")
    if not check_transaction_uniqueness(verification.transaction_id):
        raise HTTPException(400, "Transaction already used")
    if verification.bundle_id != "com.example.app":
        raise HTTPException(400, "Invalid bundle ID")
    if verification.product_id not in VALID_PRODUCTS:
        raise HTTPException(400, "Invalid product")
    await grant_subscription(req.user_id, verification)
    return {"status": "success"}
```

---

## 4. Layer 3: Subscription-platform risk controls

### 4.1 RevenueCat risk rules (example)

```yaml
risk_rules:
  - name: "receipt_reuse_detection"
    condition: "receipt_use_count > 1"
    action: "flag_and_review"
  - name: "rapid_transfer_detection"
    condition: "transfer_count > 3 in 24h"
    action: "auto_block"
  - name: "ip_mismatch_detection"
    condition: "ip_changed > 2 in 1h"
    action: "flag_for_review"
```

### 4.2 Webhook monitoring

```python
@app.post("/webhook/revenuecat")
async def revenuecat_webhook(request: Request):
    payload = await request.json()
    if not verify_signature(payload, request.headers.get("X-RevenueCat-Signature")):
        raise HTTPException(401, "Invalid signature")

    if payload.get("type") == "TRANSFER":
        from_user = payload.get("from_app_user_id")
        count = await count_transfers(from_user, window="24h")
        if count > 3:
            await block_account(from_user)
            await alert_security_team({"reason": "excessive_transfers", "user": from_user})

    return {"status": "received"}
```

---

## 5. Layer 4: Account & behavioral analytics

### 5.1 Metrics

| Metric | Normal | Anomalous | Detection |
|--------|--------|-----------|-----------|
| Receipt uses | 1 | >1 | DB query |
| Transfers/account | 0-1/month | >3/month | Log analysis |
| Device switches | <3/month | >10/month | Fingerprint |
| IP changes | <5/month | >20/month | IP log |
| Purchase hours | Business hours | Mass overnight | Time analysis |

### 5.2 ML outlier detection (optional)

```python
import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_suspicious(transactions: pd.DataFrame) -> pd.DataFrame:
    feats = ["receipt_use_count", "transfer_frequency", "ip_change_frequency",
             "device_change_frequency", "purchase_amount", "time_since_last"]
    X = transactions[feats].fillna(0)
    clf = IsolationForest(contamination=0.01, random_state=42)
    transactions["anomaly"] = clf.fit_predict(X)
    return transactions[transactions["anomaly"] == -1]
```

---

## 6. Developer checklist

### ✅ Must do

- [ ] Verify every purchase via StoreKit 2 `VerificationResult`
- [ ] Verify receipts server-side (never trust the client)
- [ ] Enforce transactionId uniqueness
- [ ] Validate bundleId and product_id
- [ ] Enable risk rules (if using RevenueCat)
- [ ] Monitor anomalous patterns

### ⚠️ Should do

- [ ] Implement SSL pinning (raises attacker cost)
- [ ] Add jailbreak detection (optional, bypassable)
- [ ] IP + device-fingerprint monitoring
- [ ] Automated alerting
- [ ] Periodic subscription-log audits

### 🚫 Never

- [ ] Don't trust client-sent `price`
- [ ] Don't allow receipt reuse
- [ ] Don't hardcode API keys in the client
- [ ] Don't ignore `unverified` results
- [ ] Don't skip server-side verification

---

## 7. Resources

- [Apple - StoreKit security](https://developer.apple.com/documentation/storekit/in-app_purchase/setting_up_storekit_testing_in_xcode)
- [RevenueCat - Security best practices](https://www.revenuecat.com/docs/best-practices/security)
- [OWASP Mobile Security Testing Guide](https://owasp.org/www-project-mobile-security-testing-guide/)
- [CWE-345: Insufficient Verification of Data Authenticity](https://cwe.mitre.org/data/definitions/345.html)

---

*Guide by #napster. Educational purposes only.*