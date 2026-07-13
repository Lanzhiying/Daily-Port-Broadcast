"""
Port status analysis. 
AGGRESSIVE weather-to-closure mapping.
"""
import json, os, time
import google.generativeai as genai


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["ports"]


PROMPT = """你是港口紧急运营分析师。你的任务是检测所有封港、停航和运行风险。

## 监控港口（{total_ports}个，全部必须报告）
{port_list}

## 新闻数据
{news_text}

## 天气风险数据（已标关键级别）
{weather_text}

## 天气 → 运营影响映射（严格执行）

### CRITICAL 级别港口（必须生成封港或停航条目）：
- 巨浪 > 3.5m → 报告为 "全港关闭" 或 "泊位暂停"
- 暴风 > 50km/h → 报告为 "全港关闭"  
- 雷暴天气 → 报告为 "码头作业暂停"，预估持续 2-6 小时
- 涌浪 > 3m → 报告为 "引航暂停"
- 趋势"急剧恶化" → 报告为 "预计未来24-48h关闭"，给出具体时间窗

### HIGH 级别港口：
- 大浪 2.5-3.5m → 报告为 "吊机/部分泊位可能暂停"
- 强风 35-50km/h → 报告为 "吊机作业受限，引航可能暂停"
- 趋势"恶化中" → 报告为 "如持续恶化，未来48h可能关闭"

### MODERATE 级别港口：
- 报告天气对运营的轻度影响
- 如趋势恶化，标记 closure_risk 为 "中"

### LOW 级别港口：
- 报告为 "正常运行"
- 如有微浪或微风，简单说明

## 重要规则
1. CRITICAL 级别港口必须至少生成 1 条 closures 或 suspensions 条目
2. 预估时间窗必须具体（如"7月11日14:00-20:00"或"未来24小时"）
3. 即使没有新闻，天气数据本身就足够生成封港/停航预警
4. 没有天气数据的港口：如有新闻用新闻，都没有标"无数据"
5. 全部 {total_ports} 个港口必须都有条目

## 输出格式（纯JSON，中文）
{{
  "closures": [
    {{
      "country": "国家",
      "port": "港口名",
      "port_code": "CODE",
      "closure_type": "天气/劳工/事故/监管/其他",
      "closure_scope": "全港/特定码头/特定泊位",
      "affected_facility": "受影响设施",
      "start_time": "开始时间或预估开始",
      "estimated_duration": "预计持续",
      "reason_detail": "详细原因（基于天气或新闻）",
      "weather_basis": "导致关闭的具体天气数据",
      "source_count": 1,
      "verification_status": "预测（基于天气）/已确认（基于新闻）",
      "confidence": "高/中/低"
    }}
  ],
  "suspensions": [
    {{
      "country": "国家",
      "port": "港口",
      "port_code": "CODE", 
      "suspension_type": "船舶交通/引航/加油/装卸/吊机/其他",
      "detail": "详细说明",
      "start_time": "开始时间",
      "estimated_duration": "预计持续",
      "weather_basis": "天气依据",
      "verification_status": "预测/已确认",
      "confidence": "高/中/低"
    }}
  ],
  "disrupted_ports": [
    {{
      "country": "国家", "port": "港口", "port_code": "CODE",
      "issue": "具体问题", "severity": "中度/严重",
      "closure_risk": "低/中/高", "weather_note": "天气说明"
    }}
  ],
  "normal_ports": [
    {{
      "country": "国家", "port": "港口", "port_code": "CODE",
      "status_note": "运营正常", "weather_note": "天气简述"
    }}
  ],
  "no_data_ports": [
    {{"country": "国家", "port": "港口", "port_code": "CODE"}}
  ],
  "summary": "全局摘要（封港数、停航数、台风影响、最严重港口）",
  "typhoon_alert": "如检测到台风/热带气旋影响，给出预警（无则写'无台风影响'）",
  "alerts": ["紧急预警"]
}}

只输出JSON，不要其他文字。
"""


def organize_news(news_list, ports, weather_data=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Port table
    lines = ["| 国家 | 港口 | 代码 |", "|---|---|---|"]
    for p in ports:
        lines.append(f"| {p['country']} | {p['port']} | {p['code']} |")

    # News
    items = []
    for i, n in enumerate(news_list[:30]):
        items.append(f"[{i+1}] {n['title']} | {n.get('summary','')[:200]}")

    # Weather with risk levels
    w_lines = []
    critical_ports = []
    high_ports = []
    for code, wd in (weather_data or {}).items():
        risk = wd.get("risk", {})
        level = risk.get("risk", "unknown")
        wave = risk.get("wave", "?")
        wind = risk.get("wind", "?")
        trend = risk.get("trend", "?")
        alerts = risk.get("alerts", [])
        
        line = f"- [{level.upper()}] {wd['country']}/{wd['port']}({code}): wave={wave} wind={wind} gust={risk.get('gust','?')} trend={trend}"
        if alerts:
            line += f" alerts={'; '.join(alerts)}"
        w_lines.append(line)
        
        if level == "critical":
            critical_ports.append(f"{wd['port']}")
        elif level == "high":
            high_ports.append(f"{wd['port']}")

    weather_text = "\n".join(w_lines) if w_lines else "(天气不可用)"
    
    if critical_ports:
        weather_text += f"\n\nCRITICAL: {', '.join(critical_ports)} — MUST generate closure entries"
    if high_ports:
        weather_text += f"\n\nHIGH RISK: {', '.join(high_ports)} — MUST generate disruption entries"

    prompt = PROMPT.format(
        port_list="\n".join(lines),
        news_text="\n".join(items) if items else "(今日无新闻)",
        weather_text=weather_text,
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
