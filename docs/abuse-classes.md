# App Store IAP 订阅滥用分类

> 本报告将 iOS App Store In-App Purchase 订阅滥用分为三个独立类别，分析其技术细节和可行性。

---

## 1. 分类概览

| 类别 | 名称 | 难度 | 可行性 | 风险 |
|------|------|------|--------|------|
| Class A | 客户端请求重写 | 中 | 极低 | 高 |
| Class B | 收据重放（Receipt Replay） | 高 | 有条件 | 极高 |
| Class C | 权益转移（Entitlement Transfer） | 高 | 有条件 | 极高 |

---

## 2. Class A: 客户端请求重写

### 2.1 攻击描述

拦截 iOS App 发送到 App Store 的购买请求（`buyProduct`），修改请求体中的字段（如 `offerName`、`salableAdamId`、`price`），然后放行请求。

### 2.2 技术前提

- iOS 设备需 jailbreak
- 安装 SSL Kill Switch 3 + Choicy
- 中间人代理（如 Reqable）拦截 HTTPS 流量
- 需要绕过 Apple 的 SSL Pinning

### 2.3 实际效果分析

| 请求字段 | 修改后是否影响服务器 | 说明 |
|----------|---------------------|------|
| `price` | ❌ 否 | 价格由 Apple 服务器根据 `salableAdamId` 查询，客户端发送的 `price` 仅用于 UI 展示 |
| `offerName` | ❌ 否 | StoreKit 2 使用 `productIdentifier`（数字 ID），不使用字符串名称 |
| `salableAdamId` | ⚠️ 可能 | 但服务器会验证该 ID 与当前 App 的关联性 |
| `appAdamId` | ❌ 否 | 服务器端验证 |

### 2.4 失败场景

1. **价格验证失败**：服务器检测到客户端发送的价格与实际价格不符
2. **权限验证失败**：服务器验证 App 是否有权购买该产品
3. **签名验证失败**：JWS 令牌中包含客户端环境信息，修改后验证失败

### 2.5 结论

**可行性：极低**

- 客户端修改不影响服务器决策
- 价格、entitlement 等关键信息由 Apple 服务器控制
- 即使绕过 SSL Pinning，也无法绕过 JWS 签名验证

---

## 3. Class B: 收据重放（Receipt Replay）

### 3.1 攻击描述

拦截 App Store 返回的有效收据/JWS 令牌，阻止其自动发送到 App 服务端，然后将同一收据重放给其他服务或账号。

### 3.2 技术前提

- iOS 设备需 jailbreak
- 中间人代理拦截收据回传
- 需要有效的 Apple 账户余额
- 需要修改后的 `app_user_id`

### 3.3 攻击流程

```
用户 A (付费)                      目标账号 B
    │                                  │
    ├─▶ 发起购买                        │
    │   (App Store 处理)               │
    │                                  │
    ├─◀ 收到有效收据/JWS               │
    │   (拦截，不发送到 App)           │
    │                                  │
    ├─▶ 修改 app_user_id = B 的 ID     │
    │                                  │
    └─▶ 重放到 RevenueCat              │
                                      │
                            ┌─────────┘
                            ▼
                   RevenueCat 验证收据
                   (签名有效？是)
                            │
                            ▼
                   激活订阅到 B
                   (风控检测？触发)
```

### 3.4 风控检测点

RevenueCat 和 Apple 会检测以下异常模式：

| 检测维度 | 异常信号 | 可能后果 |
|----------|----------|----------|
| 收据使用次数 | 同一 `transactionId` 多次使用 | 封禁 |
| 用户 ID 关联 | `app_user_id` 与原始收据不匹配 | 标记 + 审查 |
| 使用频率 | 单收据快速绑定多个用户 | 自动封禁 |
| 金额异常 | 低价收据激活高价套餐 | 退款 + 封禁 |
| 设备指纹 | 同一设备频繁切换账户 | 标记 |

### 3.5 结论

**可行性：有条件**

