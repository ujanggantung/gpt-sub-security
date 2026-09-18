# Apple In-App Purchase 订阅完整流程

> 基于 Apple 官方文档，还原 iOS IAP 订阅支付的真实技术链路，用于理解教程中提到的攻击面。

---

## 1. 系统架构总览

```
┌─────────────────────────────────────────────────────────────┐
│                  设备端 (iOS)                                │
│  ┌──────────┐    ┌──────────────┐    ┌───────────────────┐  │
│  │ 你的 App  │───▶│   StoreKit 2 │───▶│  App Store Server │  │
│  │ (ChatGPT)│    │  (系统框架)   │    │  (Apple 后端)     │  │
│  └──────────┘    └──────────────┘    └───────────────────┘  │
│       │                 │                       │            │
│       │                 ▼                       ▼            │
│       │          ┌──────────────┐    ┌───────────────────┐  │
│       │          │ Transaction  │    │  Receipt / JWS    │  │
│       │          │  (JWS 签名)   │    │   (Apple 签发)     │  │
│       │          └──────────────┘    └───────────────────┘  │
│       │                                                    │
└───────┼────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────┐
│       App 服务端               │
│  ┌─────────────────────────┐  │
│  │ 验证 Receipt / JWS       │  │
│  │ (App Store Server API)  │  │
│  └─────────────────────────┘  │
│  ┌─────────────────────────┐  │
│  │ 授予 Entitlement         │  │
│  │ (Subscription Benefit)  │  │
│  └─────────────────────────┘  │
│  ┌─────────────────────────┐  │
│  │ 第三方平台 (RevenueCat)  │  │
│  │ 可选：统一管理订阅        │  │
│  └─────────────────────────┘  │
└───────────────────────────────┘
```

---

## 2. StoreKit 2 购买流程（现代方式）

### 2.1 发起购买

```swift
// 开发者代码示例（Swift）
import StoreKit

// 获取产品
let products = try await Product.products(for: ["oai_chatgpt_plus_1999_1m"])

// 购买
let result = try await products.first!.purchase()
switch result {
case .success(let verification):
    // 关键：验证签名
    switch verification {
    case .verified(let transaction):
        // ✅ JWS 签名已验证，来自 Apple
        await transaction.finish()
    case .unverified(_, let error):
        // ❌ 签名无效
        print("Verification failed: \(error)")
    }
case .userCancelled:
    break
default:
    break
}
```

### 2.2 关键点

- **`Product.purchase()`** 是系统级 API，用户必须通过系统 UI 确认
- **`VerificationResult`** 自动验证签名，开发者无需实现
- **JWS 令牌** 由 Apple 签名，包含完整交易信息

---

## 3. 交易令牌 (Transaction JWS) 结构

StoreKit 2 返回的 JWS（JSON Web Signature）令牌包含 3 部分：

```
<header>.<payload>.<signature>
```

### 3.1 Header

```json
{
  "alg": "ES256",
  "x5c": ["MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE..."],
  "kid": "K4GkGMfGhMxiWmQKnI0GredqTylpA0llT2LbQxh8WQ",
  "typ": "JWT"
}
```

| 字段 | 说明 |
|------|------|
| `alg` | 签名算法（ES256 = ECDSA P-256 + SHA-256） |
| `x5c` | 证书链（用于验证） |
| `kid` | Key ID（用于验证） |
| `typ` | JWT 类型 |

### 3.2 Payload（`JWSDecodedPayload`）

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

### 3.3 关键字段解释

| 字段 | 含义 | 安全作用 |
|------|------|----------|
| `transactionId` | 交易 ID | 唯一标识，防重放 |
| `originalTransactionId` | 原始交易 ID | 用于关联订阅续期 |
| `productId` | 产品 ID | 标识购买的产品 |
| `bundleId` | App Bundle ID | 验证请求来源 |
| `environment` | Production/Sandbox | 防止沙盒令牌在线上使用 |
| `expiresDate` | 过期时间 | 判断订阅是否有效 |
| `signedDate` | 签发时间 | 验证时间窗口 |
| `inAppOwnershipType` | 所有权类型 | PURCHASED / FAMILY_SHARED |

> **注意**：`offerIdentifier` 可能为 null，因为 StoreKit 2 的产品 ID 是 `productId` 而非 `offerName`。

---

## 4. App Store Server API（服务端验证）

### 4.1 推荐的验证方式

```bash
# 使用 App Store Look Up API
curl -X GET \
  "https://api.appstoreconnect.apple.com/v1/apps/{appId}/inAppPurchases/{purchaseId}" \
  -H "Authorization: Bearer {token}"
```

### 4.2 经典验证（deprecated）

```bash
# 旧版 verifyReceipt（已废弃）
POST https://buy.itunes.apple.com/verifyReceipt
```

Apple 已在 iOS 15+ 弃用旧版 `verifyReceipt` API，推荐使用 StoreKit 2 的 `VerificationResult` 或 App Store Server API。

---

## 5. RevenueCat 角色（ChatGPT 的订阅管理）

### 5.1 为什么用 RevenueCat

- 统一管理多个平台的订阅状态
- 自动处理续费、退款、过期
- 提供跨平台一致性

### 5.2 RevenueCat 的工作流

```
App ──▶ StoreKit 2 purchase ──▶ JWS token
  │                              │
  ▼                              ▼
App 发送 token 到 RevenueCat ──▶ RevenueCat 验证 + 存储
  │                              │
  ▼                              ▼
RevenueCat 返回 entitlement ──▶ App 授予用户权限
```

### 5.3 RevenueCat 的 `app_user_id`

- 唯一标识用户
- 由 App 生成（UUID）
- 用于关联订阅状态
- **必须**与 App 服务端一致

> ⚠️ **重要**：RevenueCat 的 `app_user_id` 与 Apple 的 `appAccountToken` 是两个不同的概念。前者是 RevenueCat 的客户 ID，后者是 App 自定义的账户标识。

---

## 6. 安全边界总结

| 层 | 安全机制 | 绕过难度 |
|----|----------|----------|
| 客户端 | SSL Pinning | 中（需 jailbreak） |
| StoreKit | 签名验证 (JWS) | 高（需 Apple 私钥） |
| App Store Server | 价格验证、风控 | 非常高 |
| RevenueCat | 风控、行为分析 | 高 |
| App 服务端 | 账户绑定、异常检测 | 高 |

**结论**：客户端是唯一可通过 jailbreak 修改的层，但该层不参与价格和 entitlement 的最终决策。所有安全关键决策都在 Apple/RevenueCat 的服务端。

---

## 7. 参考文献

- [Apple - StoreKit 2](https://developer.apple.com/documentation/storekit)
- [Apple - JWSDecodedPayload](https://developer.apple.com/documentation/appstoreserverapi/jwsdecodedpayload)
- [Apple - App Store Server API](https://developer.apple.com/documentation/appstoreserverapi)
- [RevenueCat - StoreKit 2](https://www.revenuecat.com/docs/ios/v4)
- [RevenueCat - REST API](https://www.revenuecat.com/docs/api-reference)

---

*本文档仅用于教育目的。*
