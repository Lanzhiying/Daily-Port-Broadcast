from src.fetch import fetch_news

news = fetch_news()

print()

print(f"总共抓到 {len(news)} 条新闻")
