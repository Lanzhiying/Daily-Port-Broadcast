"""
Format organized data into Markdown daily broadcast.
"""
from datetime import datetime


def format_report(reports, no_match_news, weather_data, ports):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# Port Broadcast {today}", ""]

    summary = ""
    alerts = []
    if isinstance(reports, dict):
        summary = reports.get("summary", "")
        alerts = reports.get("alerts", [])
        reports = reports.get("reports", [])

    if summary:
        lines.append(f"> {summary}")
        lines.append("")

    # Alerts
    if alerts:
        lines.append("## Alerts")
        for a in alerts:
            lines.append(f"- {a}")
        lines.append("")

    # Port status table
    lines.append("---")
    lines.append("## Port Status")
    lines.append("")

    status_label = {
        "normal": "Normal", "congested": "Congested",
        "closed": "CLOSED", "disrupted": "Disrupted", "no_data": "No Data",
    }

    by_country = {}
    for r in reports:
        by_country.setdefault(r.get("country", "Other"), []).append(r)

    for country in sorted(by_country):
        items = by_country[country]
        lines.append(f"### {country}")
        lines.append("")
        lines.append("| Port | Status | Weather Impact | Closure Forecast | Confidence |")
        lines.append("|------|--------|----------------|-----------------|------------|")
        for r in items:
            port = r.get("port", "?")
            status = status_label.get(r.get("status", "no_data"), r.get("status", "?"))
            wi = r.get("weather_impact", "-")
            cf = r.get("closure_forecast", "-")
            conf = r.get("confidence", "?")
            lines.append(f"| **{port}** | {status} | {wi} | {cf} | {conf} |")
        lines.append("")

    # Terminal detail for key ports
    lines.append("---")
    lines.append("## Terminal Detail (Key Ports)")
    lines.append("")
    has_detail = False
    for r in reports:
        td = r.get("terminal_detail", "")
        if td and td != "-":
            has_detail = True
            lines.append(f"**{r.get('country','')} / {r.get('port','')}**")
            lines.append(f"> {td}")
            lines.append("")
    if not has_detail:
        lines.append("(no terminal-level detail available)")
        lines.append("")

    # Key events
    lines.append("---")
    lines.append("## Key Events")
    lines.append("")
    has_events = False
    for r in reports:
        events = r.get("key_events", [])
        if events:
            has_events = True
            lines.append(f"**{r.get('country','')} / {r.get('port','')}**")
            for e in events:
                lines.append(f"- {e}")
            lines.append("")
    if not has_events:
        lines.append("(no significant events)")
        lines.append("")

    # Weather table
    if weather_data:
        lines.append("---")
        lines.append("## Weather")
        lines.append("")
        lines.append("| Country | Port | Wave | Wind | Trend |")
        lines.append("|---------|------|------|------|-------|")
        for code, wd in weather_data.items():
            s = wd.get("summary", {})
            if wd.get("error"):
                lines.append(f"| {wd.get('country','?')} | {wd.get('port','?')} | failed | - | - |")
            else:
                lines.append(f"| {wd.get('country','?')} | {wd.get('port','?')} | {s.get('wave','-')} | {s.get('wind','-')} | {s.get('trend','-')} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*Auto {today} | Daily Port Broadcast*")
    return "\n".join(lines)
