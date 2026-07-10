"""
Format organized data into Markdown daily port broadcast.
"""
from datetime import datetime


def format_report(reports, no_match_news, weather_data, ports):
    today = datetime.now().strftime("%Y-%m-%d")

    lines = []
    lines.append(f"# Port Broadcast {today}")
    lines.append("")

    # Summary
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
    lines.append("")
    lines.append("## Port Status")
    lines.append("")

    status_emoji = {
        "normal": "Normal",
        "congested": "Congested",
        "closed": "CLOSED",
        "disrupted": "Disrupted",
        "no_data": "No Data",
    }

    # Group by country
    by_country = {}
    for r in reports:
        c = r.get("country", "Other")
        by_country.setdefault(c, []).append(r)

    for country in sorted(by_country):
        items = by_country[country]
        lines.append(f"### {country}")
        lines.append("")
        lines.append("| Port | Status | Details | Closure Risk | Confidence |")
        lines.append("|------|--------|---------|-------------|------------|")
        for r in items:
            port = r.get("port", "?")
            status = r.get("status", "no_data")
            st_label = status_emoji.get(status, status)
            detail = r.get("headline", r.get("congestion_detail", ""))
            risk = r.get("closure_risk", "?")
            conf = r.get("confidence", "?")
            lines.append(f"| **{port}** | {st_label} | {detail} | {risk} | {conf} |")
        lines.append("")

    # Weather
    if weather_data:
        lines.append("---")
        lines.append("")
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

    # Key events
    lines.append("---")
    lines.append("")
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
        lines.append("(no significant events reported)")
        lines.append("")

    lines.append("---")
    lines.append(f"*Auto-generated {today} | Daily Port Broadcast*")

    return "\n".join(lines)
