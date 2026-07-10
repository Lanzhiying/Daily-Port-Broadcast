"""
Generate daily broadcast with closures/suspensions as PRIMARY sections.
"""
from datetime import datetime


def format_report(data, no_match_news, weather_data, ports):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# Port Broadcast {today}", ""]

    if not isinstance(data, dict):
        lines.append("(no data)")
        return "\n".join(lines)

    summary = data.get("summary", "")
    alerts = data.get("alerts", [])
    closures = data.get("closures", [])
    suspensions = data.get("suspensions", [])
    disrupted = data.get("disrupted_ports", [])
    normal = data.get("normal_ports", [])
    no_data = data.get("no_data_ports", [])

    if summary:
        lines.append(f"> {summary}")
        lines.append("")

    # === ALERTS ===
    if alerts:
        lines.append("## ALERTS")
        for a in alerts:
            lines.append(f"- {a}")
        lines.append("")

    # === CLOSURES (PRIMARY) ===
    if closures:
        lines.append("---")
        lines.append("## PORT CLOSURES")
        lines.append("")
        for c in closures:
            verified = c.get("verification_status", "unverified")
            vflag = "CONFIRMED" if verified == "confirmed" else ("UNVERIFIED" if verified == "unverified" else "CONFLICTING")
            
            lines.append(f"### {vflag}: {c.get('country','')} / {c.get('port','')} ({c.get('port_code','')})")
            lines.append("")
            lines.append(f"- **Type**: {c.get('closure_type','?')}")
            lines.append(f"- **Scope**: {c.get('closure_scope','?')} — {c.get('affected_facility','?')}")
            lines.append(f"- **Start**: {c.get('start_time','?')}")
            lines.append(f"- **Duration**: {c.get('estimated_duration','?')}")
            lines.append(f"- **Affected**: {c.get('affected_operations','?')}")
            lines.append(f"- **Reason**: {c.get('reason_detail','?')}")
            lines.append(f"- **Weather**: {c.get('weather_link','?')}")
            lines.append(f"- **Sources**: {c.get('source_count',0)} independent sources")
            if verified == "unverified":
                lines.append(f"- **Note**: {c.get('verification_note','Needs confirmation')}")
            elif verified == "conflicting":
                lines.append(f"- **Conflict**: {c.get('verification_note','Sources disagree')}")
            lines.append("")
    else:
        lines.append("---")
        lines.append("## PORT CLOSURES")
        lines.append("")
        lines.append("None reported today.")
        lines.append("")

    # === SUSPENSIONS ===
    if suspensions:
        lines.append("---")
        lines.append("## Shipping Suspensions")
        lines.append("")
        for s in suspensions:
            vflag = "CONFIRMED" if s.get("verification_status") == "confirmed" else "UNVERIFIED"
            lines.append(f"### {vflag}: {s.get('country','')} / {s.get('port','')}")
            lines.append("")
            lines.append(f"- **Type**: {s.get('suspension_type','?')}")
            lines.append(f"- **Detail**: {s.get('detail','?')}")
            lines.append(f"- **Start**: {s.get('start_time','?')}")
            lines.append(f"- **Duration**: {s.get('estimated_duration','?')}")
            lines.append("")
    else:
        lines.append("---")
        lines.append("## Shipping Suspensions")
        lines.append("")
        lines.append("None reported today.")
        lines.append("")

    # === DISRUPTED ===
    if disrupted:
        lines.append("---")
        lines.append("## Disrupted Operations")
        lines.append("")
        lines.append("| Port | Country | Issue | Severity | Closure Risk |")
        lines.append("|------|---------|-------|----------|-------------|")
        for d in disrupted:
            lines.append(f"| **{d.get('port','?')}** | {d.get('country','?')} | {d.get('issue','?')} | {d.get('severity','?')} | {d.get('closure_risk','?')} |")
        lines.append("")

    # === NORMAL ===
    if normal:
        lines.append("---")
        lines.append("## Normal Operations")
        lines.append("")
        by_c = {}
        for n in normal:
            by_c.setdefault(n.get("country","Other"), []).append(n)
        for country in sorted(by_c):
            lines.append(f"### {country}")
            lines.append("")
            for n in by_c[country]:
                wn = n.get("weather_note", "")
                sn = n.get("status_note", "")
                lines.append(f"- **{n.get('port','?')}**: {sn}. {wn}")
            lines.append("")

    # === NO DATA ===
    if no_data:
        lines.append("---")
        lines.append("## No Data")
        lines.append("")
        ports_str = ", ".join(f"{n.get('port','?')}" for n in no_data)
        lines.append(f"{ports_str}")
        lines.append("")

    # === WEATHER ===
    if weather_data:
        lines.append("---")
        lines.append("## Weather Summary")
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
    lines.append(f"*Auto {today} | Cross-verified | Daily Port Broadcast*")
    return "\n".join(lines)
