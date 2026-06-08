"""
GPT Usage Widget — Codex Quota API Client
Uses ChatGPT session cookie to fetch Codex compute quota via internal backend APIs.

Auth flow:
  1. User provides full Cookie header from browser
  2. Widget calls /api/auth/session → gets Bearer access token (cached!)
  3. Bearer token used for /backend-api/* quota endpoints
  4. On subsequent refreshes, reuse cached token (no Cloudflare needed)

Uses curl_cffi to impersonate Chrome TLS fingerprint (bypasses Cloudflare).
"""
import json
import time
from dataclasses import dataclass, field
from typing import Any, Optional

from curl_cffi import requests as cf_requests
from PyQt6.QtCore import QThread, pyqtSignal

CHATGPT_BASE = "https://chatgpt.com"
TIMEOUT = 15

# Ordered list of endpoints to probe for quota data
QUOTA_ENDPOINTS = [
    "/backend-api/wham/usage",
    "/backend-api/codex/usage",
    "/backend-api/usage_status",
    "/backend-api/agentic/limits",
    "/backend-api/accounts/check/v4-2023-04-27",
    "/backend-api/accounts/check",
]

# ── Token cache (module-level, survives across worker instances) ──────────
_cached_access_token: str = ""
_cached_token_time: float = 0.0
_cached_user_info: dict = {}
_cached_expires: str = ""
_cached_account_id: str = ""
TOKEN_CACHE_SECONDS = 30 * 60  # reuse token for up to 30 minutes


@dataclass
class CodexData:
    # ── Period quota (5-hour window) ──────────────────────────────────────────
    period_label: str = "5小时额度"
    period_used_h: float = 0.0       # hours consumed in current period
    period_total_h: float = 0.0      # total hours per period, if known
    period_percent: float = 0.0      # remaining percent, 0‒100

    # ── Weekly quota ──────────────────────────────────────────────────────────
    weekly_label: str = "周额度"
    weekly_used_h: float = 0.0
    weekly_total_h: float = 0.0
    weekly_percent: float = 0.0

    # ── User info ─────────────────────────────────────────────────────────────
    user_name: str = ""
    user_email: str = ""
    plan: str = "ChatGPT Plus"
    session_expires: str = ""        # ISO datetime string

    # ── Debug ─────────────────────────────────────────────────────────────────
    raw_quota: dict = field(default_factory=dict)
    data_source: str = ""            # which endpoint returned data

    @property
    def period_remaining_h(self) -> float:
        return max(0.0, self.period_total_h - self.period_used_h)

    @property
    def weekly_remaining_h(self) -> float:
        return max(0.0, self.weekly_total_h - self.weekly_used_h)


