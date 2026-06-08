"""Test curl_cffi vs requests for Cloudflare bypass."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.config_manager import ConfigManager
c = ConfigManager()
raw_cookie = c.get_raw_cookies()
print(f"Cookie length: {len(raw_cookie)}")

# Test with curl_cffi (Chrome TLS fingerprint)
from curl_cffi import requests as cf_requests

resp = cf_requests.get(
    "https://chatgpt.com/api/auth/session",
    headers={
        "Cookie": raw_cookie,
        "Accept": "application/json",
        "Referer": "https://chatgpt.com/",
    },
    impersonate="chrome",
    timeout=15,
)
print(f"\ncurl_cffi status: {resp.status_code}")
print(f"content-type: {resp.headers.get('content-type', 'unknown')}")
text = resp.text[:500]
print(f"body (first 500): {text}")
