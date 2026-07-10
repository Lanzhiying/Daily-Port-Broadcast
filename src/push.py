"""
Push daily report to WeChat via PushPlus (free tier: 200 msgs/day).
Alternative: Server酱 (sct.ftqq.com)
"""
import os
import httpx


def push_to_wechat(title, content, push_type="pushplus"):
    """
    Push markdown message to WeChat.

    Args:
        title: message title
        content: markdown body
        push_type: "pushplus" or "serverchan"
    """
    if push_type == "pushplus":
        return push_via_pushplus(title, content)
    elif push_type == "serverchan":
        return push_via_serverchan(title, content)
    else:
        raise ValueError(f"Unknown push type: {push_type}")


def push_via_pushplus(title, content):
    """Push via PushPlus (pushplus.plus) — free 200/day."""
    token = os.environ.get("PUSHPLUS_TOKEN")
    if not token:
        raise RuntimeError("PUSHPLUS_TOKEN not set in environment")

    url = "https://www.pushplus.plus/send"
    payload = {
        "token": token,
        "title": title,
        "content": content,
        "template": "markdown",  # Use markdown template
    }
    resp = httpx.post(url, json=payload, timeout=15)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 200:
        print(f"  ✅ PushPlus 推送成功")
    else:
        print(f"  ❌ PushPlus 推送失败: {result}")
    return result


def push_via_serverchan(title, content):
    """Push via Server酱 (sct.ftqq.com) — free 5/day."""
    key = os.environ.get("SERVERCHAN_KEY")
    if not key:
        raise RuntimeError("SERVERCHAN_KEY not set in environment")

    url = f"https://sctapi.ftqq.com/{key}.send"
    payload = {
        "title": title,
        "desp": content,
    }
    resp = httpx.post(url, data=payload, timeout=15)
    resp.raise_for_status()
    result = resp.json()
    if result.get("code") == 0:
        print(f"  ✅ Server酱 推送成功")
    else:
        print(f"  ❌ Server酱 推送失败: {result}")
    return result


if __name__ == "__main__":
    push_to_wechat("测试标题", "## 测试内容\n这是一条测试消息")
