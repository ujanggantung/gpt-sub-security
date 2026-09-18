# GPT Sub Analysis — Apple IAP Security & Fact-Check

> **Fact-check × Vulnerability analysis × Hardening guide**
> Security analysis of viral iOS ChatGPT subscription bypass tutorials
> 
> **Made by #napster**

![License](https://img.shields.io/badge/license-MIT-green)
![Last Updated](https://img.shields.io/badge/last--updated-2026--09--18-blue)
![Focus](https://img.shields.io/badge/focus-App%20Store%20IAP-lightgrey)

---

## ⚠️ Why this project exists

In September 2026, a tutorial about **"bypassing iOS ChatGPT subscriptions"** went viral on Telegram and GitHub. It claimed that by rewriting fields inside the App Store purchase request body, you could get a **Pro 20x ($200/month)** subscription at the **Plus price ($200/year)** — or hijack the RevenueCat callbacks to transfer the subscription to a different account.

**That tutorial is riddled with technical errors and misleading claims.**

This project exists to:

- 🔍 **Fact-check** — verify every technical claim in the tutorial, one by one
- 🛡️ **Attack-surface analysis** — classify iOS App Store IAP subscription abuse into 3 distinct classes
- 📚 **Hardening guidance** — concrete defense measures for developers and subscription platforms
- 🔧 **Practical tooling** — a StoreKit 2 JWS token viewer (educational)

**This project does NOT provide attack tooling or bypass methods. It is security research and education only.**

---

## 📋 Contents

| File | What's inside |
|------|---------------|
| [Fact-Check Report](docs/fact-check.md) | Verifies each claim in the viral tutorial, with accuracy + risk ratings |
| [IAP Subscription Flow](docs/iap-flow.md) | The real Apple In-App Purchase payment pipeline (StoreKit 2) |
| [Abuse Classes](docs/abuse-classes.md) | 3 classes of subscription abuse: technical detail + feasibility |
| [Hardening Guide](docs/hardening.md) | Developer-side defense-in-depth for subscription abuse |
| [References](docs/references.md) | Apple / RevenueCat official docs + industry resources |
| [Tool: JWS Viewer](scripts/jws_viewer.py) | Parse StoreKit 2 transaction JWS tokens (educational) |

---

## 🔬 Core Findings

### Tutorial claims vs reality

| Tutorial claim | Reality | Rating |
|----------------|---------|--------|
| Rewriting `price` gets you a discount | Apple's server prices from `salableAdamId`; client `price` is display-only | ❌ Misleading |
| Rewriting `offerName` activates hidden tiers | `offerName` is not part of the StoreKit 2 purchase request | ❌ Misleading |
| SSL Kill Switch 3 works globally | Requires per-daemon injection; Apple hardened pinning in iOS 16+ | ⚠️ Partially true |
| `app_user_id` can be freely transferred on RevenueCat | RevenueCat validates server-side; receipt replay is monitored | ⚠️ High risk |
| "High success rate" | No verifiable transaction hashes or successful case evidence | ❌ Untrustworthy |

### Abuse class feasibility

| Attack class | Feasibility | Requirements | Likely outcome |
|--------------|-------------|--------------|----------------|
| `buyProduct` request rewrite | ❌ Very low | jailbreak + MITM + valid signing | Server decides pricing; client edits are ignored |
| Receipt replay | ⚠️ Conditional | jailbreak + MITM + funded Apple account | May work once, then risk-flagged → Apple ID ban |
| Entitlement transfer | ⚠️ Conditional | exposed RevenueCat key + unlinked receipt | Many conditions must align; monitored pattern |

---

## 🛠️ JWS Viewer Tool

`scripts/jws_viewer.py` parses the payload of a StoreKit 2 transaction JWS token:

```bash
python scripts/jws_viewer.py <jws_token>
```

Prints `transactionId`, `productId`, `purchaseDate`, `expiresDate`, `type`, `environment`, etc. This tool does **not** verify signatures, recover keys, or forge anything.

> **Note:** StoreKit 2 tokens are signed by Apple private keys; the private key lives only on Apple servers. This tool only decodes the payload — pair it with Apple's App Store Server API on a trusted backend for real verification.

---

## 🏗️ Project Structure

```
gpt-sub-analysis/
├── README.md                           # This file
├── LICENSE                             # MIT License
├── CONTRIBUTING.md                     # Contribution guidelines
├── .gitignore
├── docs/
│   ├── fact-check.md                   # Fact-check report
│   ├── iap-flow.md                     # IAP subscription flow explained
│   ├── abuse-classes.md                # Abuse classification analysis
│   ├── hardening.md                    # Defense-in-depth guide
│   └── references.md                   # References
└── scripts/
    ├── jws_viewer.py                   # StoreKit 2 JWS viewer
    └── README.md                       # Tool usage docs
```

---

## 📜 Disclaimer

This project was created by security researchers to:

- Verify and correct technical misinformation spread on social media
- Understand the security boundaries of Apple App Store IAP
- Provide attack-surface analysis and defense guidance for subscription platforms

**All analysis is based on public documentation and known information and contains NO:**

- Zero-day vulnerability details
- Directly exploitable attack code
- Tooling to bypass Apple / RevenueCat security mechanisms

This project does not encourage illegal activity. Readers are responsible for complying with local laws and terms of service.

---

## 🤝 Contributing

PRs and Issues welcome; see [CONTRIBUTING.md](CONTRIBUTING.md) for the acceptance criteria (grounding rules, no attack tooling).

---

## 🐆 About

Created by **#napster** — independent security research, fact-checking, and dev tooling.

*Last updated: 2026-09-18*