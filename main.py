from src.fetch import fetch_news
from src.filter import filter_news
from src.deduplicate import deduplicate

news = fetch_news()

print(f"\n抓取新闻：{len(news)}")

filtered = filter_news(news)

print(f"过滤后：{len(filtered)}")

unique = deduplicate(filtered)

print(f"去重后：{len(unique)}")
