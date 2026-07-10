KEYWORDS = [
    "port",
    "shipping",
    "ship",
    "vessel",
    "container",
    "cargo",
    "harbour",
    "harbor",
    "terminal",
    "logistics",
    "freight",
    "maritime",
    "canal",
    "suez",
    "panama",
    "imo",
    "dock",
    "berth",
]


def filter_news(news_list):
    result = []

    for news in news_list:

        text = (
            news["title"] + " " + news["summary"]
        ).lower()

        if any(keyword in text for keyword in KEYWORDS):
            result.append(news)

    return result
