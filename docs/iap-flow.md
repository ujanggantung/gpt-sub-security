# Apple In-App Purchase Subscription Flow

> The real technical pipeline behind iOS IAP subscriptions — the surface the viral tutorial claims to attack. Written by #napster.

---

## 1. Architecture overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Device (iOS)                               │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │   App    │───▶│  StoreKit 2  │───▶│  App Store Server  │  │
│  │(ChatGPT) │    │  (system)    │    │  (Apple backend)   │  │
│  └──────────┘    └──────────────┘    └───────────────────┘  │
│       │                 │                       │            │
│       │                 ▼                       ▼            │
│       │          ┌──────────────┐    ┌───────────────────┐  │
│       │          │ Transaction  │    │  Receipt / JWS    │  │
│       │          │  (JWS-signed)│    │   (Apple-issued)  │  │
│       │          └──────────────┘    └───────────────────┘  │
│       │                                                    │
└───────┼────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│       App server               │
│  ┌─────────────────────────┐  │
│  │ Verify receipt / JWS     │  │
│  │ (App Store Server API)  │  │
│  └─────────────────────────┘  │
│  ┌─────────────────────────┐  │
│  │ Grant entitlement        │  │
│  └─────────────────────────┘  │
│  ┌─────────────────────────┐  │
│  │ Third-party (RevenueCat) │  │
│  │ optional: subscription   │  │
│  │ management               │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘
```

---

## 2. StoreKit 2 purchase flow (modern)

### 2.1 Initiate purchase

```swift
import StoreKit

let products = try await Product.products(for: ["oai_chatgpt_plus_1999_1m"])
let result = try await products.first!.purchase()

switch result {
case .success(let verification):
    switch verification {
    case .verified(let transaction):
        // ✅ JWS signature verified — genuine Apple transaction
        await transaction.finish()
    case .unverified(_, let error):
        // ❌ Invalid signature — reject
        print("Verification failed: \(error)")
    }
case .userCancelled:
    break
default:
    break
}
```

### 2.2 Key points

- `Product.purchase()` is a system-level API; users must confirm via the system UI
- `VerificationResult` verifies the signature automatically — the developer cannot skip it
- The JWS token is signed by Apple and carries the full transaction record

---

## 3. Transaction token (JWS) structure

`<header>.<payload>.<signature>`

### 3.1 Header

```json
{
  "alg": "ES256",
  "x5c": ["MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE..."],
  "kid": "K4GkGMfGhMxiWmQKnI0GredqTylpA0llT2LbQxh8WQ",
  "typ": "JWT"
}
```

| Field | Meaning |
|-------|---------|
| `alg` | Signing algorithm (ES256 = ECDSA P-256 + SHA-256) |
| `x5c` | Certificate chain (for verification) |
| `kid` | Key ID (for verification) |
| `typ` | JWT type |

### 3.2 Payload (`JWSDecodedPayload`)

```json
{
  "appAccountToken": "a7a1c9a5-...",
  "bundleId": "com.openai.chat",
  "environment": "Production",
  "expiresDate": 1779118400000,
  "inAppOwnershipType": "PURCHASED",
  "isUpgraded": false,
  "offerIdentifier": null,
  "originalPurchaseDate": 1775854400000,
  "originalTransactionId": "490001234567890",
  "productId": "oai_chatgpt_plus_1999_1m",
  "purchaseDate": 1775854400000,
  "quantity": 1,
  "revocationDate": null,
  "revocationReason": null,
  "signedDate": 1775854400000,
  "subscriptionGroupIdentifier": "6749460546",
  "transactionId": "490001234567890",
  "type": "Auto-Renewable Subscription",
  "webOrderLineItemId": "490001234567890"
}
```

### 3.3 Important fields

| Field | Meaning | Security role |
|-------|---------|---------------|
| `transactionId` | Transaction ID | Unique; replay protection |
| `originalTransactionId` | Original transaction | Links renewals |
| `productId` | Purchased product | Identifies the product |
| `bundleId` | App bundle ID | Source verification |
| `environment` | Production/Sandbox | Prevents sandbox tokens in prod |
| `expiresDate` | Expiry | Validates subscription status |
| `signedDate` | Signed-at | Validates time window |
| `inAppOwnershipType` | Ownership | PURCHASED / FAMILY_SHARED |

> **Note**: `offerIdentifier` can be null — StoreKit 2 identifies products by `productId`, **not** by an `offerName` string. This directly contradicts the viral tutorial.

---

## 4. Server-side validation (App Store Server API)

### 4.1 Recommended approach

Use StoreKit 2 `VerificationResult` on-device, and/or the App Store Server API server-side. The legacy `verifyReceipt` endpoint was deprecated after iOS 15; new code should use the [App Store Server API](https://developer.apple.com/documentation/appstoreserverapi).

---

## 5. RevenueCat's role (ChatGPT's subscription manager)

### 5.1 Why RevenueCat

- Unified subscription state across platforms
- Handles renewals, refunds, expirations
- Cross-platform consistency

### 5.2 RevenueCat workflow

```
App ──▶ StoreKit 2 purchase ──▶ JWS token
  │                              │
  ▼                              ▼
App sends token to RevenueCat ──▶ RevenueCat verifies + stores
  │                              │
  ▼                              ▼
RevenueCat returns entitlement ──▶ App grants user access
```

### 5.3 RevenueCat `app_user_id`

- Unique customer ID generated by the app (UUID)
- Associates subscription state
- **Must** be consistent with the app's own server

> ⚠️ RevenueCat's `app_user_id` ≠ Apple's `appAccountToken`. The first is the RevenueCat customer ID; the second is the app's custom account identifier.

---

## 6. Security boundary summary

| Layer | Mechanism | Bypass difficulty |
|-------|-----------|-------------------|
| Client | SSL pinning | Medium (needs jailbreak) |
| StoreKit | JWS signature verification | High (needs Apple private key) |
| App Store Server | Pricing + risk validation | Very high |
| RevenueCat | Risk engine + behavioral analysis | High |
| App backend | Account binding + anomaly detection | High |

**Conclusion**: The client is the only layer a jailbreak modifies — and it plays no part in price or entitlement decisions. All security-critical decisions happen server-side, at Apple or RevenueCat.

---

## 7. References

- [Apple - StoreKit 2](https://developer.apple.com/documentation/storekit)
- [Apple - JWSDecodedPayload](https://developer.apple.com/documentation/appstoreserverapi/jwsdecodedpayload)
- [Apple - App Store Server API](https://developer.apple.com/documentation/appstoreserverapi)
- [RevenueCat - iOS SDK](https://www.revenuecat.com/docs/ios/v4)
- [RevenueCat - REST API](https://www.revenuecat.com/docs/api-reference)

---

*Documentation by #napster. Educational purposes only.*