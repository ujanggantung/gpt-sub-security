# App Store IAP Subscription Abuse Classes

> A structured look at the three ways malicious actors attack iOS In-App Purchase subscriptions — and why most fail. By #napster.

---

## 1. Class overview

| Class | Name | Difficulty | Feasibility | Risk |
|-------|------|------------|-------------|------|
| A | Client request rewrite | Medium | Very low | High |
| B | Receipt replay | High | Conditional | Extreme |
| C | Entitlement transfer | High | Conditional | Extreme |

---

## 2. Class A: Client request rewrite

### 2.1 Description

Intercept the purchase request (`buyProduct`) sent by the iOS app to the App Store, modify fields (`offerName`, `salableAdamId`, `price`), then release the request.

### 2.2 Requirements

- Jailbroken iOS device
- SSL Kill Switch 3 + Choicy
- MITM proxy (e.g., Reqable)
- Bypass Apple's SSL pinning

### 2.3 What actually happens

| Field changed | Server impact? | Reasoning |
|---------------|----------------|-----------|
| `price` | ❌ No | Server prices from `salableAdamId`; client `price` is UI-only |
| `offerName` | ❌ No | StoreKit 2 uses `productId`, not a name string |
| `salableAdamId` | ⚠️ Maybe | But server validates the ID against the app |
| `appAdamId` | ❌ No | Server-side validation |

### 2.4 Failure modes

1. **Price validation**: server detects client price ≠ real price
2. **Entitlement validation**: app cannot buy that product
3. **Signature validation**: JWS carries environment info; tampering invalidates it

### 2.5 Conclusion

**Feasibility: very low.** Client-side edits don't influence server decisions. Prices and entitlements are controlled by Apple's servers. Bypassing SSL pinning does not bypass JWS signature validation.

---

## 3. Class B: Receipt replay

### 3.1 Description

Intercept a valid App Store receipt/JWS, block it from reaching the app's backend, then replay the same receipt against other services or accounts.

### 3.2 Requirements

- Jailbroken iOS device
- MITM proxy to capture the receipt
- Funded Apple account
- Modified `app_user_id`

### 3.3 Attack flow

```
User A (pays)                       Target account B
    │                                    │
    ├─▶ initiate purchase                 │
    │   (App Store processes)             │
    ├─◀ valid receipt/JWS returned        │
    │   (intercepted, not sent to app)    │
    ├─▶ modify app_user_id = B's ID       │
    └─▶ replay to RevenueCat              │
                                         │
                              ┌──────────┘
                              ▼
                     RevenueCat verifies receipt
                     (signature valid? yes)
                              │
                              ▼
                     Subscription activated on B
                     (risk engine? triggered)
```

### 3.4 Risk-detection signals

| Dimension | Anomaly | Likely result |
|-----------|---------|---------------|
| Receipt use count | Same `transactionId` used multiple times | Ban |
| User-ID linkage | `app_user_id` mismatched with original receipt | Flag + review |
| Usage frequency | One receipt binds many users quickly | Auto-ban |
| Amount anomaly | Cheap receipt activates expensive tier | Refund + ban |
| Device fingerprint | Same device switches accounts rapidly | Flag |

### 3.5 Conclusion

**Feasibility: conditional.** Technically the receipt verifies, but triggering the risk engine leads to: Apple ID ban, financial loss, legal exposure. RevenueCat has complete abuse monitoring. One-receipt-many-users is a known attack signature.

---

## 4. Class C: Entitlement transfer

### 4.1 Description

Use a third-party subscription platform's API (e.g., RevenueCat) to move an activated subscription entitlement from one account to another.

### 4.2 Requirements

- RevenueCat API key (often embedded in the app binary)
- Target account's `app_user_id`
- A valid receipt (from a real purchase)

### 4.3 Attack flow

```
Step 1: obtain API key
├── extract from app binary
├── capture from network traffic
└── via MITM proxy

Step 2: obtain receipt
├── purchase a subscription
└── intercept receipt callback

Step 3: transfer entitlement
├── POST /v1/receipts
├── Headers: Authorization Bearer <API_KEY>
├── Body: { fetch_token: <valid receipt>, app_user_id: <target ID> }
└── RevenueCat verifies + activates
```

### 4.4 Risk-detection signals

| Dimension | Anomaly | Likely result |
|-----------|---------|---------------|
| API usage pattern | One API key doing cross-account ops | Flag |
| Receipt origin | Receipt's original owner unrelated to new user | Review |
| Account linkage | Same device/IP across accounts | Flag |
| Amount mismatch | Receipt amount ≠ target tier | Ban |

### 4.5 Conclusion

**Feasibility: conditional.** Requires all of: valid API key + valid receipt + target user ID + no risk trigger. RevenueCat API keys are permission-tiered (some read-only). Even success leaves audit logs.

---

## 5. Real-world precedent

- **Netflix (2019)**: similar request-field tampering → fixed server-side validation in <48h
- **Spotify Premium (2020)**: family-plan regional abuse → added geo+IP binding
- **YouTube Premium (2021)**: purchase-region manipulation → Google region checks; mass bans
- **Apple IDs (2023)**: family-sharing-based subscription transfer → Apple hardened verification in <7 days

---

## 6. Comparison summary

| Dimension | Class A (rewrite) | Class B (replay) | Class C (transfer) |
|-----------|-------------------|------------------|--------------------|
| Attack layer | Client request | Receipt validation | API call |
| Prerequisites | Jailbreak + MITM | Jailbreak + MITM + funds | API key + receipt |
| Success rate | Very low | Conditional | Conditional |
| Detection ease | Low (client anomaly) | Medium | Medium |
| Ban speed | Immediate | 24-72h | 24-72h |
| Legal risk | High | Extreme | Extreme |

---

## 7. Defense

See the [Hardening Guide](hardening.md) for developer-side mitigations.

---

## 8. References

- [Apple - Setting up StoreKit testing](https://developer.apple.com/documentation/storekit/in-app_purchase/setting_up_storekit_testing_in_xcode)
- [RevenueCat - Security best practices](https://www.revenuecat.com/docs/best-practices/security)
- [OWASP Mobile Top 10](https://owasp.org/www-project-mobile-top-10/)
- [CWE-345: Insufficient Verification of Data Authenticity](https://cwe.mitre.org/data/definitions/345.html)

---

*Analysis by #napster. Security research and education only.*