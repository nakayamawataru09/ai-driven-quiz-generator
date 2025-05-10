# generate.py

import openai
import json
import logging
import os
import uuid

# ロガー設定
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(h)

openai.api_key = os.getenv("OPENAI_API_KEY")

def generate_questions(certification: str, num: int, time_limit: int) -> str:
    prompt = (
        f"あなたはAWS認定試験の専門家です。以下の要件を満たすように、'{certification}' 試験向けの問題を{num}問生成してください。\n"
        "1. exam_info に category（文字列）と time_limit（例: '15 minutes'）を含める。\n"
        "2. questions は配列で、各要素は { id, question, choices, answer_index, explanation } を持つ。\n"
        "3. choices は必ず4つの選択肢を配列で持つ。\n"
        "4. answer_index は 0-3 の整数で正解を示す。\n"
        "5. explanation に簡潔な解説を含める。\n"
        "6. 全体を有効な JSON オブジェクトとして返す。"
    )
    resp = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[{"role":"user","content":prompt}],
        temperature=0.2,
        max_tokens=1200,
    )
    parsed = json.loads(resp.choices[0].message.content)
    for q in parsed.get("questions", []):
        if "id" not in q:
            q["id"] = str(uuid.uuid4())
    return json.dumps(parsed, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    print(generate_questions("AWS: Solutions Architect", 5, 15))