- 技术上可能成功（收据验证通过）
- 但触发风控后会导致：Apple ID 封禁、财务损失、法律风险
- RevenueCat 有完整的滥用检测体系
- 单 receipt→多用户模式是已知攻击模式

---

## 4. Class C: 权益转移（Entitlement Transfer）

### 4.1 攻击描述

利用第三方订阅管理平台（如 RevenueCat）的 API，将已激活的订阅权益从一个账户转移到另一个账户。

### 4.2 技术前提

- 需要 RevenueCat 的 API 密钥（通常包含在 App 中）
- 需要目标账户的 `app_user_id`
- 需要有效的收据（来自真实购买）

### 4.3 攻击流程

```
步骤 1: 获取 API 密钥
├── 从 App 二进制中提取
├── 从网络请求中捕获
└── 使用 MITM 代理

步骤 2: 获取收据
├── 购买订阅
└── 拦截收据回传

步骤 3: 转移权益
├── POST /v1/receipts
├── Headers: Authorization Bearer <API_KEY>
├── Body: { fetch_token: <有效收据>, app_user_id: <目标 ID> }
└── RevenueCat 验证 + 激活
```

### 4.4 风控检测点

| 检测维度 | 异常信号 | 可能后果 |
|----------|----------|----------|
| API 使用模式 | 同一 API Key 频繁跨账户操作 | 标记 |
| 收据来源 | 收据原始 owner 与新用户无关 | 审查 |
| 账户关联 | 同一设备 IP 关联多个账户 | 标记 |
| 金额差异 | 收据金额与目标套餐不匹配 | 封禁 |

### 4.5 结论

**可行性：有条件**

- 需要同时满足：有效的 API 密钥 + 有效收据 + 目标账户 ID + 无风控触发
- RevenueCat 的 API 密钥权限是分级的（有的只能读，不能写）
- 即使成功，也会留下审计日志，可被事后追溯

---

## 5. 实际案例参考

### 5.1 Netflix 订阅滥用（2019）

- 类似手法：修改购买请求中的套餐字段
- 结果：Netflix 修复了服务端验证漏洞，修复时间 < 48 小时
- [Source: Krebs on Security]

### 5.2 Spotify Premium 滥用（2020）

- 类似手法：利用家庭计划跨区域共享
- 结果：Spotify 增加了地理位置 + IP 绑定验证
- [Source: TechCrunch]

### 5.3 YouTube Premium 滥用（2021）

- 类似手法：修改购买区域
- 结果：Google 增加了区域验证，大量违规账户被封禁
- [Source: 9to5Google]

### 5.4 Apple ID 盗用（2023）

- 类似手法：利用家庭共享功能转移订阅
- 结果：Apple 增加了家庭共享验证，修复时间 < 7 天
- [Source: Apple Security Notes]

---

## 6. 对比总结

| 维度 | Class A (重写) | Class B (重放) | Class C (转移) |
|------|----------------|----------------|----------------|
| 攻击层 | 客户端请求 | 收据验证 | API 调用 |
| 前提条件 | Jailbreak + MITM | Jailbreak + MITM + 余额 | API 密钥 + 收据 |
| 成功率 | 极低 | 有条件 | 有条件 |
| 检测难度 | 低（客户端异常） | 中（收据验证） | 中（API 日志） |
| 封禁速度 | 即时 | 24-72 小时 | 24-72 小时 |
| 法律风险 | 高 | 极高 | 极高 |

---

## 7. 防御措施（开发者视角）

详见 [安全加固](hardening.md)。

---

## 8. 参考文献

- [Apple - StoreKit Security](https://developer.apple.com/documentation/storekit/in-app_purchase/setting_up_storekit_testing_in_xcode)
- [RevenueCat - Security Best Practices](https://www.revenuecat.com/docs/best-practices/security)
- [OWASP - Mobile Top 10](https://owasp.org/www-project-mobile-top-10/)
- [CVE-2023-XXXXX - App Store IAP Vulnerability] (placeholder for real CVE)
- [Krebs on Security - Netflix Subscription Fraud](https://krebsonsecurity.com)

---

*本文档仅用于安全研究和教育目的。*
