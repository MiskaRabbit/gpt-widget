"""
GPT Usage Widget — Config Manager (Codex version)
Handles settings persistence and secure session token storage via keyring.
"""
import json
import os
import sys
from pathlib import Path
from typing import Any, Optional

IS_WINDOWS = sys.platform.startswith("win")
IS_MACOS = sys.platform == "darwin"

if IS_WINDOWS:
    import winreg
else:
    winreg = None

try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

KEYRING_SERVICE = "gpt-usage-widget"
KEYRING_USER = "chatgpt-cookie-header"

CONFIG_DIR = Path.home() / ".gpt-widget"
CONFIG_FILE = CONFIG_DIR / "settings.json"

DEFAULT_SETTINGS: dict = {
    "theme": "dark_glass",
    "refresh_interval_minutes": 5,
    "window_x": 60,
    "window_y": 60,
    "window_opacity": 92,
    "show_on_startup": True,
    "auto_start": False,
    "expanded": False,
    "minimal_mode": False,
    "proxy_url": "",
    "auto_detect_proxy": True,
}

AUTOSTART_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_NAME = "GPTUsageWidget"
COOKIE_CONFIG_KEYS = (
    "_raw_cookies",
    "_session_token_0",
    "_session_token_1",
    "_session_token",
    "_session_token_fallback",
)


