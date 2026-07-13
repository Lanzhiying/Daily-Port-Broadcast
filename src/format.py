"""
Generate daily broadcast in Chinese. Typhoon alerts prominently.
"""
from datetime import datetime


def format_report(data, no_match_news, weather_data, ports):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 港口每日广播 — {today}", ""]

    if not isinstance(data, dict):
        lines.append("（无数据）")
        return "\n".join(lines)

    summary = data.get("summary", "")
    typhoon = data.get("typhoon_alert", "")
    alerts = data.get("alerts", [])
    closures = data.get("closures", [])
    suspensions = data.get("suspensions", [])
    disrupted = data.get("disrupted_ports", [])
    normal = data.get("normal_ports", [])
    no_data = data.get("no_data_ports", [])

    if summary:
        lines.append(f"> **摘要：** {summary}")
        lines.append("")

    # === TYPHOON ALERT ===
    if typhoon and typhoon != "无台风影响":
        lines.append("## 台风/热带气旋预警")
        lines.append("")
        lines.append(f"> {typhoon}")
        lines.append("")

    # === ALERTS ===
    if alerts:
        lines.append("## 紧急预警")
        for a in alerts:
            lines.append(f"- {a}")
        lines.append("")

    # === CLOSURES ===
    lines.append("---")
    lines.append("## 封港情况")
    lines.append("")
    if closures:
        for c in closures:
            v = c.get("verification_status", "")
            vflag = "预测" if "预测" in v else ("已确认" if "已确认" in v else v)
            lines.append(f"### {vflag}：{c.get('country','')} / {c.get('port','')}（{c.get('port_code','')}）")
            lines.append("")
            lines.append(f"- **类型**：{c.get('closure_type','?')}")
            lines.append(f"- **范围**：{c.get('closure_scope','?')} — {c.get('affected_facility','?')}")
            lines.append(f"- **时间**：{c.get('start_time','?')}（预计持续 {c.get('estimated_duration','?')}）")
            lines.append(f"- **原因**：{c.get('reason_detail','?')}")
            if c.get("weather_basis"):
                lines.append(f"- **天气依据**：{c.get('weather_basis')}")
            lines.append("")
    else:
        lines.append("今日无封港。")
        lines.append("")

    # === SUSPENSIONS ===
    lines.append("---")
    lines.append("## 停航/暂停运营")
    lines.append("")
    if suspensions:
        for s in suspensions:
            vflag = "预测" if "预测" in s.get("verification_status","") else s.get("verification_status","?")
            lines.append(f"### {vflag}：{s.get('country','')} / {s.get('port','')}")
            lines.append("")
            lines.append(f"- **类型**：{s.get('suspension_type','?')}")
            lines.append(f"- **详情**：{s.get('detail','?')}")
            lines.append(f"- **时间**：{s.get('start_time','?')}（预计持续 {s.get('estimated_duration','?')}）")
            if s.get("weather_basis"):
                lines.append(f"- **天气依据**：{s.get('weather_basis')}")
            lines.append("")
    else:
        lines.append("今日无停航。")
        lines.append("")

    # === DISRUPTED ===
    if disrupted:
        lines.append("---")
        lines.append("## 运行中断")
        lines.append("")
        lines.append("| 港口 | 问题 | 严重程度 | 封港风险 | 天气 |")
        lines.append("|------|------|----------|----------|------|")
        for d in disrupted:
            lines.append(f"| **{d.get('port','?')}** ({d.get('country','?')}) | {d.get('issue','?')} | {d.get('severity','?')} | {d.get('closure_risk','?')} | {d.get('weather_note','?')} |")
        lines.append("")

    # === NORMAL ===
    if normal:
        lines.append("---")
        lines.append("## 正常运行")
        lines.append("")
        by_c = {}
        for n in normal:
            by_c.setdefault(n.get("country","其他"), []).append(n)
        for country in sorted(by_c):
            lines.append(f"### {country}")
            lines.append("")
            for n in by_c[country]:
                lines.append(f"- **{n.get('port','?')}**：{n.get('status_note','?')}。{n.get('weather_note','?')}")
            lines.append("")

    # === NO DATA ===
    if no_data:
        lines.append("---")
        lines.append("## 无数据")
        lines.append("")
        lines.append("、".join(n.get("port","?") for n in no_data))
        lines.append("")

    # === WEATHER RISK MAP ===
    if weather_data:
        lines.append("---")
        lines.append("## 天气风险总览")
        lines.append("")
        lines.append("| 港口 | 浪高 | 风速 | 阵风 | 涌浪 | 降雨 | 趋势 | 风险 |")
        lines.append("|------|------|------|------|------|------|------|------|")
        for code, wd in weather_data.items():
            r = wd.get("risk", {})
            risk = r.get("risk","?")
            flag = {"critical":"CRITICAL","high":"HIGH","moderate":"MOD","low":"OK","unknown":"?"}.get(risk, risk)
            lines.append(
                f"| {wd.get('country','?')} {wd.get('port','?')} | {r.get('wave','-')} | {r.get('wind','-')} | "
                f"{r.get('gust','-')} | {r.get('swell','-')} | {r.get('rain','-')} | {r.get('trend','-')} | **{flag}** |"
            )
        lines.append("")

    lines.append("---")
    lines.append(f"*{today} | 天气驱动预警 | Daily Port Broadcast*")
    return "\n".join(lines)
