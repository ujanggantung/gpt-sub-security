#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
jws_viewer.py — StoreKit 2 Transaction JWS Payload Viewer (EDUCATIONAL)

Parses the payload of a StoreKit 2 transaction JWS token (the signed receipt
returned by Apple when a user purchases an auto-renewable subscription).

What this tool does:
  - Splits the JWS into header.payload.signature
  - Base64-decodes the header and payload
  - Pretty-prints the payload fields with human-readable timestamps

What this tool does NOT do:
  - It does NOT verify the JWS signature (that requires Apple's root CA and
    the full cert chain; on-device StoreKit 2 does this automatically).
  - It does NOT forge, modify, or re-sign anything.
  - It does NOT contact Apple, RevenueCat, or any network service.

Usage:
    python jws_viewer.py <jws_token>
    python jws_viewer.py --sample          # print a synthetic example
    cat token.txt | python jws_viewer.py   # read from stdin

Exit codes:
    0  success
    1  invalid JWS / decode error
    2  usage error
"""

from __future__ import annotations

import base64
import json
import sys
from datetime import datetime, timezone

# Human-readable labels for known StoreKit 2 payload fields (Apple's "JWSDecodedPayload").
FIELD_LABELS = {
    "appAccountToken": "App Account Token (appAccountToken)",
    "bundleId": "Bundle ID (bundleId)",
    "environment": "Environment",
    "expiresDate": "Expires (epoch ms)",
    "inAppOwnershipType": "Ownership Type",
    "isUpgraded": "Was Upgraded",
    "offerIdentifier": "Offer Identifier",
    "offerType": "Offer Type",
    "originalPurchaseDate": "Original Purchase (epoch ms)",
    "originalTransactionId": "Original Transaction ID",
    "productId": "Product ID",
    "purchaseDate": "Purchase Date (epoch ms)",
    "quantity": "Quantity",
    "revocationDate": "Revocation Date (epoch ms)",
    "revocationReason": "Revocation Reason",
    "signedDate": "Signed Date (epoch ms)",
    "subscriptionGroupIdentifier": "Subscription Group ID",
    "transactionId": "Transaction ID",
    "type": "Type",
    "webOrderLineItemId": "Web Order Line Item ID",
    "currency": "Currency",
    "price": "Price (milliunits)",
}

# Group identifiers are shared across a subscription group (e.g. ChatGPT's group 6749460546).
KNOWN_SUBSCRIPTION_GROUPS = {
    "6749460546": "ChatGPT subscription group (referenced in public tutorials)",
}


def b64url_decode(segment: str) -> bytes:
    """Decode a base64url segment, adding padding as needed."""
    pad = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + pad)


def epoch_ms_to_iso(ms):
    """Convert epoch milliseconds to ISO 8601 UTC string."""
    try:
        return datetime.fromtimestamp(int(ms) / 1000, tz=timezone.utc).strftime(
            "%Y-%m-%d %H:%M:%S UTC"
        )
    except (TypeError, ValueError, OverflowError):
        return "(invalid timestamp)"


def parse_jws(token: str) -> dict:
    """Parse a JWS string into header/payload/signature dicts."""
    parts = token.strip().split(".")
    if len(parts) != 3:
        raise ValueError(
            f"Expected 3 dot-separated JWS segments, got {len(parts)}. "
            "A StoreKit 2 transaction token looks like: <header>.<payload>.<signature>"
        )

    header_b64, payload_b64, signature_b64 = parts

    try:
        header = json.loads(b64url_decode(header_b64).decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Could not decode JWS header: {e}")

    try:
        payload = json.loads(b64url_decode(payload_b64).decode("utf-8"))
    except Exception as e:
        raise ValueError(f"Could not decode JWS payload: {e}")

    return {"header": header, "payload": payload, "signature_b64": signature_b64}


def format_timestamps(payload: dict) -> dict:
    """Return a shallow copy of payload with epoch-ms fields annotated."""
    out = dict(payload)
    for key in (
        "expiresDate",
        "originalPurchaseDate",
        "purchaseDate",
        "revocationDate",
        "signedDate",
    ):
        if key in out and isinstance(out[key], (int, float)):
            out[key] = f"{out[key]}  →  {epoch_ms_to_iso(out[key])}"
    return out


def render(parsed: dict) -> str:
    """Render the parsed JWS as a readable report."""
    lines = []
    header = parsed["header"]
    payload = parsed["payload"]

    lines.append("=" * 60)
    lines.append("StoreKit 2 Transaction JWS — Payload Viewer (educational)")
    lines.append("=" * 60)
    lines.append("")
    lines.append("[ JWS Header ]")
    lines.append(f"  Algorithm      : {header.get('alg', '(missing)')}")
    lines.append(f"  Key ID (kid)   : {header.get('kid', '(missing)')}")
    certs = header.get("x5c") or []
    lines.append(f"  Cert Chain     : {len(certs)} cert(s) in x5c")
    for i, c in enumerate(certs[:3], 1):
        lines.append(f"      [{i}] {c[:48]}...")
    lines.append(f"  Token Type     : {header.get('typ', '(missing)')}")
    lines.append("")

    lines.append("[ JWS Payload — JWSDecodedPayload fields ]")
    if not payload:
        lines.append("  (empty payload)")
    for key, raw in payload.items():
        label = FIELD_LABELS.get(key, key.replace("_", " ").title())
        value = raw
        if isinstance(raw, dict):
            value = json.dumps(raw, ensure_ascii=False, indent=6)
        elif isinstance(raw, list):
            value = json.dumps(raw, ensure_ascii=False)
        lines.append(f"  {label}:")
        lines.append(f"      {value}")
    lines.append("")

    group_id = payload.get("subscriptionGroupIdentifier")
    if group_id in KNOWN_SUBSCRIPTION_GROUPS:
        lines.append(f"  -> Group {group_id}: {KNOWN_SUBSCRIPTION_GROUPS[group_id]}")

    lines.append("")
    lines.append("[ Signature ]")
    sig = parsed["signature_b64"]
    lines.append(f"  {sig[:32]}...{sig[-16:] if len(sig) > 48 else ''} ({len(sig)} chars)")
    lines.append("")
    lines.append(
        "NOTE: Signature verification is NOT performed here. StoreKit 2 verifies it"
    )
    lines.append("on-device using Apple's public keys. Do not trust un-verified tokens.")
    lines.append("=" * 60)
    return "\n".join(lines)


SAMPLE_TOKEN_PAYLOAD = {
    "appAccountToken": "a7a1c9a5-6c03-4b2e-9d48-0f0e1d2c3b4a",
    "bundleId": "com.openai.chat",
    "environment": "Production",
    "expiresDate": 1779118400000,
    "inAppOwnershipType": "PURCHASED",
    "isUpgraded": False,
    "offerIdentifier": None,
    "originalPurchaseDate": 1775854400000,
    "originalTransactionId": "490001234567890",
    "productId": "oai_chatgpt_plus_1999_1m",
    "purchaseDate": 1775854400000,
    "quantity": 1,
    "revocationDate": None,
    "revocationReason": None,
    "signedDate": 1775854400000,
    "subscriptionGroupIdentifier": "6749460546",
    "transactionId": "490001234567890",
    "type": "Auto-Renewable Subscription",
    "webOrderLineItemId": "490001234567890",
}


def make_sample_token() -> str:
    """Build a synthetic (unsigned, for demo) JWS string from SAMPLE_TOKEN_PAYLOAD."""
    header_b64 = base64.urlsafe_b64encode(
        json.dumps(
            {
                "alg": "ES256",
                "kid": "K4GkGMfGhMxiWmQKnI0GredqTylpA0llT2LbQxh8WQ",
                "typ": "JWT",
                "x5c": ["MIIBzTCCAXWgAwIBAgI... (synthetic cert chain)"],
            },
            separators=(",", ":"),
        ).encode()
    ).decode().rstrip("=")

    payload_b64 = base64.urlsafe_b64encode(
        json.dumps(SAMPLE_TOKEN_PAYLOAD, separators=(",", ":")).encode()
    ).decode().rstrip("=")

    # Explicitly NOT a real signature — token is for structure illustration only.
    fake_sig = "SYNTHETIC_SIGNATURE_FOR_DEMO_ONLY_" + "A" * 60
    return f"{header_b64}.{payload_b64}.{fake_sig}"


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] in ("-h", "--help"):
        print(__doc__)
        return 0
    if len(argv) == 2 and argv[1] == "--sample":
        token = make_sample_token()
        print(f"# Synthetic demo token (NOT a real transaction):")
        parsed = parse_jws(token)
        print(render(parsed))
        return 0

    if len(argv) == 2:
        token = argv[1]
    elif len(argv) == 1:
        # Read from stdin (e.g. `cat token.txt | python jws_viewer.py`)
        token = sys.stdin.read().strip()
        if not token:
            print("error: no JWS token provided (stdin was empty)", file=sys.stderr)
            return 2
    else:
        print(__doc__)
        return 2

    try:
        parsed = parse_jws(token)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1

    print(render(parsed))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))