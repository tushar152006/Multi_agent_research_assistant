import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {
    "localhost",
    "127.0.0.1",
    "::1",
    "0.0.0.0",
    "169.254.169.254",
    "metadata.google.internal",
    "instance-data",
}


def is_safe_ip(ip_str: str) -> bool:
    """Validate that an IP is globally routable and not private/loopback/link-local/multicast."""
    try:
        ip = ipaddress.ip_address(ip_str)
        return not (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_reserved
            or ip.is_multicast
            or ip.is_unspecified
        )
    except ValueError:
        return False


def is_safe_url(url: str, allowed_schemes: tuple[str, ...] = ("http", "https")) -> bool:
    """
    Validate target URL against SSRF threats:
    - Enforces allowed schemes (http, https)
    - Rejects cloud metadata, loopback, and local hostnames
    - Resolves all A and AAAA DNS records and verifies they are globally routable public IPs
    """
    if not url or not isinstance(url, str):
        return False

    try:
        parsed = urlparse(url.strip())
        if parsed.scheme.lower() not in allowed_schemes:
            return False

        hostname = parsed.hostname
        if not hostname:
            return False

        if hostname.lower() in BLOCKED_HOSTNAMES:
            return False

        # Attempt to resolve all IP records (IPv4 & IPv6)
        addr_info = socket.getaddrinfo(hostname, None)
        if not addr_info:
            return False

        for item in addr_info:
            ip_str = item[4][0]
            if not is_safe_ip(ip_str):
                return False

        return True
    except Exception:
        return False


def sanitize_untrusted_prompt_data(val: object) -> str:
    """Sanitize untrusted strings before inserting into LLM prompt delimiter blocks.

    Prevents prompt injection breakouts by neutralizing closing and opening tags,
    escaping control tokens, and preventing delimiter spoofing.
    """
    if val is None:
        return ""
    if isinstance(val, (list, tuple, set)):
        return ", ".join(sanitize_untrusted_prompt_data(item) for item in val)
    if isinstance(val, dict):
        return ", ".join(f"{k}: {sanitize_untrusted_prompt_data(v)}" for k, v in val.items())

    import re

    text = str(val)
    # Neutralize closing and opening delimiter variations
    text = re.sub(
        r"<\s*/?\s*untrusted_research_data\s*>",
        "[ESCAPED_UNTRUSTED_TAG]",
        text,
        flags=re.IGNORECASE,
    )
    # Neutralize common system/instruction injection cues
    text = re.sub(r"<\s*/?\s*system\s*>", "[ESCAPED_SYSTEM_TAG]", text, flags=re.IGNORECASE)
    text = re.sub(r"<\s*/?\s*developer\s*>", "[ESCAPED_DEV_TAG]", text, flags=re.IGNORECASE)
    text = re.sub(
        r"<\|im_start\|>|<\|im_end\|>|\[INST\]|\[/INST\]",
        "[ESCAPED_CONTROL_TOKEN]",
        text,
        flags=re.IGNORECASE,
    )
    return text

