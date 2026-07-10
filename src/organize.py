"""
Use Gemini 1.5 Flash to analyze port status.
Reports on every port with terminal-level detail for key ports.
"""
import json, os, time
import google.generativeai as genai


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["ports"]


PROMPT = """You are a senior port operations analyst. Report on EVERY port listed below.

## Monitored Ports (report ALL)
{port_list}

## Available News
{news_text}

## Current Weather
{weather_text}

## Key Ports — Terminal-Level Detail Required
For these ports, provide specific terminal/berth status if available from news:
- Maoming: single buoy mooring, oil terminal
- Shanghai: Yangshan deep-water, Waigaoqiao terminals
- Tianjin: container terminals, bulk cargo berths
- Kaohsiung: container terminals
- Busan: Busan New Port, North Port
- Laem Chabang: deep-sea berths

## Task
For EVERY port, return JSON with these fields per port:

{{
  "reports": [
    {{
      "country": "国家",
      "port": "港口名",
      "port_code": "CODE",
      "status": "normal/congested/closed/disrupted/no_data",
      "headline": "一句话运营状态",
      "terminal_detail": "重点港口的码头/泊位具体情况（非重点港口写 '-'）",
      "congestion_detail": "拥堵详情或 '无明显拥堵'",
      "closure_risk": "none/low/medium/high",
      "weather_impact": "天气对运营的影响分析",
      "closure_forecast": "未来24-48h是否可能因天气关闭，预估时间段（无则写 'no forecast needed'）",
      "key_events": ["事件"],
      "confidence": "high/medium/low"
    }}
  ],
  "summary": "全局摘要",
  "alerts": ["需关注的预警"]
}}

## Status definitions
- normal: no disruption, weather fine
- congested: delays, queues reported
- closed: port shutdown, storm closure
- disrupted: partial closure, labor issues
- no_data: no info available

## Weather → Operations Rules
- Waves > 2.5m: crane ops restricted, possible berth suspension
- Waves > 3.5m: likely port closure
- Wind > 30 km/h: crane ops restricted
- Wind > 50 km/h: likely port closure
- Swell > 3m: pilot boarding suspended
- If 3-day trend shows worsening, forecast closure window

## Rules
1. Report ALL {total_ports} ports
2. Key ports (Maoming/Shanghai/Tianjin/Kaohsiung/Keelung/Taichung/Busan/Incheon/Gwangyang/Laem Chabang/Bangkok): include terminal_detail
3. Always assess weather_impact and closure_forecast
4. Be conservative: "normal" unless evidence of disruption
5. Return valid JSON only
"""


def organize_news(news_list, ports, weather_data=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Port table
    lines = ["| Country | Port | Code |", "|---|---|---|"]
    for p in ports:
        lines.append(f"| {p['country']} | {p['port']} | {p['code']} |")
    port_list = "\n".join(lines)

    # News (limit 25)
    items = []
    for i, n in enumerate(news_list[:25]):
        items.append(f"[{i+1}] {n['title']} | {n.get('summary','')[:150]}")
    news_text = "\n".join(items) if items else "(no news)"

    # Weather
    w_lines = []
    for code, wd in (weather_data or {}).items():
        s = wd.get("summary", {})
        if s and not wd.get("error"):
            w_lines.append(f"- {wd['country']}/{wd['port']}({code}): {s.get('wave','?')} {s.get('wind','?')} {s.get('trend','?')}")
    weather_text = "\n".join(w_lines) if w_lines else "(unavailable)"

    prompt = PROMPT.format(
        port_list=port_list,
        news_text=news_text,
        weather_text=weather_text,
        total_ports=len(ports),
    )

    for attempt in range(3):
        try:
            resp = model.generate_content(
                prompt,
                generation_config={"temperature": 0.2, "max_output_tokens": 8192},
            )
            text = resp.text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
            return json.loads(text.strip())
        except json.JSONDecodeError as e:
            print(f"  JSON attempt {attempt+1}: {e}")
            time.sleep(2 ** attempt)
        except Exception as e:
            if "429" in str(e):
                print(f"  429, waiting 60s...")
                time.sleep(60)
                continue
            return {"reports": [], "alerts": [], "error": str(e)}

    return {"reports": [], "alerts": [], "error": "JSON failed"}
