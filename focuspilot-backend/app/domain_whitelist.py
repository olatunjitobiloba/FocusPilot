import os
import re


DEFAULT_WHITELIST = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "chrome.google.com",
    "newtab",
    "devtools",
}


def _normalize_domain(domain: str) -> str:
    return (domain or "").strip().lower().replace("www.", "")


def _looks_like_extension_id(domain: str) -> bool:
    # Chrome extension ids are typically 32 lowercase chars.
    return bool(re.fullmatch(r"[a-z]{32}", domain))


def get_whitelist_domains() -> set[str]:
    configured = os.getenv("FOCUSPILOT_DOMAIN_WHITELIST", "")
    configured_set = {
        _normalize_domain(item)
        for item in configured.split(",")
        if item and item.strip()
    }
    return DEFAULT_WHITELIST | configured_set


def is_whitelisted_domain(domain: str) -> bool:
    normalized = _normalize_domain(domain)
    if not normalized:
        return True

    if normalized.startswith("chrome-extension://"):
        return True

    if _looks_like_extension_id(normalized):
        return True

    whitelist = get_whitelist_domains()

    if normalized in whitelist:
        return True

    # Support parent-domain matches via env config, e.g. "mycompany.com"
    for entry in whitelist:
        if normalized.endswith(f".{entry}"):
            return True

    return False


def filter_activities_by_domain(activities: list[dict]) -> list[dict]:
    return [a for a in activities if not is_whitelisted_domain(a.get("domain", ""))]
