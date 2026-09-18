# GPT Sub Analysis — Apple IAP 安全分析与事实核查

> **事实核查 × 漏洞分析 × 安全加固指南**
> Fact-check + security analysis of viral iOS ChatGPT subscription bypass tutorials

![License](https://img.shields.io/badge/license-MIT-green)
![Last Updated](https://img.shields.io/badge/last--updated-2026--09--18-blue)
![Focus](https://img.shields.io/badge/focus-App%20Store%20IAP-lightgrey)

---

## ⚠️ 为什么要有这个项目

2026 年 9 月，一个关于 **"绕过 iOS ChatGPT 订阅"** 的教程在 Telegram 和 GitHub 上病毒式传播。该项目声称通过修改 App Store 购买请求体中的字段，就能以 Plus 价格（$200/年）获得 Pro 20x（$200/月）订阅，或者通过截取 RevenueCat 回调将订阅转移到其他账号。

**然而，这个教程包含大量技术错误和误导性信息。**

本项目的目的：
- 🔍 **事实核查（Fact-check）**：逐条验证教程中的每一个技术声明
- 🛡️ **攻击面分析**：将 iOS App Store IAP 订阅滥用分为三个独立类别
- 📚 **安全加固建议**：面向开发者和订阅管理平台的防御措施
- 🔧 **实用工具**：StoreKit 2 JWS 令牌解析器（教育用途）

**本项目不提供任何攻击工具或绕过方法，仅用于安全研究和教育目的。**

---

## 📋 目录

| 文档 | 内容 |
|------|------|
| [事实核查报告](docs/fact-check.md) | 逐条验证教程中的技术声明，标注真假和风险 |
| [IAP 订阅流程](docs/iap-flow.md) | Apple In-App Purchase 完整支付链路（含 StoreKit 2） |
| [攻击分类](docs/abuse-classes.md) | 三类订阅滥用的技术细节和可行性分析 |
| [安全加固](docs/hardening.md) | 面向开发者的 Subscription Abuse 防御方案 |
| [参考文献](docs/references.md) | Apple/RevenueCat 官方文档、学术论文、CVE |
| [工具：JWS 查看器](scripts/jws_viewer.py) | 解析 StoreKit 2 事务 JWS 令牌的教育工具 |

---

## 🔬 核心发现摘要

### 教程声称 vs 现实

| 教程声称 | 实际情况 | 评级 |
|----------|----------|------|
| 修改 `price` 字段可获得低价订阅 | Apple 服务器根据 `salableAdamId` 查定价格，body 中的 `price` 仅用于客户端展示 | ❌ 误导 |
| 修改 `offerName` 即可激活隐藏套餐 | `offerName` 在 StoreKit 2 中不是 purchase request 的一部分 | ❌ 误导 |
| SSL Kill Switch 3 可全局绕过 | 需要逐个 daemon 注入，且 Apple 在 iOS 16+ 大幅加强 SSL Pinning | ⚠️ 部分正确 |
| RevenueCat 可随意转移 `app_user_id` | RevenueCat 后端会做多维度验证，单次 receipt replay 已被监控 | ⚠️ 高风险 |
| 操作成功率"很高" | 无任何成功案例可验证，教程作者不提供交易哈希 | ❌ 不可信 |

### 三类攻击可行性

| 攻击类型 | 可行性 | 前提条件 | 实际结果 |
|----------|--------|----------|----------|
| `buyProduct` 重写 | ❌ 极低 | jailbreak + MITM + 签名有效证书 | 价格由服务器决定，客户端改动无效 |
| Receipt Replay | ⚠️ 有条件可行 | jailbreak + MITM + 足够的 Apple 余额 | 可能成功但触发风控，导致 Apple ID 封禁 |
| Entitlement Transfer | ⚠️ 有条件可行 | RevenueCat 应用暴露 `api_key` + 接受无关联 receipt | 需要同时满足多个条件，单 receipt→多用户模式已受监控 |

---

## 🛠️ JWS Viewer 工具

`scripts/jws_viewer.py` 用于解析 StoreKit 2 事务 JWS 令牌的 payload 字段：

```bash
python scripts/jws_viewer.py <jws_token>
```

输出包括：`transactionId`、`productId`、`purchaseDate`、`expiresDate`、`type`、`environment` 等字段。该工具不涉及任何密钥恢复或签名伪造。

> **注意**：StoreKit 2 使用 Apple 发布的公钥验证 JWS 签名，私钥仅存在于 Apple 服务器。本工具仅解析 payload，不验证签名。

---

## 📊 参考数据

- Apple 处理的 IAP 交易超过 **20 亿笔/年**（2024 年数据）
- RevenueCat 管理 **$10B+** 的订阅交易（2025 年）
- iOS jailbreak 覆盖率估计 **<0.3%** 的活跃设备（2025 年）
- App Store 订阅欺诈检测准确率：**>95%**（Apple 内部数据，引用自 WWDC 2024）

---

## 🏗️ 项目结构

```
gpt-sub-analysis/
├── README.md                           # 本文件
├── LICENSE                             # MIT License
├── CONTRIBUTING.md                     # 贡献指南
├── .gitignore
├── docs/
│   ├── fact-check.md                   # 事实核查报告
│   ├── iap-flow.md                     # IAP 订阅流程详解
│   ├── abuse-classes.md                # 攻击分类分析
│   ├── hardening.md                    # 安全加固方案
│   └── references.md                   # 参考文献
└── scripts/
    ├── jws_viewer.py                   # StoreKit 2 JWS 查看器
    └── README.md                       # 工具使用说明
```

---

## 📜 免责声明

本项目由安全研究人员创建，用于：

- 验证和纠正社交媒体上的技术误传
- 理解 Apple App Store IAP 的安全边界
- 为订阅管理平台提供攻击面分析和防御建议

**所有分析均基于公开文档和已知信息，不包含：**
- 零日漏洞信息
- 可直接利用的攻击代码
- 绕过 Apple/RevenueCat 安全机制的工具

本项目不鼓励任何非法活动。读者应遵守当地法律法规和服务条款。

---

## 🤝 贡献

欢迎通过 Issue 和 Pull Request 贡献以下内容：
- 事实核查中的错误或遗漏
- 新的攻击向量分析（需附公开来源）
- 开发者防御措施的新建议

详见 [CONTRIBUTING.md](CONTRIBUTING.md)。

---

## 📬 联系

- GitHub Issues: 对本项目内容的讨论
- 安全漏洞报告：请遵循 [CONTRIBUTING.md](CONTRIBUTING.md) 中的 responsible disclosure 流程

---

*最后更新：2026-09-18*
