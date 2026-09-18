# Scripts

Tools included in this repository (educational / defensive use only).

## jws_viewer.py — StoreKit 2 Transaction JWS Viewer

Parses and pretty-prints the payload of a StoreKit 2 transaction JWS token
(the signed receipt Apple returns for an in-app purchase / subscription).

### Why

Viral "ChatGPT subscription bypass" tutorials tell readers to copy tokens and
edit `app_user_id` / `offerName` / `salableAdamId` fields. Understanding the
actual structure of the token is the first step in realizing:

- the payload is signed (you cannot just edit fields)
- the payload is validated server-side, not client-side
- critical fields (`transactionId`, `bundleId`, `environment`, `expiresDate`)
  exist specifically to prevent replay and forgery

### Usage

```bash
# Parse a real (or synthetic) StoreKit 2 JWS token
python jws_viewer.py <jws_token>

# Print a synthetic example so you can see the structure without a token
python jws_viewer.py --sample

# Read from stdin
cat token.txt | python jws_viewer.py
```

### Example output (synthetic)

```
============================================================
StoreKit 2 Transaction JWS — Payload Viewer (educational)
============================================================

[ JWS Header ]
  Algorithm      : ES256
  Key ID (kid)   : K4GkGMfGhMxiWmQKnI0GredqTylpA0llT2LbQxh8WQ
  Cert Chain     : 1 cert(s) in x5c
      [1] MIIBzTCCAXWgAwIBAgI... (synthetic cert chain)
  Token Type     : JWT

[ JWS Payload — JWSDecodedPayload fields ]
  Bundle ID (bundleId):
      com.openai.chat
  Environment:
      Production
  ...
  -> Group 6749460546: ChatGPT subscription group (referenced in public tutorials)

[ Signature ]
  SYNTHETIC_SIGNATURE_FOR_DEMO_ONLY_...AAAA (100 chars)

NOTE: Signature verification is NOT performed here...
============================================================
```

### Important

- The tool **does not verify signatures** — put real tokens through Apple's
  App Store Server API on a trusted backend before trusting them.
- The tool **does not modify or forge** anything.
- The synthetic sample token is clearly marked and contains no real data.

## Requirements

- Python 3.8+
- Standard library only (no third-party dependencies)