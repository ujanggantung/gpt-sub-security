# Subscription Abuse 防御方案

> 面向开发者和订阅管理平台的 IAP 订阅滥用防御措施。

---

## 1. 分层防御模型

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 客户端防护 (StoreKit 2 + App Security)            │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 服务端验证 (App Store Server API + 自验证)         │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 订阅平台风控 (RevenueCat / 托管服务)              │
├─────────────────────────────────────────────────────────────┤
│  Layer 4: 账户与行为分析 (异常检测 + 用户画像)              │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Layer 1: 客户端防护

### 2.1 StoreKit 2 验证

```swift
// 必须使用 VerificationResult
let result = try await product.purchase()
switch result {
case .success(let verification):
    switch verification {
    case .verified(let transaction):
        // ✅ 签名有效，继续
    case .unverified(_, let error):
        // ❌ 签名无效，拒绝
        return
    }
}
```

**关键点**：
- StoreKit 2 自动验证 JWS 签名，无需开发者实现
- 验证结果不可绕过（系统级 API）
- `unverified` 结果必须立即拒绝

### 2.2 SSL Pinning

```swift
// 使用 URLSession 的 certificate pinning
let session = URLSession(
    configuration: .default,
    delegate: self,
    delegateQueue: nil
)

func urlSession(
    _ session: URLSession,
    didReceive challenge: URLAuthenticationChallenge
) async -> (URLSession.AuthChallengeDisposition, URLCredential?) {
    // 验证服务器证书
    guard let serverTrust = challenge.protectionSpace.serverTrust,
          let certificate = SecTrustGetCertificateAtIndex(serverTrust, 0) else {
        return (.cancelAuthenticationChallenge, nil)
    }

    // 验证证书指纹
    let serverCertData = SecCertificateCopyData(certificate) as Data
    let expectedCertData = // 你的证书指纹

    guard serverCertData == expectedCertData else {
        return (.cancelAuthenticationChallenge, nil)
    }

    return (.useCredential, URLCredential(trust: serverTrust))
}
```

**注意**：SSL Pinning 可被 jailbreak 设备绕过（SSL Kill Switch 3），因此不能单独依赖。

### 2.3 Jailbreak 检测

```swift
func isDeviceJailbroken() -> Bool {
    // 检查常见 jailbreak 路径
    let paths = [
        "/Applications/Cydia.app",
        "/usr/sbin/sshd",
        "/etc/apt",
        "/private/var/lib/apt/"
    ]
    for path in paths {
        if FileManager.default.fileExists(atPath: path) {
            return true
        }
    }

    // 检查是否可写入系统目录
    let testPath = "/private/jailbreak_test.txt"
    do {
        try "test".write(toFile: testPath, atomically: true, encoding: .utf8)
        try FileManager.default.removeItem(atPath: testPath)
        return true
    } catch {
        return false
    }
}
```

**重要**：Jailbreak 检测不是 100% 可靠，但可以增加攻击成本。

---

## 3. Layer 2: 服务端验证

### 3.1 App Store Server API 验证

```python
import requests
import jwt  # PyJWT

def verify_app_store_receipt(receipt_data: str, apple_root_cert: bytes) -> dict:
    """
    验证 App Store 收据

    Args:
        receipt_data: Base64 编码的收据
        apple_root_cert: Apple Root CA 证书

    Returns:
        验证结果
    """
    # 1. 验证证书链
    # 2. 验证签名
    # 3. 检查 transactionId 唯一性
    # 4. 验证 purchaseDate 是否在合理范围内
    # 5. 检查 bundleId 是否匹配
    pass

def check_transaction_uniqueness(transaction_id: str) -> bool:
    """
    检查 transactionId 是否已被使用

    防止同一笔交易被多次使用（Receipt Replay）
    """
    # 查询数据库
    existing = db.query(
        "SELECT id FROM transactions WHERE transaction_id = %s",
        (transaction_id,)
    )
    return len(existing) == 0
```

### 3.2 关键验证点

| 验证项 | 说明 | 防御目标 |
|--------|------|----------|
| 证书链验证 | 使用 Apple Root CA 验证证书链 | 防止伪造收据 |
| 签名验证 | 验证 JWS/收据签名 | 防止篡改 |
| Transaction ID 唯一性 | 同一 transactionId 只能使用一次 | 防止 Receipt Replay |
| Bundle ID 验证 | 确保收据来自正确的 App | 防止跨 App 混用 |
| Environment 验证 | Production/Sandbox 不混用 | 防止测试令牌在线上使用 |
| Purchase Date 验证 | 检查购买日期是否合理 | 防止时间篡改 |

### 3.3 自定义 Receipt 验证服务

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class ReceiptVerification(BaseModel):
    receipt_data: str
    user_id: str
    product_id: str

@app.post("/verify-receipt")
async def verify_receipt(request: ReceiptVerification):
    """
    验证收据并授予订阅
    """
    # 1. 调用 App Store Server API 验证
    verification = await call_app_store_server(request.receipt_data)

    if not verification.valid:
        raise HTTPException(400, "Invalid receipt")

    # 2. 检查 transactionId 唯一性
    if not check_transaction_uniqueness(verification.transaction_id):
        raise HTTPException(400, "Transaction already used")

    # 3. 验证 bundleId
    if verification.bundle_id != "com.openai.chat":
        raise HTTPException(400, "Invalid bundle ID")

    # 4. 验证 product_id
    if verification.product_id not in VALID_PRODUCTS:
        raise HTTPException(400, "Invalid product")

    # 5. 验证 user_id 与 receipt 的关联
    # (可选：验证 app_account_token)

    # 6. 授予订阅
    await grant_subscription(request.user_id, verification)

    return {"status": "success"}
