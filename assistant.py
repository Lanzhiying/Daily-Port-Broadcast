"""
CrewAI-style Personal Work Assistant
3 agents: decompose → execute → verify (loop)
Uses DeepSeek API directly (no CrewAI dependency needed)
"""
import os, json, sys

# Try to use openai library (already installed)
try:
    from openai import OpenAI
except ImportError:
    print("Installing openai...")
    import subprocess, sys as _sys
    subprocess.run([_sys.executable, "-m", "pip", "install", "openai", "-q"])
    from openai import OpenAI


def get_client():
    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\n" + "=" * 50)
        print("需要配置 API Key")
        print("=" * 50)
        print("请选择：")
        print("1. DeepSeek（推荐，我已在使用）")
        print("2. OpenAI")
        print()
        choice = input("选择 (1/2): ").strip()
        
        if choice == "2":
            key = input("输入 OpenAI API Key: ").strip()
            os.environ["OPENAI_API_KEY"] = key
            return OpenAI(api_key=key), "gpt-4o-mini"
        else:
            key = input("输入 DeepSeek API Key: ").strip()
            os.environ["DEEPSEEK_API_KEY"] = key
            return OpenAI(api_key=key, base_url="https://api.deepseek.com"), "deepseek-chat"
    
    if "DEEPSEEK_API_KEY" in os.environ:
        return OpenAI(api_key=os.environ["DEEPSEEK_API_KEY"], base_url="https://api.deepseek.com"), "deepseek-chat"
    return OpenAI(api_key=os.environ["OPENAI_API_KEY"]), "gpt-4o-mini"


SYSTEM_PROMPTS = {
    "decomposer": """你是一个任务分解专家。你的任务是将用户的复杂需求拆解成3-5个清晰的步骤。
输出格式（严格JSON）：
{
  "task_name": "任务名称",
  "steps": ["步骤1: 具体做什么", "步骤2: 具体做什么", ...],
  "output_format": "最终交付物的格式要求（如：报告/邮件/表格/PPT草稿）",
  "key_requirements": ["关键要求1", "关键要求2"]
}
不要输出其他内容。""",

    "executor": """你是一个执行专家。根据任务计划和原始需求，逐步骤完成并输出完整的交付物。
要求：
1. 严格按照计划中的步骤执行
2. 输出完整、可直接使用的内容（不要省略，不要用"等"字）
3. 如果涉及中文写作，使用正式商务中文
4. 如果涉及分析，给出具体数据或依据
5. 标注信息来源（如果是基于已知知识还是推理）""",

    "reviewer": """你是一个质量审核专家。审核交付物是否满足以下标准：
1. 完整性：是否覆盖了所有要求
2. 准确性：信息是否准确、逻辑是否通顺
3. 可用性：是否可以直接使用，无需二次修改
4. 格式：是否符合要求的输出格式

输出格式（严格JSON）：
{
  "passed": true/false,
  "score": 0-100,
  "issues": ["问题1", "问题2"],
  "suggestions": ["修改建议1", "修改建议2"],
  "summary": "一句话总结审核结果"
}
passed 为 false 时，必须提供具体的 issues 和 suggestions。
passed 为 true 时，score 必须≥80，issue 可以为空。"""
}


def call_llm(client, model, system_prompt, user_message):
    """Call LLM and return response text."""
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.3,
    )
    return resp.choices[0].message.content


def decompose(client, model, task):
    """Agent 1: Decompose the task into steps."""
    print("\n" + "=" * 50)
    print("📋 分解者：正在拆解任务...")
    print("=" * 50)
    
    result = call_llm(client, model, SYSTEM_PROMPTS["decomposer"], task)
    
    try:
        plan = json.loads(result)
        print(f"  任务：{plan.get('task_name', '?')}")
        print(f"  步骤：{len(plan.get('steps', []))} 步")
        for i, s in enumerate(plan.get('steps', []), 1):
            print(f"    {i}. {s}")
        print(f"  交付格式：{plan.get('output_format', '?')}")
        return plan
    except json.JSONDecodeError:
        print(f"  (解析JSON失败，使用原始输出)")
        print(f"  {result[:300]}")
        return {"task_name": task, "steps": [result], "output_format": "文本"}


