"""
Daily Port Broadcast — 港口每日广播系统
Pipeline: fetch → filter → dedup → weather → organize → format → push
"""
import os
import sys
import traceback
from datetime import datetime

from src.fetch import fetch_news
from src.filter import filter_news
from src.deduplicate import deduplicate
from src.weather import load_ports, fetch_all_weather
from src.organize import organize_news
from src.format import format_report
from src.push import push_report
from src.scrape_web import scrape_all


def main():
    print("=" * 60)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"Port Broadcast {now_str}")
    print("=" * 60)

    # Step 1: Load port config
    print()
    print("Step 1: Loading ports...")
    ports = load_ports()
    print(f"  Loaded {len(ports)} ports")

    # Step 2: Scrape port authority sites
    print()
    print("Step 2: Scraping port news sites...")
    try:
        scraped = scrape_all()
        print(f"  Scraped {len(scraped)} items from web")
    except Exception as e:
        print(f"  Scraping failed: {e}")
        scraped = []

    # Step 9: Fetch news from RSS
    print()
    print("Step 9: Fetching RSS news...")
    try:
        news = fetch_news()
        print(f"  Fetched {len(news)} items")
    except Exception as e:
        print(f"  FAILED: {e}")
        news = []

    # Step 9: Filter by keywords
    print()
    print("Step 9: Keyword filtering...")
    filtered = filter_news(all_raw_news)
    dropped = len(news) - len(filtered)
    dropped = len(all_raw_news) - len(filtered)
    print(f"  After filter: {len(filtered)} (dropped {dropped})")

    # Step 9: Deduplicate
    print()
    print("Step 9: Dedup...")
    unique = deduplicate(filtered)
    dups = len(filtered) - len(unique)
    print(f"  After dedup: {len(unique)} (removed {dups} duplicates)")

    # Step 9: Fetch weather
    print()
    print("Step 9: Fetching weather...")
    try:
        weather_data = fetch_all_weather(ports)
    except Exception as e:
        print(f"  Weather error: {e}")
        weather_data = {}

    # Step 9: Organize with Gemini
    print()
    print("Step 9: Gemini classification...")
    try:
        organized = organize_news(unique, ports, weather_data)
        reports = organized.get("closures", []) if isinstance(organized, dict) else []
        closures = len(organized.get("closures", [])) if isinstance(organized, dict) else 0
        suspensions = len(organized.get("suspensions", [])) if isinstance(organized, dict) else 0
        print(f"  Closures: {closures}, Suspensions: {suspensions}")
    except Exception as e:
        print(f"  Gemini failed: {e}")
        traceback.print_exc()
        organized = {"reports": [], "summary": "", "alerts": []}
        reports = []

    # Step 9: Format markdown report
    print()
    print("Step 9: Generating report...")
    try:
        report_md = format_report(organized, None, weather_data, ports)
        date_str = datetime.now().strftime("%Y-%m-%d")
        os.makedirs("reports", exist_ok=True)
        with open(f"reports/{date_str}.md", "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"  Report saved: reports/{date_str}.md ({len(report_md)} chars)")
    except Exception as e:
        print(f"  Format failed: {e}")
        report_md = ""

    # Step 9: Send email report
    print()
    print("Step 9: Sending email...")
    try:
        title = f"Port Report {datetime.now().strftime('%Y-%m-%d')}"
        push_report(title, report_md)
    except Exception as e:
        print(f"  Email failed: {e}")

    # Summary
    print()
    print("=" * 60)
    print("Done.")
    print(f"  Raw: {len(all_raw_news)} -> filtered: {len(filtered)} -> deduped: {len(unique)}")
    print(f"  Weather: {len(weather_data)} ports")
    total_reported = (
        len(organized.get("closures", [])) +
        len(organized.get("suspensions", [])) +
        len(organized.get("disrupted_ports", [])) +
        len(organized.get("normal_ports", [])) +
        len(organized.get("no_data_ports", []))
    ) if isinstance(organized, dict) else 0
    print(f"  Ports reported: {total_reported} (closures: {closures}, suspensions: {suspensions})")
    print("=" * 60)


if __name__ == "__main__":
    main()
