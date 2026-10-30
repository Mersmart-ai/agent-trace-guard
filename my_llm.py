from pathlib import Path
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name(".env"))
def call_model(messages,tools=None,model="deepseek-flash"):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise SystemExit("请先在 .env 里填写 DEEPSEEK_API_KEY")
    client=OpenAI(api_key=api_key,base_url="https://api.deepseek.com")
    #发起HTTP请求
    response=client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
        tools=tools,
    )
    return response.choices[0].message
if __name__ == "__main__":
    print(call_model([{"role": "user", "content": "只回复 OK"}]).content)
