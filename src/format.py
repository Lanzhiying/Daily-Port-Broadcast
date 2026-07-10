"""
Generate daily broadcast in Chinese.
"""
from datetime import datetime


def format_report(data, no_match_news, weather_data, ports):
    today = datetime.now().strftime("%Y-%m-%d")
    lines = [f"# 港口每日广播 — {today}", ""]

    if not isinstance(data, dict):
        lines.append("（无数据）")
        return "\n".join(lines)

    summary = data.get("summary", "")
    alerts = data.get("alerts", [])
    closures = data.get("closures", [])
    suspensions = data.get("suspensions", [])
    disrupted = data.get("disrupted_ports", [])
    normal = data.get("normal_ports", [])
    no_data = data.get("no_data_ports", [])

    if summary:
        lines.append(f"> **摘要：** {summary}")
        lines.append("")

    # === 预警 ===
    if alerts:
        lines.append("## 预警")
        for a in alerts:
            lines.append(f"- {a}")
        lines.append("")

    # === 封港 ===
    lines.append("---")
    lines.append("## 封港情况")
    lines.append("")
    if closures:
        for c in closures:
            verified = c.get("verification_status", "待确认")
            if verified == "已确认":
                vflag = "已确认"
            elif verified == "待确认":
                vflag = "待确认"
            else:
                vflag = "信息冲突"

            lines.append(f"### {vflag}：{c.get('country','')} / {c.get('port','')}（{c.get('port_code','')}）")
            lines.append("")
            lines.append(f"- **类型**：{c.get('closure_type','?')}")
            lines.append(f"- **范围**：{c.get('closure_scope','?')} — {c.get('affected_facility','?')}")
            lines.append(f"- **开始时间**：{c.get('start_time','?')}")
            lines.append(f"- **预计持续**：{c.get('estimated_duration','?')}")
            lines.append(f"- **受影响操作**：{c.get('affected_operations','?')}")
            lines.append(f"- **原因**：{c.get('reason_detail','?')}")
            lines.append(f"- **天气关联**：{c.get('weather_link','?')}")
            lines.append(f"- **交叉验证**：{c.get('source_count',0)} 个独立来源确认")
            if verified == "待确认":
                lines.append(f"- **备注**：{c.get('verification_note','需进一步确认')}")
            elif verified == "信息冲突":
                lines.append(f"- **冲突说明**：{c.get('verification_note','来源信息不一致')}")
            lines.append("")
    else:
        lines.append("今日无封港报告。")
        lines.append("")

    # === 停航 ===
    lines.append("---")
    lines.append("## 停航情况")
    lines.append("")
    if suspensions:
        for s in suspensions:
            vflag = "已确认" if s.get("verification_status") == "已确认" else "待确认"
            lines.append(f"### {vflag}：{s.get('country','')} / {s.get('port','')}")
            lines.append("")
            lines.append(f"- **类型**：{s.get('suspension_type','?')}")
            lines.append(f"- **详情**：{s.get('detail','?')}")
            lines.append(f"- **开始时间**：{s.get('start_time','?')}")
            lines.append(f"- **预计持续**：{s.get('estimated_duration','?')}")
            lines.append("")
    else:
        lines.append("今日无停航报告。")
        lines.append("")

    # === 运行中断 ===
    if disrupted:
        lines.append("---")
        lines.append("## 运行中断")
        lines.append("")
        lines.append("| 港口 | 国家 | 问题 | 严重程度 | 封港风险 |")
        lines.append("|------|------|------|----------|----------|")
        for d in disrupted:
            lines.append(f"| **{d.get('port','?')}** | {d.get('country','?')} | {d.get('issue','?')} | {d.get('severity','?')} | {d.get('closure_risk','?')} |")
        lines.append("")

    # === 正常运行 ===
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
            lines.append("| 港口 | 状态 | 天气 |")
            lines.append("|------|------|------|")
            for n in by_c[country]:
                lines.append(f"| **{n.get('port','?')}** | {n.get('status_note','?')} | {n.get('weather_note','?')} |")
            lines.append("")

    # === 无数据 ===
    if no_data:
        lines.append("---")
        lines.append("## 无数据港口")
        lines.append("")
        ports_str = "、".join(f"{n.get('port','?')}" for n in no_data)
        lines.append(f"{ports_str}")
        lines.append("")

    # === 天气 ===
    if weather_data:
        lines.append("---")
        lines.append("## 天气海况")
        lines.append("")
        lines.append("| 国家 | 港口 | 浪高 | 风速 | 趋势 |")
        lines.append("|------|------|------|------|------|")
        for code, wd in weather_data.items():
            s = wd.get("summary", {})
            if wd.get("error"):
                lines.append(f"| {wd.get('country','?')} | {wd.get('port','?')} | 获取失败 | - | - |")
            else:
                lines.append(f"| {wd.get('country','?')} | {wd.get('port','?')} | {s.get('wave','-')} | {s.get('wind','-')} | {s.get('trend','-')} |")
        lines.append("")

    lines.append("---")
    lines.append(f"*自动生成 {today} | 交叉验证 | Daily Port Broadcast*")
    return "\n".join(lines)
