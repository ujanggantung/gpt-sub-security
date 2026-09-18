# Fact-Check Report: The "iOS ChatGPT Pro 20x Bypass" Tutorial

> This report verifies, claim by claim, the technical assertions in the September 2026 viral tutorial "iOS ChatGPT Pro 20x 开通教程" (made by #napster).

---

## 📌 Source

- **Origin**: GitHub repo `engineerbas/gpt_sub_analysis` (with Telegram contact info)
- **Spread**: Telegram groups + Chinese tech communities
- **Claim**: Rewriting App Store purchase request fields gets Pro 20x at the Plus price
- **Associated**: `codex-x.site`, `yynxxxxx/Codex-X` (same author's other projects)

---

## 🔍 Claim-by-claim verification

### Claim 1: "Rewriting `price` gets you a discount"

**Original claim**: Change `offerName` from `oai_chatgpt_plus_20000_1y` to `oai_chatgpt_pro_20000_1m`, change `salableAdamId` from `6745416289` to `6657954405`, keep `price` at `200000`.

**Result**: ❌ **Incorrect**

**Analysis**:
1. App Store prices are set in App Store Connect and bound to the `salableAdamId`
2. The `price` field in a StoreKit 2 purchase is **not part of server-side price verification**
3. Apple's server looks up the real price for the `salableAdamId`; the client-supplied `price` is display-only
4. Even if you send `price=200000`, if that `salableAdamId` is actually priced at $200/month, you are billed $200/month

**Evidence**:
- [Apple StoreKit 2 Documentation](https://developer.apple.com/documentation/storekit) includes no client-controlled `price` for purchases
- App Store purchase requests use Apple's private plist format; `price` is for logging/UI only
- Modifying `salableAdamId` triggers server-side validation (wrong app link, wrong price, or error)

**Conclusion**: This operation either fails (server rejects) or genuinely purchases Pro 20x **at its real $200/month price**.

---

### Claim 2: "Rewriting `offerName` activates hidden tiers"

**Original claim**: Change `offerName` from `oai_chatgpt_plus_20000_1y` to `oai_chatgpt_pro_20000_1m`.

**Result**: ❌ **Incorrect**

**Analysis**:
1. StoreKit 2 purchase APIs use `productIdentifier`, not `offerName`
2. `offerName` is not a documented field in Apple's purchase request
3. The App Store identifies products by numeric `salableAdamId` (or `productId`), not by name strings
4. Changing `offerName` without also changing `salableAdamId` is contradictory

**Conclusion**: `offerName` likely doesn't exist in the real request (or is client-internal only). Editing it does not affect server behavior.

---

### Claim 3: "SSL Kill Switch 3 works globally"

**Original claim**: Install SSL Kill Switch 3 from Sileo and enable it globally.

**Result**: ⚠️ **Partially true, oversimplified**

**Analysis**:
1. SSL Kill Switch 3 can disable some SSL pinning
2. Apple significantly hardened SSL pinning in iOS 16+
3. Not every system daemon can be injected with tweaks
4. The 5 daemons listed (`cloudd`, `accountsd`, `identityservicesd`, `akd`, `nsurlsessiond`) do handle IAP-related traffic, but injection success depends on jailbreak + iOS versions
5. It requires Choicy per-daemon configuration — not a "global toggle"

**Conclusion**: Possible on specific jailbreak+iOS combos, but the tutorial oversimplifies setup difficulty.

---

### Claim 4: "`app_user_id` can be freely transferred on RevenueCat"

**Original claim**: Replace `app_user_id` with the target account ID and re-send to complete the transfer.

**Result**: ⚠️ **Technically possible, very high risk, unreliable**

**Analysis**:
1. RevenueCat's `/v1/receipts` does accept an `app_user_id` parameter
2. **But** RevenueCat validates server-side:
   - Reuse of the same receipt is flagged
   - Mismatches between `app_user_id` and the receipt's demographics trigger review
   - One-receipt-many-users patterns are detected by risk systems
3. Even a single success can result in:
   - RevenueCat account suspension
   - OpenAI account suspension
   - Apple ID flagged as fraud-risk
   - Refund / chargeback

**Conclusion**: RevenueCat is not a "just change the ID" system. Complete abuse-detection exists.

---

### Claim 5: "High success rate"

**Original claim**: The tutorial implies high success.

**Result**: ❌ **No verifiable evidence**

**Analysis**:
1. No transaction hashes, order numbers, or verified success screenshots are provided
2. All "success" claims come from the tutorial text itself
3. Even a real success would be anecdotal, not reproducible
4. The tutorial promotes a Telegram group and paid services — clear financial incentive

**Conclusion**: Success rate unknown; the author provides no verifiable evidence.

---

## 🎯 Summary rating

| Dimension | Rating | Reason |
|-----------|--------|--------|
| Technical accuracy | ❌ Low | Core claim (price rewrite) is wrong |
| Feasibility | ⚠️ Very low | Needs jailbreak + MITM + signed certs, uncertain result |
| Risk | 🔴 Extreme | Apple ID ban, financial loss, legal exposure |
| Trustworthiness | ❌ Low | No success evidence, commercial promotion motive |

---

## 📚 References

- [Apple StoreKit 2 Documentation](https://developer.apple.com/documentation/storekit)
- [RevenueCat REST API](https://www.revenuecat.com/docs/api-reference)
- [Apple App Store Review Guidelines](https://developer.apple.com/app-store/review/guidelines/)
- [SSL Kill Switch 3](https://github.com/nabla-c0d3/ssl-kill-switch3)

---

*Fact-check by #napster. This is a technical analysis, not legal advice.*