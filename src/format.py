"""
Format the organized data into a Markdown daily port broadcast.
"""
from datetime import datetime, timedelta


def format_report(reports, no_match_news, weather_data, ports):
    """Generate a Markdown report from organized data."""

    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    lines = []
    lines.append(f"# 🌊 港口每日广播 — {today}")
    lines.append("")
    lines.append(f"> 📅 日期：{today} ｜ ⏰ 推送时间：北京时间 08:00")
    lines.append(f"> 📡 覆盖港口：{len(ports)} 个（中国10 + 东南亚8）")
    lines.append("")

    # ---- Section 1: Port Reports ----
    lines.append("---")
    lines.append("")
    lines.append("## 📋 港口航运情报")
    lines.append("")

    # Group by country
    by_country = {}
    for r in reports:
        country = r.get("country", "未知")
        if country not in by_country:
            by_country[country] = []
        by_country[country].append(r)

    for country, items in by_country.items():
        lines.append(f"### {country}")
        lines.append("")
        lines.append("| 港口 | 摘要 | 拥堵 | 封港 | 封港风险 | 可信度 |")
        lines.append("|------|------|------|------|----------|--------|")
        for item in items:
            port = item.get("port", "?")
            summary = item.get("summary", "—")
            congestion = item.get("congestion_level", "—")
            is_closure = "🚫 是" if item.get("is_port_closure") else "✅ 否"
            closure_risk = item.get("closure_risk", "—")
            confidence = item.get("confidence", "—")

            # Emoji for congestion
            cong_emoji = {"正常":"🟢","轻微拥堵":"🟡","中度拥堵":"🟠","严重拥堵":"🔴"}
            cong_display = f"{cong_emoji.get(congestion,'')} {congestion}"

            lines.append(
                f"| **{port}** | {summary} | {cong_display} | {is_closure} | {closure_risk} | {confidence} |"
            )
        lines.append("")

    # ---- Section 2: Weather Summary ----
    lines.append("---")
    lines.append("")
    lines.append("## 🌤️ 天气海况概览")
    lines.append("")

    if weather_data:
        lines.append("| 国家 | 港口 | 浪高 | 风速 | 趋势 |")
        lines.append("|------|------|------|------|------|")
        for code, wd in weather_data.items():
            s = wd.get("summary", {})
            if wd.get("error"):
                lines.append(f"| {wd.get('country','?')} | {wd.get('port','?')} | ❌ 获取失败 | — | — |")
            else:
                lines.append(
                    f"| {wd.get('country','?')} | {wd.get('port','?')} | "
                    f"{s.get('wave','—')} | {s.get('wind','—')} | {s.get('trend','—')} |"
                )
        lines.append("")
    else:
        lines.append("> ⚠️ 天气数据暂不可用")
        lines.append("")

    # ---- Section 3: Unmatched News ----
    if no_match_news:
        lines.append("---")
        lines.append("")
        lines.append("## 📰 其他相关新闻（未匹配到监控港口）")
        lines.append("")
        for item in no_match_news:
            title = item.get("title", "?")
            reason = item.get("reason", "")
            lines.append(f"- **{title}** — {reason}")
        lines.append("")

    # ---- Footer ----
    lines.append("---")
    lines.append("")
    lines.append(f"*由 Daily Port Broadcast 自动生成 · {today}*")
    lines.append(f"*数据来源：Google News RSS + 海事行业RSS + Open-Meteo天气*")

    return "\n".join(lines)


if __name__ == "__main__":
    # Test with sample data
    sample_reports = [
        {
            "country": "中国", "port": "上海", "port_code": "CNSHA",
            "summary": "上海港目前运营正常，无拥堵报告",
            "is_port_closure": False, "congestion_level": "正常",
            "closure_risk": "无", "confidence": "高"
        }
    ]
    md = format_report(sample_reports, [], {}, [])
    print(md)
