"""
Use Gemini (free API) to:
1. Classify news by country-port
2. Generate Chinese summaries
3. Detect port closures, congestion, etc.
"""
import json
import os
import google.generativeai as genai


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["ports"]


def build_port_context(ports):
    """Build a short port reference for the LLM prompt."""
    lines = []
    for p in ports:
        lines.append(f"- {p['country']} / {p['port']} ({p['port_en']}) — 代码: {p['code']}")
    return "\n".join(lines)


PROMPT_TEMPLATE = """你是一个港口航运情报分析助手。请根据以下新闻列表，按"国家-港口"分类整理，并生成简明中文摘要。

## 监控港口
{port_context}

## 新闻列表
{news_text}

## 输出要求
请严格按以下 JSON 格式输出（不要输出其他内容）：

{{
  "reports": [
    {{
      "country": "国家名",
      "port": "港口中文名",
      "port_code": "PORT_CODE",
      "summary": "一句话中文摘要（50字以内）",
      "is_port_closure": false,
      "congestion_level": "正常/轻微拥堵/中度拥堵/严重拥堵",
      "closure_risk": "无/低/中/高",
      "confidence": "高/中/低"
    }}
  ],
  "no_match_news": [
    {{
      "title": "原标题",
      "reason": "无法匹配到监控港口的原因"
    }}
  ]
}}

## 注意事项
1. 只提取与上述监控港口直接相关的新闻
2. 如果同一条新闻涉及多个港口，每个港口单独一条记录
3. 封港判断标准：新闻中出现"closure/shutdown/suspension/关闭/暂停运营"等关键词
4. 拥堵程度根据新闻描述判断：waiting time/delay/congestion/排队/延误/拥堵
5. 封港风险预测：结合天气和新闻中提到的罢工/政策/维护等综合判断
6. 无法匹配到任何监控港口的新闻放入 no_match_news
7. 务必返回合法 JSON，不要加任何解释文字
"""


def organize_news(news_list, ports, weather_data=None):
    """Send news to Gemini for classification and summarization."""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    # Build port context
    port_context = build_port_context(ports)

    # Build news text
    news_items = []
    for i, item in enumerate(news_list):
        title = item.get("title", "")
        summary = item.get("summary", "")[:300]  # truncate long summaries
        news_items.append(f"[{i+1}] 标题: {title}\n    摘要: {summary}")
    news_text = "\n".join(news_items[:30])  # limit to 30 items per call

    # Add weather context if available
    weather_context = ""
    if weather_data:
        weather_lines = []
        for code, wd in weather_data.items():
            s = wd.get("summary", {})
            if s:
                weather_lines.append(
                    f"- {wd['country']}/{wd['port']}({code}): "
                    f"浪高={s.get('wave','?')}, 风速={s.get('wind','?')}, {s.get('trend','')}"
                )
        if weather_lines:
            weather_context = "\n## 当前天气数据\n" + "\n".join(weather_lines)

    prompt = PROMPT_TEMPLATE.format(
        port_context=port_context,
        news_text=news_text,
    )
    if weather_context:
        prompt += weather_context

    # Call Gemini
    try:
        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": 0.2,
                "max_output_tokens": 4096,
            },
        )
        text = response.text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            if text.endswith("```"):
                text = text[:-3]
        text = text.strip()

        result = json.loads(text)
        return result

    except json.JSONDecodeError as e:
        print(f"  ⚠️ Gemini returned invalid JSON: {e}")
        print(f"  Raw response: {text[:500]}")
        return {"reports": [], "no_match_news": [], "error": str(e)}
    except Exception as e:
        print(f"  ❌ Gemini API error: {e}")
        return {"reports": [], "no_match_news": [], "error": str(e)}


if __name__ == "__main__":
    # Quick test
    ports = load_ports()
    print(f"Loaded {len(ports)} ports")
    print(build_port_context(ports[:3]))
