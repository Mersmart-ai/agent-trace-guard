from pathlib import Path
import os
from openai import OpenAI
from dotenv import load_dotenv

# .env 在项目根目录，不在 fbs/ 里
load_dotenv(Path(__file__).parent.parent / ".env")


class OutOfCredit(Exception):
    """API 余额不足。

    这不是"任务失败"，是整个批次该停了——继续跑，每个任务都会报 402，
    跑满 max_turns，产出几十条垃圾 trace，和"模型不会做"混在一起分不清。
    """


def call_model(messages,tools=None,model="deepseek-flash",thinking_off=False):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("请先在 .env 里填写 DEEPSEEK_API_KEY")
    client=OpenAI(api_key=api_key,base_url="https://api.deepseek.com")
    #发起HTTP请求
    kwargs = dict(model=model, messages=messages, temperature=0, tools=tools)
    if thinking_off:
        #思考模式下 API 要求把上一轮的 reasoning_content 原样回传，
        #而 SDK 的 model_dump() 里取不到它，多轮对话就会 400；关掉才能走标准对话
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}
    try:
        response=client.chat.completions.create(**kwargs)
    except Exception as e:
        # 402 / Insufficient Balance 说明是钱的问题，不是能力的问题
        if getattr(e, "status_code", None) == 402 or "Insufficient Balance" in str(e):
            raise OutOfCredit(str(e)) from e
        raise
    return response.choices[0].message
if __name__ == "__main__":
    print(call_model([{"role": "user", "content": "只回复 OK"}]).content)
