"""
Daily Port Broadcast
Pipeline: scrape → fetch RSS → merge → filter → dedup → weather → Gemini → format → email
"""
import os, sys, traceback
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
    print(f"Port Broadcast {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # 1. Load ports
    print()
    print("1. Loading ports...")
    ports = load_ports()
    print(f"   {len(ports)} ports loaded")

    # 2. Scrape web
    print()
    print("2. Scraping web...")
    try:
        scraped = scrape_all()
        print(f"   {len(scraped)} items scraped")
    except Exception as e:
        print(f"   Failed: {e}")
        scraped = []

    # 3. Fetch RSS
    print()
    print("3. Fetching RSS...")
    try:
        rss_news = fetch_news()
        print(f"   {len(rss_news)} items")
    except Exception as e:
        print(f"   Failed: {e}")
        rss_news = []

    # 4. Merge
    all_raw = scraped + rss_news
    print()
    print(f"4. Merged: {len(all_raw)} total (scraped:{len(scraped)} + RSS:{len(rss_news)})")

    # 5. Filter
    print()
    print("5. Filtering...")
    filtered = filter_news(all_raw)
    print(f"   {len(filtered)} passed ({len(all_raw) - len(filtered)} dropped)")

    # 6. Dedup
    print()
    print("6. Deduplicating...")
    unique = deduplicate(filtered)
    print(f"   {len(unique)} unique ({len(filtered) - len(unique)} removed)")

    # 7. Weather
    print()
    print("7. Weather...")
    try:
        weather_data = fetch_all_weather(ports)
    except Exception as e:
        print(f"   Failed: {e}")
        weather_data = {}

    # 8. Gemini
    print()
    print("8. Gemini analysis...")
    try:
        organized = organize_news(unique, ports, weather_data)
        if isinstance(organized, dict):
            c = len(organized.get("closures", []))
            s = len(organized.get("suspensions", []))
            print(f"   Closures:{c} Suspensions:{s}")
        else:
            organized = {"closures":[],"suspensions":[],"disrupted_ports":[],"normal_ports":[],"no_data_ports":[],"alerts":[]}
            c = s = 0
    except Exception as e:
        print(f"   Failed: {e}")
        traceback.print_exc()
        organized = {"closures":[],"suspensions":[],"disrupted_ports":[],"normal_ports":[],"no_data_ports":[],"alerts":[]}
        c = s = 0

    # 9. Format
    print()
    print("9. Generating report...")
    try:
        report_md = format_report(organized, None, weather_data, ports)
        date_str = datetime.now().strftime("%Y-%m-%d")
        os.makedirs("reports", exist_ok=True)
        with open(f"reports/{date_str}.md", "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"   Saved: reports/{date_str}.md ({len(report_md)} chars)")
    except Exception as e:
        print(f"   Failed: {e}")
        report_md = ""

    # 10. Email
    print()
    print("10. Sending email...")
    try:
        title = f"Port Report {datetime.now().strftime('%Y-%m-%d')}"
        push_report(title, report_md)
    except Exception as e:
        print(f"   Failed: {e}")

    # Summary
    total = 0
    if isinstance(organized, dict):
        total = (len(organized.get("closures",[])) + len(organized.get("suspensions",[])) +
                 len(organized.get("disrupted_ports",[])) + len(organized.get("normal_ports",[])) +
                 len(organized.get("no_data_ports",[])))

    print()
    print("=" * 60)
    print("Done.")
    print(f"   Raw:{len(all_raw)} -> Filtered:{len(filtered)} -> Unique:{len(unique)}")
    print(f"   Weather: {len(weather_data)} ports")
    print(f"   Report: {total} ports (closures:{c} suspensions:{s})")
    print("=" * 60)


if __name__ == "__main__":
    main()
