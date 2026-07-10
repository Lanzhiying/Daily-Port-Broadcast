"""
Daily Port Broadcast — 港口每日广播系统
Pipeline: fetch → filter → dedup → weather → organize → format → push
"""
import sys
import traceback
from datetime import datetime

from src.fetch import fetch_news
from src.filter import filter_news
from src.deduplicate import deduplicate
from src.weather import load_ports, fetch_all_weather
from src.organize import organize_news
from src.format import format_report
from src.push import push_to_wechat


def main():
    print("=" * 60)
    print(f"🌊 Daily Port Broadcast — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    # Step 1: Load port config
    print("
📌 Step 1: 加载港口配置...")
    ports = load_ports()
    print(f"   已加载 {len(ports)} 个港口")

    # Step 2: Fetch news from RSS
    print("
📡 Step 2: 抓取 RSS 新闻...")
    try:
        news = fetch_news()
        print(f"   抓取到 {len(news)} 条新闻")
    except Exception as e:
        print(f"   ❌ 抓取失败: {e}")
        news = []

    # Step 3: Filter by keywords
    print("
🔍 Step 3: 关键词过滤...")
    filtered = filter_news(news)
    print(f"   过滤后: {len(filtered)} 条 (过滤掉 {len(news)-len(filtered)} 条)")

    # Step 4: Deduplicate
    print("
🧹 Step 4: 去重...")
    unique = deduplicate(filtered)
    print(f"   去重后: {len(unique)} 条 (去除 {len(filtered)-len(unique)} 条重复)")

    # Step 5: Fetch weather
    print("
🌤️  Step 5: 获取港口天气...")
    try:
        weather_data = fetch_all_weather(ports)
    except Exception as e:
        print(f"   ⚠️ 天气获取异常: {e}")
        weather_data = {}

    # Step 6: Organize with Gemini
    print("
🤖 Step 6: Gemini 分类分析...")
    try:
        organized = organize_news(unique, ports, weather_data)
        reports = organized.get("reports", [])
        no_match = organized.get("no_match_news", [])
        print(f"   分类出 {len(reports)} 条港口报告, {len(no_match)} 条未匹配新闻")
    except Exception as e:
        print(f"   ❌ Gemini 分析失败: {e}")
        traceback.print_exc()
        reports = []
        no_match = []

    # Step 7: Format markdown report
    print("
📝 Step 7: 生成 Markdown 简报...")
    try:
        report_md = format_report(reports, no_match, weather_data, ports)
        # Save to file for reference
        date_str = datetime.now().strftime("%Y-%m-%d")
        os.makedirs("reports", exist_ok=True)
        with open(f"reports/{date_str}.md", "w", encoding="utf-8") as f:
            f.write(report_md)
        print(f"   报告已保存至 reports/{date_str}.md")
        print(f"   报告长度: {len(report_md)} 字符")
    except Exception as e:
        print(f"   ❌ 格式化失败: {e}")
        report_md = ""

    # Step 8: Push to WeChat
    print("
📲 Step 8: 推送到微信...")
    try:
        title = f"🌊 港口日报 {datetime.now().strftime('%Y-%m-%d')}"
        result = push_to_wechat(title, report_md)
    except Exception as e:
        print(f"   ❌ 推送失败: {e}")
        # Don't fail the whole pipeline on push failure
        result = {"error": str(e)}

    # Summary
    print("
" + "=" * 60)
    print("✅ Daily Port Broadcast 完成")
    print(f"   新闻: {len(news)} → 过滤: {len(filtered)} → 去重: {len(unique)}")
    print(f"   天气: {len(weather_data)} 港口")
    print(f"   报告: {len(reports)} 条 / 未匹配: {len(no_match)} 条")
    print("=" * 60)


if __name__ == "__main__":
    main()