```

---

## 4. Layer 3: 订阅平台风控

### 4.1 RevenueCat 配置

在 RevenueCat Dashboard 中启用以下风控规则：

```yaml
# RevenueCat 风控配置示例
risk_rules:
  # 单 receipt 多用户检测
  - name: "receipt_reuse_detection"
    condition: "receipt_use_count > 1"
    action: "flag_and_review"

  # 快速跨用户转移检测
  - name: "rapid_transfer_detection"
    condition: "transfer_count > 3 in 24h"
    action: "auto_block"

  # 异常 IP 检测
  - name: "ip_mismatch_detection"
    condition: "ip_changed > 2 in 1h"
    action: "flag_for_review"
```

### 4.2 自定义 Webhook 监控

```python
import hmac
import hashlib
from fastapi import FastAPI, Request

app = FastAPI()

@app.post("/webhook/revenuecat")
async def revenuecat_webhook(request: Request):
    """
    监控 RevenueCat 事件
    """
    payload = await request.json()

    # 1. 验证签名
    signature = request.headers.get("X-RevenueCat-Signature")
    if not verify_signature(payload, signature):
        raise HTTPException(401, "Invalid signature")

    # 2. 分析事件
    event_type = payload.get("type")

    if event_type == "INITIAL_PURCHASE":
        await handle_initial_purchase(payload)
    elif event_type == "TRANSFER":
        await handle_transfer(payload)
    elif event_type == "CANCELLATION":
        await handle_cancellation(payload)

    # 3. 检测异常
    if is_suspicious_event(payload):
        await alert_security_team(payload)

    return {"status": "received"}

async def handle_transfer(payload: dict):
    """
    处理权益转移事件
    """
    from_user = payload.get("from_app_user_id")
    to_user = payload.get("to_app_user_id")
    receipt = payload.get("receipt")

    # 检查转移频率
    transfer_count = await count_transfers(from_user, time_window="24h")
    if transfer_count > 3:
        await block_account(from_user)
        await alert_security_team({
            "reason": "excessive_transfers",
            "user": from_user,
            "count": transfer_count
        })
```

---

## 5. Layer 4: 账户与行为分析

### 5.1 异常检测指标

| 指标 | 正常范围 | 异常阈值 | 检测方法 |
|------|----------|----------|----------|
| 单 receipt 使用次数 | 1 | >1 | 数据库查询 |
| 单账户订阅转移次数 | 0-1/月 | >3/月 | 日志分析 |
| 设备指纹切换频率 | <3/月 | >10/月 | 设备指纹 |
| IP 地址变化频率 | <5/月 | >20/月 | IP 日志 |
| 购买时间分布 | 正常工作时间 | 凌晨批量 | 时间分析 |

### 5.2 机器学习检测（可选）

```python
import pandas as pd
from sklearn.ensemble import IsolationForest

def detect_suspicious_patterns(transactions: pd.DataFrame) -> pd.DataFrame:
    """
    使用 Isolation Forest 检测异常交易
    """
    features = [
        "receipt_use_count",
        "transfer_frequency",
        "ip_change_frequency",
        "device_change_frequency",
        "purchase_amount",
        "time_since_last_purchase"
    ]

    X = transactions[features].fillna(0)

    # 训练异常检测模型
    clf = IsolationForest(contamination=0.01, random_state=42)
    transactions["anomaly_score"] = clf.fit_predict(X)

    # 返回异常交易
    return transactions[transactions["anomaly_score"] == -1]
```

---

## 6. 开发者检查清单

### ✅ 必须实施

- [ ] 使用 StoreKit 2 的 `VerificationResult` 验证所有购买
- [ ] 服务端验证收据（不信任客户端）
- [ ] 实现 transactionId 唯一性检查
- [ ] 验证 bundleId 和 product_id
- [ ] 启用 RevenueCat 风控规则（如使用）
- [ ] 监控异常交易模式

### ⚠️ 推荐实施

- [ ] 实现 SSL Pinning（增加攻击成本）
- [ ] 添加 Jailbreak 检测（可选，有绕过方式）
- [ ] 实现 IP 和设备指纹监控
- [ ] 设置自动告警机制
- [ ] 定期审计订阅日志

### 🚫 不要

- [ ] 不要信任客户端发送的 `price` 字段
- [ ] 不要允许同一收据多次使用
- [ ] 不要将 API 密钥硬编码在客户端
- [ ] 不要忽略 `unverified` 的交易结果
- [ ] 不要跳过服务端验证

---

## 7. 参考资源

- [Apple - StoreKit Security](https://developer.apple.com/documentation/storekit/in-app_purchase/setting_up_storekit_testing_in_xcode)
- [RevenueCat - Security Best Practices](https://www.revenuecat.com/docs/best-practices/security)
- [OWASP - Mobile Security Testing Guide](https://owasp.org/www-project-mobile-security-testing-guide/)
- [CWE-345: Insufficient Verification of Data Authenticity](https://cwe.mitre.org/data/definitions/345.html)

---

*本文档仅用于安全研究和教育目的。*