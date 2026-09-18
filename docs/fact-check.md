# 事实核查报告：iOS ChatGPT Pro 20x "绕过"教程

> 本报告逐条验证 2026 年 9 月流传的 "iOS ChatGPT Pro 20x 开通教程" 中的技术声明。

---

## 📌 教程来源

- **原始位置**：GitHub 仓库 `engineerbas/gpt_sub_analysis`（含 Telegram 联系方式）
- **传播渠道**：Telegram 群组、中文技术社区
- **教程声称**：通过修改 App Store 购买请求体，以 Plus 价格获得 Pro 20x 订阅
- **关联项目**：`codex-x.site`、`yynxxxxx/Codex-X`（同作者推广的其他项目）

---

## 🔍 逐条核查

### 声明 1："修改 `price` 字段即可获得低价订阅"

**教程原文**：将 `offerName` 从 `oai_chatgpt_plus_20000_1y` 改为 `oai_chatgpt_pro_20000_1m`，同时将 `salableAdamId` 从 `6745416289` 改为 `6657954405`，`price` 保持 `200000` 不变。

**核查结果**：❌ **错误**

**分析**：
1. Apple IAP 的价格在 App Store Connect 中配置，与 `salableAdamId` 绑定
2. `price` 字段在 StoreKit 2 的 `buyProduct` 请求中**不参与价格验证**
3. Apple 服务器根据 `salableAdamId` 查询对应的真实价格，客户端发送的 `price` 仅用于 UI 展示
4. 即使客户端发送 `price=200000`，如果对应的 `salableAdamId` 实际定价 $200/月，最终账单金额就是 $200/月

**证据**：
- [Apple StoreKit 2 Documentation](https://developer.apple.com/documentation/storekit) 中没有 `price` 字段的说明
- App Store 的购买请求格式是 Apple 私有的 plist 格式，`price` 仅用于日志和 UI
- 任何对 `salableAdamId` 的修改都会导致服务器返回错误码或显示不同的价格

**结论**：这个操作要么失败（服务器拒绝），要么真的激活了 Pro 20x 但按**实际价格 $200/月**计费。

---

### 声明 2："修改 `offerName` 即可激活隐藏套餐"

**教程原文**：`offerName` 从 `oai_chatgpt_plus_20000_1y` 改为 `oai_chatgpt_pro_20000_1m`。

**核查结果**：❌ **错误**

**分析**：
1. StoreKit 2 的 purchase API 使用 `productIdentifier` 而非 `offerName`
2. `offerName` 在 Apple 的官方文档中不是标准购买请求字段
3. App Store 使用 `salableAdamId`（数字 ID）而非字符串名称来标识商品
4. 修改 `offerName` 而不修改 `salableAdamId` 是矛盾的

**结论**：`offerName` 在实际请求中可能根本不存在，或者是客户端内部使用的字段，修改它不会影响服务器行为。

---

### 声明 3："SSL Kill Switch 3 可全局绕过 SSL Pinning"

**教程原文**：在 Sileo 安装 SSL Kill Switch 3，全局开启即可。

**核查结果**：⚠️ **部分正确，但过度简化**

**分析**：
1. SSL Kill Switch 3 确实可以绕过部分 SSL Pinning
2. 但 Apple 在 iOS 16+ 中显著加强了 SSL Pinning 实现
3. 不是所有系统 daemon 都能被 Tweak 注入
4. 教程中列出的 5 个 daemon（`cloudd`、`accountsd`、`identityservicesd`、`akd`、`nsurlsessiond`）确实负责 IAP 相关通信，但注入成功率取决于 jailbreak 版本和 iOS 版本
5. 需要配合 Choicy 逐个 daemon 配置，并非"全局生效"那么简单

**结论**：在特定 jailbreak + iOS 版本下可能成功，但教程过于简化了配置难度。

---

### 声明 4："RevenueCat 可随意转移 `app_user_id`"

**教程原文**：修改 `app_user_id` 为目标账号 ID，重新发送即可完成订阅转移。

**核查结果**：⚠️ **技术上可能，但风险极高且不可靠**

**分析**：
1. RevenueCat 的 `/v1/receipts` API 确实接受 `app_user_id` 参数
2. **但是**，RevenueCat 后端会进行多维度验证：
   - 同一 receipt 重复使用会被标记
   - `app_user_id` 与 receipt 中的 `original_app_user_id` 不匹配会触发异常
   - 单 receipt→多用户模式会被风控系统检测
3. 即使单次成功，也极可能导致：
   - RevenueCat 账户被封
   - OpenAI 账户被封
   - Apple ID 被标记为欺诈高风险
   - 退款/chargeback

**结论**：RevenueCat 不是"随便改 ID 就行"。平台有完整的滥用检测体系。

---

### 声明 5："成功率很高"

**教程原文**：暗示操作容易成功。

**核查结果**：❌ **无任何成功案例可验证**

**分析**：
1. 教程作者不提供任何交易哈希、订单号或成功截图
2. 所有"成功"信息来自教程文本本身，无法验证
3. 即使有成功案例，也可能是一次性运气，不代表可重复
4. 教程推广了 Telegram 群组和付费服务，存在明显的商业动机

**结论**：成功率未知，作者未提供可验证的证据。

---

## 🎯 综合评级

| 维度 | 评级 | 说明 |
|------|------|------|
| 技术准确性 | ❌ 低 | 核心声明（价格修改）错误 |
| 可行性 | ⚠️ 极低 | 需要 jailbreak + MITM + 签名证书，且结果不确定 |
| 风险 | 🔴 极高 | Apple ID 封禁、财务损失、法律风险 |
| 可信度 | ❌ 不可信 | 无成功证据，有商业推广动机 |

---

## 📚 参考

- [Apple StoreKit 2 Documentation](https://developer.apple.com/documentation/storekit)
- [RevenueCat REST API Documentation](https://www.revenuecat.com/docs/api-reference)
- [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [SSL Kill Switch 3 GitHub](https://github.com/nabla-c0d3/ssl-kill-switch3)

---

*本核查基于公开技术文档和行业知识，不构成法律建议。*
