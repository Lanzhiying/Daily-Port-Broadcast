from src.fetch import fetch_news
from src.filter import filter_news

news = fetch_news()

print(f"\n抓取新闻：{len(news)} 条")

filtered = filter_news(news)

print(f"过滤后：{len(filtered)} 条")
