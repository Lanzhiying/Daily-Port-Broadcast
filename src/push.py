"""
Push daily report to WeChat via WxPusher (free, no real-name verification).
https://wxpusher.zjiecode.com/
"""
import os
import httpx


def push_to_wechat(title, content):
    """Push markdown message to WeChat via WxPusher."""
    app_token = os.environ.get("WXPUSHER_APP_TOKEN")
    uid = os.environ.get("WXPUSHER_UID")

    if not app_token:
        raise RuntimeError("WXPUSHER_APP_TOKEN not set in environment")
    if not uid:
        raise RuntimeError("WXPUSHER_UID not set in environment")

    url = "https://wxpusher.zjiecode.com/api/send/message"
    payload = {
        "appToken": app_token,
        "content": content,
        "summary": title,
        "contentType": 3,  # 3 = Markdown
        "uids": [uid],
    }

    resp = httpx.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    result = resp.json()

    if result.get("code") == 1000:
        print(f"  WxPusher push success")
    else:
        print(f"  WxPusher push failed: {result}")

    return result


if __name__ == "__main__":
    push_to_wechat("test", "## test\nhello from Daily Port Broadcast")