class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self.load()

    def load(self):
        if CONFIG_FILE.exists():
            try:
                loaded = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
                self._data = {**DEFAULT_SETTINGS, **loaded}
            except Exception:
                self._data = dict(DEFAULT_SETTINGS)
        else:
            self._data = dict(DEFAULT_SETTINGS)
        self._migrate_cookie_config_to_keyring()

    def save(self):
        try:
            CONFIG_FILE.write_text(
                json.dumps(self._data, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
        except Exception as e:
            print(f"[Config] Save failed: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any):
        self._data[key] = value
        self.save()

    def supports_autostart(self) -> bool:
        return IS_WINDOWS

    def _get_secret(self) -> str:
        if not KEYRING_AVAILABLE:
            return ""
        try:
            return keyring.get_password(KEYRING_SERVICE, KEYRING_USER) or ""
        except Exception as e:
            print(f"[Config] Keyring read failed: {e}")
            return ""

    def _set_secret(self, value: str) -> bool:
        if not KEYRING_AVAILABLE:
            return False
        try:
            keyring.set_password(KEYRING_SERVICE, KEYRING_USER, value)
            return True
        except Exception as e:
            print(f"[Config] Keyring write failed: {e}")
            return False

    def _delete_secret(self):
        if not KEYRING_AVAILABLE:
            return
        try:
            keyring.delete_password(KEYRING_SERVICE, KEYRING_USER)
        except Exception:
            pass

    def _legacy_cookie_header_from_config(self) -> str:
        raw = self._data.get("_raw_cookies", "").strip()
        if raw:
            return raw

        cookies = {}
        t0 = self._data.get("_session_token_0", "")
        t1 = self._data.get("_session_token_1", "")
        if t0 and t1:
            cookies["__Secure-next-auth.session-token.0"] = t0
            cookies["__Secure-next-auth.session-token.1"] = t1
        elif t0:
            cookies["__Secure-next-auth.session-token.0"] = t0
        else:
            single = (self._data.get("_session_token")
                      or self._data.get("_session_token_fallback")
                      or "")
            if single:
                cookies["__Secure-next-auth.session-token"] = single

        if not cookies:
            return ""
        return "; ".join(f"{k}={v}" for k, v in cookies.items())

    def _clear_cookie_config_fields(self):
        changed = False
        for key in COOKIE_CONFIG_KEYS:
            if key in self._data:
                self._data.pop(key, None)
                changed = True
        if changed:
            self.save()

    def _migrate_cookie_config_to_keyring(self):
        existing = self._get_secret()
        legacy = self._legacy_cookie_header_from_config()
        if existing:
            self._clear_cookie_config_fields()
            return
        if legacy and self._set_secret(legacy):
            self._clear_cookie_config_fields()
            print("[Config] Migrated cookies from settings.json to keyring")

    # ── Raw Cookie Header ────────────────────────────────────────────────────
    # User pastes the entire "Cookie:" header value from browser DevTools.
    # This captures ALL cookies (session tokens + cf_clearance + etc.)

    def set_raw_cookies(self, raw_cookie_str: str):
        """Save the full Cookie header string from the browser."""
        raw_cookie_str = raw_cookie_str.strip()
        if self._set_secret(raw_cookie_str):
            self._clear_cookie_config_fields()
        else:
            self._data["_raw_cookies"] = raw_cookie_str
            self.save()
        print(f"[Config] Saved raw cookie string ({len(raw_cookie_str)} chars)")

    def get_raw_cookies(self) -> str:
        """Get the stored raw cookie string."""
        secret = self._get_secret()
        if secret:
            return secret
        return self._legacy_cookie_header_from_config()

    def get_session_cookies(self) -> dict:
        """
        Parse the raw cookie header string into a dict for requests.
        Handles both raw cookie header format and legacy split token format.
        """
        raw = self.get_raw_cookies()
        if raw:
            return self._parse_cookie_header(raw)

        # Legacy fallback: try old split token fields
        cookies = {}
        t0 = self._data.get("_session_token_0", "")
        t1 = self._data.get("_session_token_1", "")
        if t0 and t1:
            cookies["__Secure-next-auth.session-token.0"] = t0
            cookies["__Secure-next-auth.session-token.1"] = t1
        elif t0:
            cookies["__Secure-next-auth.session-token.0"] = t0
        else:
            single = (self._data.get("_session_token")
                      or self._data.get("_session_token_fallback")
                      or "")
            if single:
                cookies["__Secure-next-auth.session-token"] = single
        return cookies

    def _parse_cookie_header(self, raw: str) -> dict:
        """Parse a raw Cookie header value into a dict.
        Example input: 'name1=val1; name2=val2; name3=val3'
        """
        cookies = {}
        for part in raw.split(";"):
            part = part.strip()
            if not part:
                continue
            if "=" in part:
                name, value = part.split("=", 1)
                cookies[name.strip()] = value.strip()
        return cookies

    def has_session_token(self) -> bool:
        """Check if we have any valid cookies stored."""
        raw = self.get_raw_cookies()
        if raw and len(raw) > 20:
            # Check if it contains a session token
            cookies = self._parse_cookie_header(raw)
            has = any(
                "session-token" in k.lower()
                for k in cookies
            )
            print(f"[Config] has_session_token (raw cookies)={has}, cookie_count={len(cookies)}")
            return has

        # Legacy fallback
        t = (self._data.get("_session_token_0")
             or self._data.get("_session_token")
             or self._data.get("_session_token_fallback")
             or "")
        result = bool(t and len(t) > 20)
        print(f"[Config] has_session_token (legacy)={result}")
        return result

    # Keep legacy methods for backward compat
    def get_session_token(self) -> Optional[str]:
        """Returns token.0 or legacy token. Used for has_session_token check."""
        raw = self.get_raw_cookies()
        if raw:
            cookies = self._parse_cookie_header(raw)
            for k, v in cookies.items():
                if "session-token" in k.lower():
                    return v
        return (self._data.get("_session_token_0")
                or self._data.get("_session_token")
                or self._data.get("_session_token_fallback")
                or "")

    def set_session_token(self, token0: str, token1: str = ""):
        """Legacy: Save split cookie parts."""
        cookies = {"__Secure-next-auth.session-token.0": token0.strip()}
        if token1.strip():
            cookies["__Secure-next-auth.session-token.1"] = token1.strip()
        raw = "; ".join(f"{k}={v}" for k, v in cookies.items())
        self.set_raw_cookies(raw)

    def clear_session_token(self):
        self._delete_secret()
        self._clear_cookie_config_fields()
        print("[Config] Cleared all cookies")

    # ── Network Proxy ────────────────────────────────────────────────────────

    def set_proxy_url(self, proxy_url: str):
        self._data["proxy_url"] = proxy_url.strip()
        self.save()

    def get_proxy_url(self) -> str:
        explicit = self._data.get("proxy_url", "").strip()
        if explicit:
            return self._normalize_proxy_url(explicit)

        for env_name in ("HTTPS_PROXY", "HTTP_PROXY", "ALL_PROXY"):
            value = os.environ.get(env_name) or os.environ.get(env_name.lower())
            if value:
                return self._normalize_proxy_url(value)

        if IS_WINDOWS and self._data.get("auto_detect_proxy", True):
            detected = self._get_windows_proxy()
            if detected:
                return detected

        return ""

    def _get_windows_proxy(self) -> str:
        if not IS_WINDOWS or winreg is None:
            return ""
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
                0,
                winreg.KEY_READ,
            )
            enabled, _ = winreg.QueryValueEx(key, "ProxyEnable")
            if not enabled:
                winreg.CloseKey(key)
                return ""
            proxy_server, _ = winreg.QueryValueEx(key, "ProxyServer")
            winreg.CloseKey(key)
            return self._parse_windows_proxy_server(str(proxy_server))
        except Exception as e:
            print(f"[Config] Proxy auto-detect failed: {e}")
            return ""

    def _parse_windows_proxy_server(self, proxy_server: str) -> str:
        proxy_server = proxy_server.strip()
        if not proxy_server:
            return ""

        if ";" not in proxy_server and "=" not in proxy_server:
            return self._normalize_proxy_url(proxy_server)

        entries = {}
        for part in proxy_server.split(";"):
            if "=" not in part:
                continue
            scheme, value = part.split("=", 1)
            entries[scheme.strip().lower()] = value.strip()

        for scheme in ("https", "http", "socks"):
            if entries.get(scheme):
                return self._normalize_proxy_url(entries[scheme], scheme)
        return ""

    def _normalize_proxy_url(self, proxy_url: str, default_scheme: str = "http") -> str:
        proxy_url = proxy_url.strip()
        if not proxy_url:
            return ""
        lower = proxy_url.lower()
        if lower.startswith(("http://", "https://", "socks4://", "socks5://")):
            return proxy_url
        if default_scheme == "socks":
            return f"socks5://{proxy_url}"
        return f"http://{proxy_url}"

    # ── Autostart ─────────────────────────────────────────────────────────────

    def set_autostart(self, enabled: bool):
        if not IS_WINDOWS or winreg is None:
            self.set("auto_start", False)
            print("[Config] Autostart is only supported on Windows")
            return
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, AUTOSTART_KEY,
                0, winreg.KEY_SET_VALUE
            )
            if enabled:
                if getattr(sys, "frozen", False):
                    command = f'"{os.path.abspath(sys.executable)}"'
                else:
                    python = os.path.abspath(sys.executable)
                    script = os.path.abspath(sys.argv[0])
                    command = f'"{python}" "{script}"'
                winreg.SetValueEx(key, AUTOSTART_NAME, 0, winreg.REG_SZ, command)
            else:
                try:
                    winreg.DeleteValue(key, AUTOSTART_NAME)
                except FileNotFoundError:
                    pass
            winreg.CloseKey(key)
            self.set("auto_start", enabled)
        except Exception as e:
            print(f"[Config] Autostart error: {e}")

    def get_autostart(self) -> bool:
        if not IS_WINDOWS or winreg is None:
            return False
        try:
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, AUTOSTART_KEY, 0, winreg.KEY_READ
            )
            winreg.QueryValueEx(key, AUTOSTART_NAME)
            winreg.CloseKey(key)
            return True
        except FileNotFoundError:
            return False
        except Exception:
            return self._data.get("auto_start", False)
