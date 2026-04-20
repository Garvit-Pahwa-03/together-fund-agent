import requests
from urllib.parse import urlparse


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


def url_is_reachable(url: str, timeout: int = 6):
    if not is_valid_url(url):
        return False, f"Malformed URL: {url}"

    blocked_domains = [
        "linkedin.com", "twitter.com", "x.com",
        "facebook.com", "instagram.com", "ndtv.com",
        "bloomberg.com", "wsj.com"
    ]
    domain = urlparse(url).netloc.lower()
    if any(b in domain for b in blocked_domains):
        return False, f"Blocked domain: {domain}"

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.head(
            url, timeout=timeout,
            headers=headers,
            allow_redirects=True
        )
        if response.status_code < 400:
            return True, "OK"
        return False, f"HTTP {response.status_code}"
    except requests.exceptions.Timeout:
        return False, "Timeout"
    except requests.exceptions.ConnectionError:
        return False, "Connection refused"
    except Exception as e:
        return False, str(e)


def validate_startup_list(raw_output: str) -> list:
    import re
    startups = []

    name_pattern = re.findall(
        r"(?:Name|Startup)[:\s*]+([^\n,]+)",
        raw_output, re.IGNORECASE
    )
    url_pattern = re.findall(r"https?://[^\s\n,\"\']+", raw_output)

    valid_urls = []
    seen = set()
    for url in url_pattern:
        url = url.strip(".,)")
        if url not in seen and is_valid_url(url):
            valid_urls.append(url)
            seen.add(url)

    for i, name in enumerate(name_pattern[:3]):
        url = valid_urls[i] if i < len(valid_urls) else ""
        reachable, reason = (
            url_is_reachable(url) if url else (False, "No URL found")
        )
        startups.append({
            "name": name.strip(),
            "url": url,
            "url_valid": reachable,
            "url_status": reason
        })

    return startups