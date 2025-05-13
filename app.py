import os
import streamlit as st
from openai import OpenAI
import uuid
import json
import boto3
import datetime

# Secretsから取得
aws_access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
aws_region = st.secrets["AWS_DEFAULT_REGION"]
openai_api_key = st.secrets["OPENAI_API_KEY"]

# boto3の初期化
dynamodb = boto3.resource(
    'dynamodb',
    region_name=aws_region,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)

# OpenAIの初期化
client = OpenAI(api_key=openai_api_key)

exam_info_table = dynamodb.Table('ExamInfo')

def default_json(obj):
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()
    return str(obj)

def get_all_exam_categories():
    """
    PKが'EXAM#'で始まり、SK='META'の全試験カテゴリを取得
    """
    try:
        response = exam_info_table.scan(
            FilterExpression="begins_with(PK, :pk) AND SK = :sk",
            ExpressionAttributeValues={
                ":pk": "EXAM#",
                ":sk": "META"
            },
            ProjectionExpression="exam_id, exam_name"
        )
        return [
            {"exam_id": item["exam_id"], "exam_name": item["exam_name"]}
            for item in response.get("Items", [])
        ]
    except Exception as e:
        st.error(f"試験カテゴリの取得に失敗しました: {e}")
        return []

def get_exam_info(exam_id):
    """
    PK/SKで試験メタ情報を取得
    """
    try:
        response = exam_info_table.get_item(
            Key={"PK": f"EXAM#{exam_id}", "SK": "META"}
        )
        return response.get("Item", {})
    except Exception as e:
        st.error(f"試験情報の取得に失敗しました: {e}")
        return {}

def generate_questions(exam_id, exam_name, q_num, time_limit):
    """
    AI にプロンプトを投げて JSON 形式で問題リストを取得する
    """
    exam_info = get_exam_info(exam_id)
    prompt = f"""
以下の試験情報に沿って、{q_num}問の日本語の択一式問題をJSONで生成してください。
絶対に説明や補足を加えず、JSONのみを出力してください。
また試験の難易度や出題傾向、問題文章量等のポイントを調べた上で問題を生成してください。

試験名: {exam_name}
試験の詳細情報:
{json.dumps(exam_info, ensure_ascii=False, indent=2, default=default_json)}

各問題オブジェクトは
  id: 一意のUUID文字列
  question: 問題文（日本語）
  choices: 選択肢リスト（4つ、日本語）
  answer_index: 正解の選択肢インデックス(0–3)
  explanation: 解説（日本語、50–100字）
形式：
{{"questions":[{{…}},…]}}
試験情報：
- 試験ID: {exam_id}
- 制限時間: {time_limit}分
"""
    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500
    )
    return res.choices[0].message.content

st.title("資格試験問題つくるん")

# サイドバーに設定を移動
with st.sidebar:
    st.header("試験設定")
    
    # DynamoDBから試験カテゴリを取得
    exam_categories = get_all_exam_categories()
    if not exam_categories:
        st.error("試験カテゴリが見つかりません。DynamoDBに試験情報を登録してください。")
        st.stop()
    
    # exam_nameのみのリストを作成
    exam_names = [item['exam_name'] for item in exam_categories]
    selected_exam_name = st.selectbox("試験カテゴリ", exam_names)
    # 選択されたexam_nameからexam_idを取得
    selected_exam = next(item for item in exam_categories if item['exam_name'] == selected_exam_name)
    q_num = st.number_input("問題数", min_value=5, max_value=50, value=10, step=5)
    time_limit = st.number_input("制限時間（分）", min_value=5, max_value=60, value=20, step=5)
    generate_button = st.button("問題生成", type="primary")

# メインコンテンツエリア
if generate_button:
    with st.spinner("AIで問題を生成中…"):
        json_str = generate_questions(
            selected_exam["exam_id"],
            selected_exam["exam_name"],
            q_num,
            time_limit
        )
    # 取得した JSON をパースして表示
    try:
        data = json.loads(json_str)  # JSON文字列をパース
        for q in data["questions"]:
            st.markdown(f"**Q. {q['question']}**")
            for idx, c in enumerate(q["choices"]):
                st.radio("", c, key=f"{q['id']}_{idx}")
            # 解説は折りたたみ
            with st.expander("解説"):
                st.write(q["explanation"])
    except Exception as e:
        st.error(f"JSONパースエラー: {e}")
