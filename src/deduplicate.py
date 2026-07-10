def deduplicate(news_list):
    seen = set()
    result = []

    for news in news_list:

        # 用标题去重
        title = news["title"].strip().lower()

        if title in seen:
            continue

        seen.add(title)
        result.append(news)

    return result
