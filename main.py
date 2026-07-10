import feedparser

RSS_URL = "https://feeds.bbci.co.uk/news/world/rss.xml"

print("正在获取 RSS...")
print("RSS:", RSS_URL)

feed = feedparser.parse(RSS_URL)

print("状态：", feed.get("status"))
print("标题：", feed.feed.get("title"))
print("新闻数量：", len(feed.entries))

for item in feed.entries[:5]:
    print(item.title)
