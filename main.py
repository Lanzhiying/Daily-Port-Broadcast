import feedparser

# 读取 feeds.txt
with open("feeds.txt", "r", encoding="utf-8") as f:
    feeds = [line.strip() for line in f if line.strip()]

print(f"共读取到 {len(feeds)} 个 RSS\n")

# 遍历所有 RSS
for rss in feeds:

    print("=" * 60)
    print(rss)

    feed = feedparser.parse(rss)

    print(f"共 {len(feed.entries)} 条新闻")

    # 只显示前3条
    for news in feed.entries[:3]:
        print("-", news.title)

    print()