class CodexAPIWorker(QThread):
    """Background thread: session cookies → access token → quota data."""
    data_ready = pyqtSignal(object)   # CodexData
    error = pyqtSignal(str)

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self._config = config  # ConfigManager instance

    def run(self):
        try:
            data = self._fetch()
            self.data_ready.emit(data)
        except SessionExpiredError:
            self.error.emit("Session 已过期，请重新获取 Cookie")
        except APIError as e:
            self.error.emit(str(e))
        except Exception as e:
            err_str = str(e)
            if "connect" in err_str.lower() or "resolve" in err_str.lower():
                self.error.emit("网络连接失败：检查代理设置")
            elif "timeout" in err_str.lower():
                self.error.emit("请求超时：请检查代理或稍后重试")
            else:
                self.error.emit(f"错误: {e}")

    # ──────────────────────────────────────────────────────────────────────────

    def _fetch(self) -> CodexData:
        global _cached_access_token, _cached_token_time
        global _cached_user_info, _cached_expires, _cached_account_id

        # Try cached token first (avoids Cloudflare entirely)
        age = time.time() - _cached_token_time
        if _cached_access_token and age < TOKEN_CACHE_SECONDS:
            print(f"[API] Using cached access token (age={int(age)}s)")
            access_token = _cached_access_token
            user_info = _cached_user_info
            expires = _cached_expires
            account_id = _cached_account_id
        else:
            # Need fresh token — requires cookies (Cloudflare)
            print("[API] Cached token expired or missing, fetching new one...")
            access_token, user_info, expires, account_id = self._get_access_token()
            # Cache it
            _cached_access_token = access_token
            _cached_token_time = time.time()
            _cached_user_info = user_info
            _cached_expires = expires
            _cached_account_id = account_id
            print(f"[API] Access token cached for {TOKEN_CACHE_SECONDS}s")

        data = CodexData(
            user_name=user_info.get("name", ""),
            user_email=user_info.get("email", ""),
            session_expires=expires,
        )

        # Query quota endpoints using Bearer token (no Cloudflare needed!)
        auth_headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://chatgpt.com/codex",
            "Origin": "https://chatgpt.com",
        }
        if account_id:
            auth_headers["ChatGPT-Account-Id"] = account_id

        found_quota = False

        for endpoint in QUOTA_ENDPOINTS:
            try:
                resp = cf_requests.get(
                    CHATGPT_BASE + endpoint,
                    headers=auth_headers,
                    impersonate="chrome",
                    timeout=TIMEOUT,
                    **self._request_kwargs(),
                )
                print(f"[API] {endpoint} -> {resp.status_code}")
                if resp.status_code == 404:
                    continue
                if resp.status_code == 401:
                    if endpoint == "/backend-api/wham/usage" and not account_id:
                        print("[API] wham/usage requires account id; trying fallback endpoints")
                        continue
                    # Token might be invalid, clear cache and retry once
                    if _cached_access_token:
                        print("[API] 401 — clearing cached token, will retry next cycle")
                        _cached_access_token = ""
                        _cached_token_time = 0
                    raise SessionExpiredError()
                if not resp.ok:
                    continue

                body = resp.json()
                data.raw_quota = body
                data.data_source = endpoint

                if self._parse_quota(body, data):
                    found_quota = True
                    break
            except (json.JSONDecodeError, ValueError):
                continue
            except SessionExpiredError:
                raise

        if not found_quota:
            raise APIError("已连接，但没有解析到 Codex 额度字段")

        return data

    def _get_access_token(self) -> tuple:
        """Call /api/auth/session with raw Cookie header → (access_token, user, expires)."""
        raw_cookie = self._config.get_raw_cookies()
        if not raw_cookie:
            raise APIError("请先在设置中配置 Cookie")

        cookie_count = len([p for p in raw_cookie.split(";") if "=" in p])
        print(f"[API] Calling /api/auth/session (curl_cffi/chrome, {cookie_count} cookies)")

        headers = {
            "Cookie": raw_cookie,
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
            "Accept": "application/json",
            "Referer": "https://chatgpt.com/",
            "Origin": "https://chatgpt.com",
        }

        resp = cf_requests.get(
            f"{CHATGPT_BASE}/api/auth/session",
            headers=headers,
            impersonate="chrome",
            timeout=TIMEOUT,
            **self._request_kwargs(),
        )
        print(f"[API] /api/auth/session -> {resp.status_code}")
        ct = resp.headers.get("content-type", "")

        if resp.status_code in (401, 403):
            if "text/html" in ct:
                raise APIError(
                    "被 Cloudflare 拦截 (403)。\n"
                    "请从浏览器 F12 → Network 标签复制最新的完整 Cookie 请求头。\n"
                    "（cf_clearance cookie 有效期很短，需要重新获取）"
                )
            raise SessionExpiredError()
        if not resp.ok:
            raise APIError(f"认证失败 HTTP {resp.status_code}")

        body = resp.json()
        print(f"[API] session response keys: {list(body.keys())}")
        access_token = body.get("accessToken", "")
        if not access_token:
            raise SessionExpiredError()

        user = body.get("user", {})
        expires = body.get("expires", "")
        account_id = self._extract_account_id(body)
        if account_id:
            print(f"[API] account_id detected: {account_id[:8]}...")
        return access_token, user, expires, account_id

    def _request_kwargs(self) -> dict:
        proxy_url = self._config.get_proxy_url()
        if proxy_url:
            print(f"[API] Using proxy: {self._mask_proxy(proxy_url)}")
            return {"proxy": proxy_url}
        print("[API] No proxy configured")
        return {}

    def _mask_proxy(self, proxy_url: str) -> str:
        if "@" not in proxy_url:
            return proxy_url
        prefix, suffix = proxy_url.rsplit("@", 1)
        scheme = prefix.split("://", 1)[0] if "://" in prefix else "proxy"
        return f"{scheme}://***@{suffix}"

    def _parse_quota(self, body: dict, data: CodexData) -> bool:
        """
        Try to extract period + weekly quota from various response shapes.
        Returns True if at least one quota value was found.
        """
        found = False

        # Wham usage shape:
        # {"rate_limit": {"five_hour": {...percent_left...}, "weekly": {...}}}
        rate_limits = self._first_dict(body, "rate_limit", "rate_limits")
        if rate_limits:
            period, weekly = self._parse_rate_limits(rate_limits)
            if period is not None:
                data.period_total_h = 0.0
                data.period_used_h = 0.0
                data.period_percent = period
                found = True
            if weekly is not None:
                data.weekly_total_h = 0.0
                data.weekly_used_h = 0.0
                data.weekly_percent = weekly
                found = True

        # ── Pattern A: flat keys like period_compute_* / weekly_compute_* ──
        mapping = {
            "period_compute_hours_used":   ("period_used_h", None),
            "period_compute_hours_total":  ("period_total_h", None),
            "period_compute_pct":          ("period_percent", "used_percent"),
            "period_compute_percent_left": ("period_percent", "remaining_percent"),
            "period_remaining_percent":    ("period_percent", "remaining_percent"),
            "period_remaining_pct":        ("period_percent", "remaining_percent"),
            "weekly_compute_hours_used":   ("weekly_used_h", None),
            "weekly_compute_hours_total":  ("weekly_total_h", None),
            "weekly_compute_pct":          ("weekly_percent", "used_percent"),
            "weekly_compute_percent_left": ("weekly_percent", "remaining_percent"),
            "weekly_remaining_percent":    ("weekly_percent", "remaining_percent"),
            "weekly_remaining_pct":        ("weekly_percent", "remaining_percent"),
            # alternate names
            "compute_hours_used":          ("period_used_h", None),
            "compute_hours_limit":         ("period_total_h", None),
            "compute_hours_weekly_used":   ("weekly_used_h", None),
            "compute_hours_weekly_limit":  ("weekly_total_h", None),
        }
        for key, (attr, kind) in mapping.items():
            if key in body:
                value = self._to_float(body[key])
                if value is None:
                    continue
                if kind == "used_percent":
                    value = 100.0 - self._normalize_percent(value)
                elif kind == "remaining_percent":
                    value = self._normalize_percent(value)
                setattr(data, attr, value)
                found = True

        # ── Pattern B: nested under "codex" key ──
        for section_key in ("codex", "agentic", "compute", "limits"):
            if section_key in body and isinstance(body[section_key], dict):
                found = self._parse_quota(body[section_key], data) or found

        # ── Pattern C: "model_limits" list containing codex entries ──
        for key in ("model_limits", "limits", "usage_limits"):
            if key in body and isinstance(body[key], list):
                for item in body[key]:
                    if not isinstance(item, dict):
                        continue
                    model = str(item.get("model", item.get("name", ""))).lower()
                    if "codex" in model or "computer" in model or "agent" in model:
                        used = item.get("used", item.get("consumed", 0))
                        total = item.get("limit", item.get("total", 0))
                        if total:
                            data.period_used_h = float(used)
                            data.period_total_h = float(total)
                            data.period_percent = max(
                                0.0,
                                100.0 - data.period_used_h / data.period_total_h * 100.0
                            )
                            found = True

        # ── Compute remaining percentages if we have used+total ──
        if data.period_total_h > 0 and data.period_percent == 0:
            data.period_percent = max(0.0, min(100.0,
                100.0 - data.period_used_h / data.period_total_h * 100.0))
        if data.weekly_total_h > 0 and data.weekly_percent == 0:
            data.weekly_percent = max(0.0, min(100.0,
                100.0 - data.weekly_used_h / data.weekly_total_h * 100.0))

        return found

    def _parse_rate_limits(self, rate_limits: dict) -> tuple:
        period = None
        weekly = None

        for key in ("five_hour", "five_hour_limit", "five_hour_rate_limit", "primary"):
            if key in rate_limits:
                period = self._parse_limit_entry(rate_limits.get(key))
                if period is not None:
                    break
        for key in ("weekly", "weekly_limit", "weekly_rate_limit", "secondary"):
            if key in rate_limits:
                weekly = self._parse_limit_entry(rate_limits.get(key))
                if weekly is not None:
                    break

        if period is None:
            period = self._parse_limit_entry(rate_limits.get("primary_window"))
        if weekly is None:
            weekly = self._parse_limit_entry(rate_limits.get("secondary_window"))

        return period, weekly

    def _parse_limit_entry(self, value: Any) -> Optional[float]:
        if not isinstance(value, dict):
            return None

        if (
            "reset_at" not in value
            and "reset_time_ms" not in value
            and isinstance(value.get("primary_window"), dict)
        ):
            value = value["primary_window"]

        for key in (
            "percent_left",
            "remaining_percent",
            "percent_remaining",
            "remaining_pct",
            "remainingPercentage",
        ):
            percent = self._to_float(value.get(key))
            if percent is not None:
                return self._normalize_percent(percent)

        for key in ("used_percent", "percent_used", "used_pct", "usage_percent"):
            used_percent = self._to_float(value.get(key))
            if used_percent is not None:
                return max(0.0, 100.0 - self._normalize_percent(used_percent))

        remaining = self._to_float(value.get("remaining"))
        total = self._to_float(value.get("limit", value.get("total")))
        if remaining is not None and total and total > 0:
            return max(0.0, min(100.0, remaining / total * 100.0))

        return None

    def _first_dict(self, data: Any, *keys: str) -> Optional[dict]:
        if not isinstance(data, dict):
            return None
        for key in keys:
            value = data.get(key)
            if isinstance(value, dict):
                return value
        return None

    def _to_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _normalize_percent(self, value: float) -> float:
        if 0 <= value <= 1:
            value *= 100.0
        return max(0.0, min(100.0, value))

    def _extract_account_id(self, body: dict) -> str:
        explicit = self._find_string_key(
            body,
            {
                "account_id",
                "accountid",
                "current_account_id",
                "currentaccountid",
                "selected_account_id",
                "selectedaccountid",
            },
        )
        if explicit:
            return explicit

        user = body.get("user")
        if isinstance(user, dict):
            accounts = user.get("accounts")
            if isinstance(accounts, list):
                for account in accounts:
                    if isinstance(account, dict):
                        account_id = account.get("id") or account.get("account_id")
                        if isinstance(account_id, str) and account_id:
                            return account_id
        return ""

    def _find_string_key(self, value: Any, names: set) -> str:
        if isinstance(value, dict):
            for key, child in value.items():
                norm = str(key).replace("-", "_").lower()
                if norm in names and isinstance(child, str) and child:
                    return child
            for child in value.values():
                found = self._find_string_key(child, names)
                if found:
                    return found
        elif isinstance(value, list):
            for child in value:
                found = self._find_string_key(child, names)
                if found:
                    return found
        return ""


class SessionExpiredError(Exception):
    pass


class APIError(Exception):
    pass
