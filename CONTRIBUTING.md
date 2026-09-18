# Contributing to GPT Sub Analysis

Thanks for your interest in contributing! This project exists to provide
accurate, well-grounded technical analysis of iOS In-App Purchase / subscription
security topics — the opposite of the misleading viral tutorials we analyze.

## What we accept

We welcome contributions that improve **accuracy**, **grounding**, or **defensive
guidance**:

- ✅ Fact-check corrections (must include a public source)
- ✅ Additional documented abuse classes / CVEs / real-world cases (cited)
- ✅ Developer-side hardening patterns (code, checklists, runbooks)
- ✅ Better references (official docs, research, talks)
- ✅ Clarifications, diagrams, translations

## What we do NOT accept

- ❌ Attack tooling / exploit code / step-by-step evasion instructions
- ❌ Requests to add "bypass" guides for App Store, RevenueCat, OpenAI, or any service
- ❌ Unverified claims presented as fact ("it worked for me, trust me")
- ❌ Plagiarized content

## Grounding rules

Any claim about how Apple / StoreKit / RevenueCat behaves **must** be backed by:

1. Official documentation (Apple Developer, RevenueCat docs), or
2. A reproducible experiment, or
3. A credible, cited industry source

If you're not sure, mark it as **speculative** in the doc rather than stating it
as fact. Misinformation is what we're fighting.

## Process

1. Open an issue describing the change, or comment on an existing one.
2. Fork the repo, create a branch (`docs/`, `chore/`, `feat/` prefix).
3. Make your change. Keep Chinese/English doc consistency (pick one per file and
   head to it; mixed headers + English body is fine as long as it's readable).
4. Open a pull request with a short description and check the `CONTRIBUTING.md` box.

## Security disclosures

If you believe you have found a **real, confirmed** vulnerability in Apple's IAP
flow, RevenueCat, or an app's subscription handling, do NOT post exploit details
here. Report it through:

- Apple Security Bounty: https://security.apple.com/bounty/
- RevenueCat Trust Center: https://www.revenuecat.com/trust-center/
- App vendors' own responsible-disclosure programs

This repo is for analysis and education, not for hosting 0-days.

## Code style

- Python 3.8+, standard library only
- Keep scripts dependency-free where possible
- `scripts/README.md` documents every script
- Target ~80 col where reasonable; readability over cleverness

---

*Last updated: 2026-09-18*