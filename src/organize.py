"""
Use Gemini 1.5 Flash (free tier) to:
1. Classify news by country-port
2. Generate Chinese summaries
3. Detect port closures, congestion, etc.
"""
import json
import os
import time
import google.generativeai as genai


def load_ports(config_path="config/ports.json"):
    with open(config_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["ports"]


def build_port_context(ports):
    """Build a short port reference for the LLM prompt."""
    lines = []
    for p in ports:
        lines.append(f"- {p['country']} / {p['port']} ({p['port_en']}) — code: {p['code']}")
    return "\n".join(lines)


PROMPT_TEMPLATE = """You are a port intelligence analyst. Classify the following news by country-port and generate concise summaries.

## Monitored Ports
{port_context}

## News Items
{news_text}

## Output Requirements
Return ONLY valid JSON in this exact format (no markdown, no explanation):

{{
  "reports": [
    {{
      "country": "country name",
      "port": "port name in Chinese",
      "port_code": "PORT_CODE",
      "summary": "one-line summary (under 50 words)",
      "is_port_closure": false,
      "congestion_level": "normal/mild/moderate/severe",
      "closure_risk": "none/low/medium/high",
      "confidence": "high/medium/low"
    }}
  ],
  "no_match_news": [
    {{
      "title": "original title",
      "reason": "why it doesn't match any monitored port"
    }}
  ]
}}

## Rules
1. Only extract news directly related to the monitored ports above
2. One record per port even if news mentions multiple ports
3. Port closure: news mentions "closure/shutdown/suspension/halted/closed"
4. Congestion: judge from "waiting time/delay/congestion/backlog/queue"
5. Closure risk: consider weather + strikes + policy + maintenance mentioned in news
6. News not matching any port goes to no_match_news
7. Return valid JSON only, no extra text
"""


def organize_news(news_list, ports, weather_data=None):
    """Send news to Gemini for classification and summarization."""

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in environment")

    genai.configure(api_key=api_key)

    # Use gemini-1.5-flash (more generous free tier than 2.0)
    model = genai.GenerativeModel("gemini-1.5-flash")

    # Build port context
    port_context = build_port_context(ports)

    # Build news text (limit to 25 items to stay under token limits)
    news_items = []
    for i, item in enumerate(news_list[:25]):
        title = item.get("title", "")
        summary = item.get("summary", "")[:200]
        news_items.append(f"[{i+1}] Title: {title}\n    Summary: {summary}")
    news_text = "\n".join(news_items)

    # Weather context
    weather_context = ""
    if weather_data:
        weather_lines = []
        for code, wd in weather_data.items():
            s = wd.get("summary", {})
            if s and not wd.get("error"):
                weather_lines.append(
                    f"- {wd['country']}/{wd['port']}({code}): "
                    f"wave={s.get('wave','?')}, wind={s.get('wind','?')}, {s.get('trend','')}"
                )
        if weather_lines:
            weather_context = "\n## Current Weather\n" + "\n".join(weather_lines)

    prompt = PROMPT_TEMPLATE.format(
        port_context=port_context,
        news_text=news_text,
    )
    if weather_context:
        prompt += weather_context

    # Call Gemini with retry
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(
                prompt,
                generation_config={
                    "temperature": 0.2,
                    "max_output_tokens": 4096,
                },
            )
            text = response.text.strip()

            # Strip markdown code fences
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text[:-3]
            text = text.strip()

            result = json.loads(text)
            return result

        except json.JSONDecodeError as e:
            print(f"  Attempt {attempt+1}: invalid JSON: {e}")
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
        except Exception as e:
            err_msg = str(e)
            if "429" in err_msg:
                wait = 60
                print(f"  Rate limited (429), waiting {wait}s...")
                time.sleep(wait)
                continue
            print(f"  Gemini error: {e}")
            return {"reports": [], "no_match_news": [], "error": str(e)}

    return {"reports": [], "no_match_news": [], "error": "JSON parse failed after retries"}


if __name__ == "__main__":
    ports = load_ports()
    print(f"Loaded {len(ports)} ports")
