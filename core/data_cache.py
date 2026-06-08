"""
GPT Usage Widget — Data Cache (Codex version)
Persists last successful CodexData to disk for instant display on startup.
"""
import json
import time
from pathlib import Path
from typing import Optional
from core.api_client import CodexData

CACHE_FILE = Path.home() / ".gpt-widget" / "cache.json"


def save_cache(data: CodexData):
    try:
        payload = {
            "saved_at": time.time(),
            "period_label": data.period_label,
            "period_used_h": data.period_used_h,
            "period_total_h": data.period_total_h,
            "period_percent": data.period_percent,
            "weekly_label": data.weekly_label,
            "weekly_used_h": data.weekly_used_h,
            "weekly_total_h": data.weekly_total_h,
            "weekly_percent": data.weekly_percent,
            "user_name": data.user_name,
            "user_email": data.user_email,
            "plan": data.plan,
            "session_expires": data.session_expires,
            "data_source": data.data_source,
        }
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
    except Exception as e:
        print(f"[Cache] Save failed: {e}")


def load_cache() -> Optional[CodexData]:
    if not CACHE_FILE.exists():
        return None
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            p = json.load(f)
        source = str(p.get("data_source", ""))
        if (
            source.startswith("/backend-api/accounts/check")
            and float(p.get("period_percent", 0.0) or 0.0) == 0.0
            and float(p.get("weekly_percent", 0.0) or 0.0) == 0.0
            and float(p.get("period_used_h", 0.0) or 0.0) == 0.0
            and float(p.get("weekly_used_h", 0.0) or 0.0) == 0.0
        ):
            return None
        return CodexData(
            period_label=p.get("period_label", "5小时额度"),
            period_used_h=p.get("period_used_h", 0.0),
            period_total_h=p.get("period_total_h", 5.0),
            period_percent=p.get("period_percent", 0.0),
            weekly_label=p.get("weekly_label", "周额度"),
            weekly_used_h=p.get("weekly_used_h", 0.0),
            weekly_total_h=p.get("weekly_total_h", 0.0),
            weekly_percent=p.get("weekly_percent", 0.0),
            user_name=p.get("user_name", ""),
            user_email=p.get("user_email", ""),
            plan=p.get("plan", "ChatGPT Plus"),
            session_expires=p.get("session_expires", ""),
            data_source=p.get("data_source", "cache"),
        )
    except Exception as e:
        print(f"[Cache] Load failed: {e}")
        return None


def cache_age_seconds() -> float:
    if not CACHE_FILE.exists():
        return float("inf")
    try:
        with open(CACHE_FILE, "r", encoding="utf-8") as f:
            p = json.load(f)
        return time.time() - p.get("saved_at", 0)
    except Exception:
        return float("inf")
