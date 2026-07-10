"""
Use Gemini 1.5 Flash to analyze port status from news + weather.
Reports on EVERY monitored port, not just those with news.
"""
import json
import os
import time
import google.generativeai as genai


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["ports"]


def build_port_list(ports):
    lines = ["| Country | Port | Code |", "|---|---|---|"]
    for p in ports:
        lines.append(f"| {p['country']} | {p['port']} | {p['code']} |")
    return "\n".join(lines)


PROMPT = """You are a port operations analyst. Report the current status of EVERY port listed below.

## Monitored Ports (report on ALL of them)
{port_list}

## Available News
{news_text}

## Current Weather
{weather_text}

## Task
For EVERY port in the list above, determine its status and return JSON. If there is relevant news for a port, use it. If not, infer status from weather (e.g. storm = closure risk). If neither news nor weather data is available, mark status as "no_data" with confidence "low".

Return ONLY valid JSON:

{{
  "reports": [
    {{
      "country": "国家",
      "port": "港口名",
      "port_code": "CODE",
      "status": "normal/congested/closed/disrupted/no_data",
      "congestion_detail": "具体拥堵情况（无则写'无明显拥堵报告'）",
      "headline": "一句话标题（如：上海港正常运营，天气良好）",
      "closure_risk": "none/low/medium/high",
      "key_events": ["事件1", "事件2"],
      "weather_note": "天气对港口的影响（无则写'天气无明显影响'）",
      "confidence": "high/medium/low"
    }}
  ],
  "summary": "全局一句话摘要",
  "alerts": ["需要关注的预警"]
}}

## Status definitions
- normal: no disruption reported, weather fine
- congested: delays, queues, berth waiting reported
- closed: port shutdown, force majeure, storm closure
- disrupted: partial closure, labor issues, reduced ops
- no_data: no information available

## Rules
1. Report on EVERY port (18 ports)
2. Use any relevant news + weather to determine status
3. Be conservative — "normal" unless evidence suggests otherwise
4. Weather: high waves (>3m) or gale winds suggest disruption risk
5. Return valid JSON only, no markdown or explanation
"""


def organize_news(news_list, ports, weather_data=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    port_list = build_port_list(ports)

    # News text (limit to 20 items)
    items = []
    for i, n in enumerate(news_list[:20]):
        items.append(f"[{i+1}] {n['title']} | {n.get('summary','')[:150]}")
    news_text = "\n".join(items) if items else "(no news today)"

    # Weather text
    w_lines = []
    for code, wd in (weather_data or {}).items():
        s = wd.get("summary", {})
        if s and not wd.get("error"):
            w_lines.append(f"- {wd['country']}/{wd['port']}({code}): wave={s.get('wave','?')} wind={s.get('wind','?')} {s.get('trend','?')}")
    weather_text = "\n".join(w_lines) if w_lines else "(weather unavailable)"

    prompt = PROMPT.format(
        port_list=port_list,
        news_text=news_text,
        weather_text=weather_text,
    )

    for attempt in range(3):
        try:
            response = model.generate_content(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": 8192},
            )
            text = response.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
            return json.loads(text.strip())

        except json.JSONDecodeError as e:
            print(f"  JSON parse attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            if "429" in str(e):
                print(f"  Rate limited, waiting 60s...")
                time.sleep(60)
                continue
            print(f"  Gemini error: {e}")
            return {"reports": [], "alerts": [], "error": str(e)}

    return {"reports": [], "alerts": [], "error": "JSON parse failed"}
