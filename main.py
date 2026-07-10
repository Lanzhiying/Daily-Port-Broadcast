import feedparser

# MarineLink 航运新闻 RSS
RSS_URL = "https://www.marinelink.com/rss/news"

print("正在获取新闻...")

feed = feedparser.parse(RSS_URL)

print(f"共获取到 {len(feed.entries)} 条新闻\n")

# 只显示最新 5 条
for i, item in enumerate(feed.entries[:5], start=1):
    print(f"{i}. {item.title}")