def execute(client, model, task, plan, iteration=1):
    """Agent 2: Execute the plan."""
    print("\n" + "=" * 50)
    print(f"✍️  执行者：正在执行任务 (第{iteration}轮)...")
    print("=" * 50)
    
    plan_str = json.dumps(plan, ensure_ascii=False, indent=2)
    user_msg = f"## 原始需求\n{task}\n\n## 执行计划\n{plan_str}\n\n请按计划逐步完成，输出完整的交付物。"
    
    result = call_llm(client, model, SYSTEM_PROMPTS["executor"], user_msg)
    
    preview = result[:200].replace("\n", " ")
    print(f"  完成，长度：{len(result)} 字符")
    print(f"  预览：{preview}...")
    return result


def verify(client, model, task, plan, draft, iteration=1, max_iterations=5):
    """Agent 3: Review quality, decide pass/fail."""
    print("\n" + "=" * 50)
    print(f"🔍 核查者：正在审核质量 (第{iteration}轮)...")
    print("=" * 50)
    
    user_msg = f"## 原始需求\n{task}\n\n## 交付物\n{draft}\n\n请严格审核，给出评分和修改意见。"
    
    result = call_llm(client, model, SYSTEM_PROMPTS["reviewer"], user_msg)
    
    try:
        review = json.loads(result)
        passed = review.get("passed", False)
        score = review.get("score", 0)
        issues = review.get("issues", [])
        suggestions = review.get("suggestions", [])
        
        print(f"  评分：{score}/100")
        print(f"  结论：{'✅ 通过' if passed else '❌ 不通过'}")
        
        if issues:
            print(f"  问题：")
            for issue in issues:
                print(f"    - {issue}")
        if suggestions:
            print(f"  建议：")
            for s in suggestions:
                print(f"    - {s}")
        
        if passed and score >= 80:
            return True, draft, review
        elif iteration >= max_iterations:
            print(f"\n  ⚠️ 已达最大循环次数 ({max_iterations})，强制交付当前版本")
            return True, draft, review
        else:
            # Return with feedback for next iteration
            feedback = "\n".join(suggestions) if suggestions else "\n".join(issues)
            return False, draft, {"feedback": feedback, **review}
    
    except json.JSONDecodeError:
        print(f"  (解析JSON失败，使用原始输出)")
        if "通过" in result and "80" not in result:
            return True, draft, {"score": 60}
        return True, draft, {"score": 60}


def run_workflow(client, model, task):
    """Full pipeline: decompose → execute → verify (loop)."""
    print("\n" + "🔥" * 20)
    print("  个人工作助手启动")
    print("🔥" * 20)
    print(f"\n任务：{task[:100]}{'...' if len(task) > 100 else ''}")
    
    # Phase 1: Decompose
    plan = decompose(client, model, task)
    
    # Phase 2-3: Execute → Verify (loop)
    max_iter = 5
    draft = ""
    
    for iteration in range(1, max_iter + 1):
        # Execute
        draft = execute(client, model, task, plan, iteration)
        
        # Verify
        passed, final_draft, review = verify(
            client, model, task, plan, draft, iteration, max_iter
        )
        
        if passed:
            draft = final_draft
            break
        else:
            # Add review feedback to plan for next iteration
            feedback = review.get("feedback", "")
            print(f"\n  📝 根据审核意见进行修改...")
            plan["_feedback"] = feedback
    
    # Output final result
    print("\n" + "=" * 50)
    print("✅ 最终交付物")
    print("=" * 50)
    print(draft)
    
    # Save to file
    safe_name = "".join(c for c in task[:30] if c.isalnum() or c in ' _-').strip()
    output_file = f"output_{safe_name or 'result'}.md"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(draft)
    print(f"\n📁 已保存至：{os.path.abspath(output_file)}")
    
    return draft


# ===== MAIN =====
if __name__ == "__main__":
    print("\n" + "#" * 50)
    print("#  CrewAI 风格个人工作助手")
    print("#  分解 → 执行 → 审核（循环）")
    print("#" * 50)
    print()
    
    # Initialize
    client, model = get_client()
    print(f"\n✅ 模型：{model}")
    print()
    
    while True:
        task = input("\n📝 输入你的任务（输入 q 退出）：\n> ").strip()
        
        if task.lower() in ('q', 'quit', 'exit'):
            print("\n再见！")
            break
        
        if not task:
            continue
        
        run_workflow(client, model, task)
        
        print("\n" + "-" * 40)
        again = input("\n继续下一个任务？(Enter=继续, q=退出): ").strip()
        if again.lower() == 'q':
            break
