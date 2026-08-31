#!/usr/bin/env python3
"""Generate VAPID keys for Web Push. Requires: pip install pywebpush"""

from __future__ import annotations

try:
    from py_vapid import Vapid
except ImportError as exc:
    raise SystemExit("Install pywebpush first: pip install pywebpush") from exc

v = Vapid()
v.generate_keys()
pub = v.public_key
priv = v.private_key
if isinstance(pub, bytes):
    pub = pub.decode()
if isinstance(priv, bytes):
    priv = priv.decode()
print("Add to backend/.env:\n")
print(f"WEB_PUSH_VAPID_PUBLIC_KEY={pub}")
print(f"WEB_PUSH_VAPID_PRIVATE_KEY={priv}")
print("WEB_PUSH_VAPID_SUBJECT=mailto:you@example.com")
