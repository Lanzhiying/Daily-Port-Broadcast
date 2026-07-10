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

    # Step 2: Fetch news from RSS
    print()
    print("Step 2: Fetching RSS news...")
    try:
        news = fetch_news()
        print(f"  Fetched {len(news)} items")
    except Exception as e:
        print(f"  FAILED: {e}")
        news = []

    # Step 3: Filter by keywords
    print()
    print("Step 3: Keyword filtering...")
    filtered = filter_news(news)
    dropped = len(news) - len(filtered)
    print(f"  After filter: {len(filtered)} (dropped {dropped})")

    # Step 4: Deduplicate
    print()
    print("Step 4: Dedup...")
    unique = deduplicate(filtered)
    dups = len(filtered) - len(unique)
    print(f"  After dedup: {len(unique)} (removed {dups} duplicates)")

    # Step 5: Fetch weather
    print()
    print("Step 5: Fetching weather...")
    try:
        weather_data = fetch_all_weather(ports)
    except Exception as e:
        print(f"  Weather error: {e}")
        weather_data = {}

    # Step 6: Organize with Gemini
    print()
    print("Step 6: Gemini classification...")
    try:
        organized = organize_news(unique, ports, weather_data)
        reports = organized.get("reports", [])
        no_match = organized.get("no_match_news", [])
        print(f"  Reports: {len(reports)}, unmatched: {len(no_match)}")
    except Exception as e:
        print(f"  Gemini failed: {e}")
        traceback.print_exc()
        reports = []
        no_match = []

    # Step 7: Format markdown report
    print()
    print("Step 7: Generating report...")
    try:
        report_md = format_report(reports, no_match, weather_data, ports)
        date_str = datetime.now().strftime("%Y-%m-%d")
        os.makedirs("reports", exist_ok=True)
        with open(f"reports/{date_str}.md", "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"  Report saved: reports/{date_str}.md ({len(report_md)} chars)")
    except Exception as e:
        print(f"  Format failed: {e}")
        report_md = ""

    # Step 8: Send email report
    print()
    print("Step 8: Sending email...")
    try:
        title = f"Port Report {datetime.now().strftime('%Y-%m-%d')}"
        push_report(title, report_md)
    except Exception as e:
        print(f"  Email failed: {e}")

    # Summary
    print()
    print("=" * 60)
    print("Done.")
    print(f"  News: {len(news)} -> filtered: {len(filtered)} -> deduped: {len(unique)}")
    print(f"  Weather: {len(weather_data)} ports")
    print(f"  Report: {len(reports)} items, {len(no_match)} unmatched")
    print("=" * 60)


if __name__ == "__main__":
    main()
