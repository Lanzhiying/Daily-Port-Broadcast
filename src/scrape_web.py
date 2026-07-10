"""
Scrape port-related news from Chinese maritime websites.
Uses regex-based extraction (no BeautifulSoup dep).
"""
import json
import re
import urllib.request
import ssl


def load_sites(config_path="config/port_sites.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["sources"]


def fetch_html(url, encoding="utf-8"):
    """Fetch a URL and return decoded text."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    })
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            raw = resp.read()
            # Try specified encoding, fall back to detected
            for enc in [encoding, "utf-8", "gbk", "gb2312", "latin-1"]:
                try:
                    return raw.decode(enc)
                except (UnicodeDecodeError, LookupError):
                    continue
            return raw.decode("utf-8", errors="replace")
    except Exception as e:
        print(f"    {url[:60]}: {e}")
        return ""


def extract_links(html):
    """Extract <a href> links with text from HTML."""
    results = []
    # Find all <a> tags
    pattern = re.compile(
        r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>\s*(.*?)\s*</a>',
        re.IGNORECASE | re.DOTALL
    )
    for m in pattern.finditer(html):
        href = m.group(1)
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if text and len(text) > 5 and len(text) < 300:
            # Make relative URLs absolute
            results.append({"title": text, "href": href})
    return results


def filter_port_news(links, keywords):
    """Filter links whose title contains any of the keywords."""
    results = []
    for link in links:
        title_lower = link["title"].lower()
        for kw in keywords:
            if kw.lower() in title_lower:
                # Clean title
                clean_title = re.sub(r'\s+', ' ', link["title"]).strip()
                results.append({
                    "title": clean_title,
                    "link": link["href"],
                    "summary": ""
                })
                break
    return results


def scrape_all():
    """Scrape all configured sites, return news items."""
    sites = load_sites()
    all_news = []

    for site in sites:
        name = site["name"]
        url = site["url"]
        encoding = site.get("encoding", "utf-8")
        keywords = site.get("filter_keywords", [])

        print(f"  Scraping {name}...")
        html = fetch_html(url, encoding)

        if not html:
            continue

        links = extract_links(html)
        print(f"    Extracted {len(links)} links")

        filtered = filter_port_news(links, keywords)
        print(f"    Matched {len(filtered)} port-related items")

        for item in filtered:
            item["source"] = name

        all_news.extend(filtered)

    # Deduplicate by title
    seen = set()
    unique = []
    for item in all_news:
        key = item["title"].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    print(f"  Total scraped: {len(unique)} unique items")
    return unique


if __name__ == "__main__":
    items = scrape_all()
    for i, item in enumerate(items[:10]):
        print(f"  [{item['source']}] {item['title'][:80]}")
