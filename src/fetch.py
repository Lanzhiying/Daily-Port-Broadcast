import feedparser


def fetch_news():
    news_list = []

    # 读取 RSS 列表
    with open("feeds.txt", "r", encoding="utf-8") as f:
        feeds = [line.strip() for line in f if line.strip()]

    print(f"读取到 {len(feeds)} 个 RSS")

    for rss in feeds:

        feed = feedparser.parse(rss)

        print(f"{rss} -> {len(feed.entries)} 条")

        for item in feed.entries:

            news_list.append(
                {
                    "title": item.title,
                    "link": item.link,
                    "summary": item.get("summary", "")
                }
            )

    return news_list
