"""
Port status analysis. Primary: closures/suspensions.
If no news but weather available, report as normal with weather note.
"""
import json, os, time
import google.generativeai as genai


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)["ports"]


PROMPT = """你是港口运营分析师。你的首要任务是检测港口封港和停航情况。

## 监控港口（必须全部报告）
{port_list}

## 新闻数据
{news_text}

## 天气数据  
{weather_text}

## 核心任务

### 1. 封港检测（最高优先级）
从新闻中扫描以下信号：
- 港口关闭、码头停运、泊位暂停
- 不可抗力声明
- 船舶交通暂停、引航服务停止
- 台风/风暴导致封港
- 罢工、劳工行动导致停运
- 事故、碰撞、溢油导致关闭

### 2. 交叉验证（强制执行）
- 封港信息必须至少有2个不同来源确认
- 单一来源的报告标注为"待确认"
- 来源矛盾时标注为"信息冲突"并说明
- 纯天气推测的标注为"预测"

### 3. 无新闻时的处理
- 如果某港口无相关新闻，但天气数据正常 → 状态为"正常"，confidence为"中"
- 如果某港口无新闻且天气数据不可用 → 状态为"无数据"，confidence为"低"
- 如果天气数据显示大风浪 → 标注天气风险，即使无新闻

## 输出格式（必须中文，纯JSON）
{{
  "closures": [
    {{
      "country": "国家（中文）",
      "port": "港口名（中文）",
      "port_code": "CODE",
      "closure_type": "天气/劳工/事故/监管/其他",
      "closure_scope": "全港/特定码头/特定泊位",
      "affected_facility": "受影响的码头或泊位名称",
      "start_time": "开始时间",
      "estimated_duration": "预计持续时间",
      "affected_operations": "受影响的操作",
      "reason_detail": "详细原因（2-3句中文）",
      "source_count": 2,
      "verification_status": "已确认/待确认/信息冲突",
      "verification_note": "交叉验证说明（中文）",
      "weather_link": "与天气的关联（中文）",
      "confidence": "高/中/低"
    }}
  ],
  "suspensions": [
    {{
      "country": "国家",
      "port": "港口",
      "port_code": "CODE",
      "suspension_type": "船舶交通/引航/加油/装卸/其他",
      "detail": "详细说明",
      "start_time": "开始时间",
      "estimated_duration": "预计持续时间",
      "verification_status": "已确认/待确认",
      "confidence": "高/中/低"
    }}
  ],
  "disrupted_ports": [
    {{
      "country": "国家",
      "port": "港口",
      "port_code": "CODE",
      "issue": "具体问题",
      "severity": "中度/严重",
      "closure_risk": "低/中/高"
    }}
  ],
  "normal_ports": [
    {{
      "country": "国家",
      "port": "港口",
      "port_code": "CODE",
      "status_note": "运营状态说明（中文）",
      "weather_note": "天气影响说明（中文）"
    }}
  ],
  "no_data_ports": [
    {{
      "country": "国家",
      "port": "港口",
      "port_code": "CODE"
    }}
  ],
  "summary": "全局摘要（中文，封港/停航数量优先，一句话概括）",
  "alerts": ["紧急预警（中文）"]
}}

## 最终检查（输出前必须确认）
1. 每条封港是否交叉验证？（source_count ≥ 2 才是"已确认"）
2. 纯天气预测是否标注为"预测"？
3. 相互矛盾的报道是否标注"信息冲突"？
4. 全部 {total_ports} 个港口是否都已归类？
5. 所有字段值是否都是中文？

只输出有效JSON，不要任何解释文字。
"""


def organize_news(news_list, ports, weather_data=None):
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set")

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    lines = ["| 国家 | 港口 | 代码 |", "|---|---|---|"]
    for p in ports:
        lines.append(f"| {p['country']} | {p['port']} | {p['code']} |")

    items = []
    for i, n in enumerate(news_list[:30]):
        items.append(f"[{i+1}] {n['title']} | {n.get('summary','')[:200]}")

    w_lines = []
    for code, wd in (weather_data or {}).items():
        s = wd.get("summary", {})
        if s and not wd.get("error"):
            w_lines.append(f"- {wd['country']}/{wd['port']}({code}): {s.get('wave','?')} {s.get('wind','?')} {s.get('trend','?')}")

    prompt = PROMPT.format(
        port_list="\n".join(lines),
        news_text="\n".join(items) if items else "(今日无新闻)",
        weather_text="\n".join(w_lines) if w_lines else "(天气数据不可用)",
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
