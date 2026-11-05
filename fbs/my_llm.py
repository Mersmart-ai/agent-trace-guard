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


# 两个后端，都是 OpenAI 兼容接口，切换只改 base_url 和 key
BACKENDS = {
    "deepseek": {
        "base_url": "https://api.deepseek.com",
        "env": "DEEPSEEK_API_KEY",
        "model": "deepseek-flash",
        "thinking_body": True,      # 支持 extra_body 关思考
    },
    "dashscope": {
        "base_url": "https://dashscope.aliyuncs.com/compatible-mode/v1",
        "env": "DASHSCOPE_API_KEY",
        "model": "qwen3.8-flash",
        "thinking_body": False,
    },
}

# 用哪个后端。默认 dashscope（因为现在要测 7B）。
# 想换回来：FBS_BACKEND=deepseek python run.py
BACKEND = os.environ.get("FBS_BACKEND", "deepseek")

# 用哪个模型。不给就用后端自己的默认值。
# 换模型：FBS_MODEL=qwen-plus python run.py
MODEL = os.environ.get("FBS_MODEL", "deepseek-chat")


def _client():
    cfg = BACKENDS.get(BACKEND)
    if cfg is None:
        raise SystemExit(f"不认识的后端：{BACKEND}，可选：{list(BACKENDS)}")
    api_key = os.environ.get(cfg["env"])
    if not api_key:
        raise SystemExit(f"请先在 .env 里填写 {cfg['env']}")
    return OpenAI(api_key=api_key, base_url=cfg["base_url"]), cfg


def call_model(messages, tools=None, model=None, thinking_off=False):
    client, cfg = _client()
    kwargs = dict(model=model or MODEL, messages=messages, temperature=0, tools=tools)

    if thinking_off and cfg["thinking_body"]:
        # 思考模式下 API 要求把上一轮的 reasoning_content 原样回传，
        # 而 SDK 的 model_dump() 里取不到它，多轮对话就会 400；关掉才能走标准对话
        kwargs["extra_body"] = {"thinking": {"type": "disabled"}}

    try:
        response = client.chat.completions.create(**kwargs)
    except Exception as e:
        msg = str(e)
        # 钱的问题，不是能力的问题
        if getattr(e, "status_code", None) == 402 or "Insufficient Balance" in msg \
                or "quota" in msg.lower() or "arrearage" in msg.lower():
            raise OutOfCredit(msg) from e
        raise
    return response.choices[0].message


if __name__ == "__main__":
    print(f"后端: {BACKEND}   模型: {MODEL}")
    print(call_model([{"role": "user", "content": "只回复 OK"}]).content)
