import feedparser


def fetch_news():
    news_list = []

    with open("feeds.txt", "r", encoding="utf-8") as f:
        feeds = [line.strip() for line in f if line.strip() and not line.strip().startswith("#")]

    print(f"读取到 {len(feeds)} 个 RSS")

    for rss in feeds:
        try:
            feed = feedparser.parse(rss)
            count = len(feed.entries)
            print(f"  {rss[:60]}... -> {count} 条")

            for item in feed.entries:
                news_list.append(
                    {
                        "title": item.title,
                        "link": item.link,
                        "summary": item.get("summary", "")
                    }
                )
        except Exception as e:
            print(f"  {rss[:60]}... -> ❌ {e}")

    return news_list
