import ipaddress
import socket
from urllib.parse import urlparse
import httpx


class SSRFValidationError(ValueError):
    """Raised when a URL points to a forbidden IP address or scheme."""
    pass


class PoliteFetchError(Exception):
    """Raised when fetching fails."""
    pass


def is_safe_ip(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_multicast or ip.is_unspecified:
            return False
        if ip.is_reserved and not getattr(ip, "is_global", False):
            return False
        return True
    except ValueError:
        return False


def validate_url_safety(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ("http", "https"):
        raise SSRFValidationError(f"Invalid URL scheme '{parsed.scheme}'. Only http and https allowed.")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFValidationError("URL missing hostname.")

    # Reject localhost directly
    if hostname.lower() in ("localhost", "127.0.0.1", "::1"):
        raise SSRFValidationError(f"Forbidden host: {hostname}")

    # Resolve all IPs
    try:
        addr_info = socket.getaddrinfo(hostname, None)
    except socket.gaierror as e:
        raise PoliteFetchError(f"DNS resolution failed for {hostname}: {e}")

    for item in addr_info:
        ip_str = item[4][0]
        if not is_safe_ip(ip_str):
            raise SSRFValidationError(f"Resolved IP {ip_str} for host {hostname} is non-public/private.")


class SafeFetcher:
    def __init__(
        self,
        user_agent: str = "UpthrustOutboundAgent/0.1 (+https://upthrust.com/bot)",
        timeout_s: float = 10.0,
        max_bytes: int = 1_500_000,
        max_redirects: int = 3,
    ):
        self.user_agent = user_agent
        self.timeout_s = timeout_s
        self.max_bytes = max_bytes
        self.max_redirects = max_redirects

    def fetch(self, url: str) -> tuple[int, str, str]:
        """
        SSRF-safe polite fetch.
        Returns (status_code, content_text, final_url).
        Re-validates each redirect target against SSRF.
        """
        current_url = url
        redirects = 0

        while redirects <= self.max_redirects:
            validate_url_safety(current_url)

            headers = {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
            }

            try:
                with httpx.Client(
                    follow_redirects=False,
                    timeout=self.timeout_s,
                    verify=True,
                ) as client:
                    resp = client.get(current_url, headers=headers)
            except httpx.RequestError as e:
                raise PoliteFetchError(f"HTTP request error fetching {current_url}: {e}")

            if resp.status_code in (301, 302, 303, 307, 308):
                location = resp.headers.get("Location")
                if not location:
                    break
                # Handle relative redirect
                parsed_loc = urlparse(location)
                if not parsed_loc.scheme:
                    current_url = str(httpx.URL(current_url).join(location))
                else:
                    current_url = location
                redirects += 1
                continue

            # Check size limit
            content = resp.content
            if len(content) > self.max_bytes:
                content = content[: self.max_bytes]

            text = resp.text
            return resp.status_code, text, current_url

        raise PoliteFetchError(f"Exceeded max redirects ({self.max_redirects}) for {url}")


# Global helper
_default_fetcher = SafeFetcher()

def safe_fetch(url: str) -> tuple[int, str, str]:
    return _default_fetcher.fetch(url)
