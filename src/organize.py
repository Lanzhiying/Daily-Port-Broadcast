"""
Port status analysis with PRIMARY focus on closures and suspensions.
Multiple source cross-verification required.
"""
import json, os, time
import google.generativeai as genai


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["ports"]


PROMPT = """You are a port emergency operations analyst. Your PRIMARY mission is to detect and verify port CLOSURES and shipping SUSPENSIONS.

## Monitored Ports (report ALL)
{port_list}

## Available News Sources (cross-verify across them)
{news_text}

## Weather Data
{weather_text}

## CRITICAL RULES

### 1. Closure/Suspension Detection (HIGHEST PRIORITY)
Scan ALL news for these signals:
- Port closure, terminal shutdown, berth suspension
- Force majeure declaration
- Vessel traffic suspension, pilot service halted  
- Storm/typhoon port closure, emergency shutdown
- Strike, labor action causing stoppage
- Accident, collision, oil spill causing closure
- Government order, customs halt, border closure

### 2. Cross-Verification (MANDATORY)
- If closure detected: check if confirmed by at least 2 different sources or source types (industry RSS + Google News)
- Flag single-source reports as "unverified"
- If sources conflict: report the conflict explicitly
- Weather-only closure prediction: mark as "forecast" not "confirmed"

### 3. Closure Detail (for each closure/suspension found)
REQUIRED fields when closure detected:
- closure_type: weather | labor | accident | regulatory | other
- closure_scope: full_port | specific_terminal | specific_berth
- start_time: when did/will it start
- estimated_duration: how long expected
- affected_operations: what is stopped (loading/unloading/bunkering/pilotage/...)
- source_count: how many independent sources confirm this
- verification_status: confirmed | unverified | conflicting

### 4. Report Order
Put closures/suspensions FIRST, then disruptions, then normal ports.

## Output JSON Format
{{
  "closures": [
    {{
      "country": "国家",
      "port": "港口名",
      "port_code": "CODE",
      "closure_type": "weather/labor/accident/regulatory/other",
      "closure_scope": "full_port/specific_terminal/specific_berth",
      "affected_facility": "受影响的码头/泊位名称",
      "start_time": "开始时间或预估开始时间",
      "estimated_duration": "预计持续时间",
      "affected_operations": "受影响的操作类型",
      "reason_detail": "详细原因说明（2-3句话）",
      "source_count": 2,
      "verification_status": "confirmed/unverified/conflicting",
      "verification_note": "交叉验证说明",
      "weather_link": "是否与天气相关及具体关联",
      "confidence": "high/medium/low"
    }}
  ],
  "suspensions": [
    {{
      "country": "国家",  
      "port": "港口名",
      "port_code": "CODE",
      "suspension_type": "vessel_traffic/pilotage/bunkering/cargo_ops/other",
      "detail": "详细说明",
      "start_time": "开始时间",
      "estimated_duration": "预计持续时间",
      "verification_status": "confirmed/unverified",
      "confidence": "high/medium/low"
    }}
  ],
  "disrupted_ports": [
    {{
      "country": "国家",
      "port": "港口名",
      "port_code": "CODE",
      "issue": "具体问题",
      "severity": "moderate/significant",
      "closure_risk": "low/medium/high"
    }}
  ],
  "normal_ports": [
    {{
      "country": "国家",
      "port": "港口名", 
      "port_code": "CODE",
      "status_note": "正常运营简述",
      "weather_note": "天气说明"
    }}
  ],
  "no_data_ports": [
    {{
      "country": "国家",
      "port": "港口名",
      "port_code": "CODE"
    }}
  ],
  "summary": "全局摘要（closures/suspensions数量优先）",
  "alerts": ["紧急预警"]
}}

## Final Verification Checklist (MUST complete before output)
1. Every closure: cross-checked against at least 1 other news item? (note source_count)
2. Weather-only predictions: marked as "forecast", not "confirmed"?
3. Conflicting reports: flagged and explained?
4. All {total_ports} ports accounted for across closures/suspensions/disrupted/normal/no_data?
5. No port appears in more than one category?

Return valid JSON only.
"""


def organize_news(news_list, ports, weather_data=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Port list
    lines = ["| Country | Port | Code |", "|---|---|---|"]
    for p in ports:
        lines.append(f"| {p['country']} | {p['port']} | {p['code']} |")

    # News (send ALL, not just 25 — closure detection needs breadth)
    items = []
    for i, n in enumerate(news_list[:30]):
        items.append(f"[{i+1}] {n['title']} | {n.get('summary','')[:200]}")

    # Weather
    w_lines = []
    for code, wd in (weather_data or {}).items():
        s = wd.get("summary", {})
        if s and not wd.get("error"):
            w_lines.append(f"- {wd['country']}/{wd['port']}({code}): {s.get('wave','?')} {s.get('wind','?')} {s.get('trend','?')}")

    prompt = PROMPT.format(
        port_list="\n".join(lines),
        news_text="\n".join(items) if items else "(no news)",
        weather_text="\n".join(w_lines) if w_lines else "(unavailable)",
        total_ports=len(ports),
    )

    for attempt in range(3):
        try:
            resp = model.generate_content(
                prompt,
                generation_config={"temperature": 0.1, "max_output_tokens": 8192},
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
            return {"closures":[],"suspensions":[],"disrupted_ports":[],"normal_ports":[],"no_data_ports":[],"alerts":[],"error": str(e)}

    return {"closures":[],"suspensions":[],"disrupted_ports":[],"normal_ports":[],"no_data_ports":[],"alerts":[],"error":"JSON failed"}
