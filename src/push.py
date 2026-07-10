"""Push daily report via Gmail SMTP."""
import os, re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def md_to_html(md_text):
    """Convert Markdown to basic HTML."""
    lines = md_text.split("\n")
    html = []
    in_table = False

    for line in lines:
        if line.startswith("# "):
            html.append(f"<h1>{line[2:]}</h1>")
        elif line.startswith("## "):
            html.append(f"<h2>{line[3:]}</h2>")
        elif line.startswith("### "):
            html.append(f"<h3>{line[4:]}</h3>")
        elif line.strip() == "---":
            html.append("<hr>")
        elif line.startswith("> "):
            html.append(f"<blockquote>{line[2:]}</blockquote>")
        elif line.startswith("|") and line.endswith("|"):
            cells = [c.strip() for c in line[1:-1].split("|")]
            if all(c.replace("-","").replace(":","") == "" for c in cells):
                continue
            tag = "th" if not in_table else "td"
            row = "".join(f"<{tag}>{c}</{tag}>" for c in cells)
            if not in_table:
                html.append(
                    "<table border=1 cellpadding=6 cellspacing=0 style=border-collapse:collapse>"
                )
                in_table = True
            html.append(f"<tr>{row}</tr>")
        else:
            if in_table:
                html.append("</table>")
                in_table = False
            line = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", line)
            if line.strip():
                html.append(f"<p>{line}</p>")
            else:
                html.append("<br>")

    if in_table:
        html.append("</table>")

    return "\n".join(html)


def push_report(title, md_content):
    """Send report via Gmail SMTP."""
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    mail_to_raw = os.environ.get("MAIL_TO")
    mail_to = [m.strip() for m in mail_to_raw.split(",") if m.strip()] if mail_to_raw else []

    missing = []
    if not smtp_user: missing.append("SMTP_USER")
    if not smtp_pass: missing.append("SMTP_PASS")
    if not mail_to: missing.append("MAIL_TO")
    if missing:
        raise RuntimeError(f"Missing env: {missing}")

    html_body = md_to_html(md_content)
    full_html = (
        "<!DOCTYPE html><html><head><meta charset=utf-8></head>"
        "<body style=font-family:Arial;max-width:700px;margin:0 auto;padding:20px>"
        + html_body +
        "</body></html>"
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = title
    msg["From"] = smtp_user
    msg["To"] = mail_to
    msg.attach(MIMEText(full_html, "html", "utf-8"))

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587, timeout=15)
        server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, mail_to, msg.as_string())
        server.quit()
        print(f"  Email sent to {mail_to}")
        return {"success": True}
    except Exception as e:
        print(f"  Email failed: {e}")
        raise
