import os
import streamlit as st
from openai import OpenAI
import uuid
import json

# OpenAI APIキー設定（環境変数OPENAI_API_KEY）
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def generate_questions(cert: str, q_num: int, time_limit: int):
    """
    AI にプロンプトを投げて JSON 形式で問題リストを取得する。
    各問題：{id, question, choices:[…], answer_index, explanation}
    """
    prompt = f"""
以下の試験情報に沿って、{q_num}問の択一式問題をJSONで生成してください。
各問題オブジェクトは
  id: 一意のUUID文字列
  question: 問題文
  choices: 選択肢リスト（4つ）
  answer_index: 正解の選択肢インデックス(0–3)
  explanation: 解説（50–100字）
形式：
{{"questions":[{{…}},…]}}
試験情報：
- 試験カテゴリ: {cert}
- 制限時間: {time_limit}分
"""
    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role":"user","content":prompt}],
        temperature=0.7,
        max_tokens=1500
    )
    content = res.choices[0].message.content
    return content  # JSON文字列

st.title("資格模擬試験 — 問題生成")

cert = st.selectbox("試験カテゴリ", ["AWS: Solutions Architect", "GCP: Data Engineer"])
q_num = st.number_input("問題数", min_value=5, max_value=50, value=10, step=5)
time_limit = st.number_input("制限時間（分）", min_value=5, max_value=60, value=20, step=5)

if st.button("問題生成"):
    with st.spinner("AIで問題を生成中…"):
        json_str = generate_questions(cert, q_num, time_limit)
    # 取得した JSON をパースして表示
    try:
        data = json.loads(json_str)  # JSON文字列をパース
        st.json(data)  # JSONデータを表示
        for q in data["questions"]:
            st.markdown(f"**Q. {q['question']}**")
            for idx, c in enumerate(q["choices"]):
                st.radio("", c, key=f"{q['id']}_{idx}")
            # 解説は折りたたみ
            with st.expander("解説"):
                st.write(q["explanation"])
    except Exception as e:
        st.error(f"JSONパースエラー: {e}")
