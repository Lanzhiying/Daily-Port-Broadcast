"""
Scrape port news using Firecrawl (JS-rendered pages) + regex fallback.
"""
import json, re, ssl, os, urllib.request
from datetime import datetime


def load_config(config_path="config/port_sites.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ===== Firecrawl scraper =====

def scrape_firecrawl(targets):
    """Scrape JS-rendered pages via Firecrawl API."""
    api_key = os.environ.get("FIRECRAWL_API_KEY")
    if not api_key:
        print("  Firecrawl: no API key, skipping")
        return []

    try:
        from firecrawl import FirecrawlApp
        app = FirecrawlApp(api_key=api_key)
    except ImportError:
        print("  Firecrawl: firecrawl-py not installed")
        return []

    all_items = []
    for target in targets:
        name = target["name"]
        url = target["url"]
        print(f"  Firecrawl: {name}...")
        try:
            result = app.scrape_url(url, params={"formats": ["markdown"]})
            if not result or not result.get("markdown"):
                print(f"    No content")
                continue

            md = result["markdown"]
            # Extract lines that look like news/announcements
            lines = md.split("\n")
            for line in lines:
                line = line.strip()
                if len(line) > 20 and len(line) < 500:
                    # Check for port-related keywords
                    if re.search(r'port|terminal|berth|vessel|ship|cargo|container|congestion|closure|disruption|suspend|delay|notice|maritime|harbour|harbor|dock|pilot|港口|码头|船舶|停航|封港|拥堵|关闭|暂停|延误|通知|公告|通航|泊位|引航', line, re.I):
                        all_items.append({
                            "title": line[:200],
                            "link": url,
                            "summary": "",
                            "source": name
                        })
            print(f"    Extracted {len(all_items)} items so far")
        except Exception as e:
            print(f"    Failed: {e}")

    # Dedup by title
    seen = set()
    unique = []
    for item in all_items:
        key = item["title"][:80].lower()
        if key not in seen:
            seen.add(key)
            unique.append(item)

    print(f"  Firecrawl total: {len(unique)} unique items")
    return unique


# ===== Regex fallback scraper =====

def fetch_html(url, encoding="utf-8"):
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    })
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as resp:
            raw = resp.read()
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
    results = []
    for m in re.finditer(
        r'<a\s[^>]*href\s*=\s*["\']([^"\']+)["\'][^>]*>\s*(.*?)\s*</a>',
        html, re.I | re.S
    ):
        text = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if text and 5 < len(text) < 300:
            results.append({"title": text, "href": m.group(1)})
    return results


def filter_by_keywords(links, keywords):
    results = []
    for link in links:
        t = link["title"].lower()
        for kw in keywords:
            if kw.lower() in t:
                results.append({
                    "title": re.sub(r'\s+', ' ', link["title"]).strip(),
                    "link": link["href"],
                    "summary": "",
                    "source": "regex"
                })
                break
    return results


def scrape_regex(targets):
    all_news = []
    for site in targets:
        name = site["name"]
        print(f"  Regex: {name}...")
        html = fetch_html(site["url"], site.get("encoding", "utf-8"))
        if not html:
            continue
        links = extract_links(html)
        filtered = filter_by_keywords(links, site.get("keywords", []))
        for item in filtered:
            item["source"] = name
        all_news.extend(filtered)
        print(f"    {len(filtered)} items")

    seen = set()
    unique = []
    for item in all_news:
        k = item["title"][:80].lower()
        if k not in seen:
            seen.add(k)
            unique.append(item)
    print(f"  Regex total: {len(unique)} unique items")
    return unique


# ===== Main =====

def scrape_all():
    config = load_config()
    
    firecrawl_items = []
    regex_items = []

    # Try Firecrawl first
    fc_targets = config.get("firecrawl_targets", [])
    if fc_targets:
        firecrawl_items = scrape_firecrawl(fc_targets)

    # Regex fallback
    re_targets = config.get("regex_targets", [])
    if re_targets:
        regex_items = scrape_regex(re_targets)

    all_items = firecrawl_items + regex_items

    # Final dedup
    seen = set()
    unique = []
    for item in all_items:
        k = item["title"][:80].lower()
        if k not in seen:
            seen.add(k)
            unique.append(item)

    print(f"  Grand total: {len(unique)} unique items")
    return unique


if __name__ == "__main__":
    items = scrape_all()
    for i in items[:10]:
        print(f"  [{i['source']}] {i['title'][:100]}")
