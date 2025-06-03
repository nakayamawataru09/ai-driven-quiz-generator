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

def generate_questions(exam_id, exam_name, q_num=5):
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
  explanation: 解説（日本語、300字以内）どの選択肢が正解かを明確に示してください。
形式：
{{"questions":[{{…}},…]}}
試験情報：
- 試験ID: {exam_id}
"""
    res = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1500
    )
    return res.choices[0].message.content

st.title("Certify")

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
    
    generate_button = st.button("問題生成", type="primary")

# セッション状態の初期化
if 'questions' not in st.session_state:
    st.session_state.questions = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 0
if 'questions_per_page' not in st.session_state:
    st.session_state.questions_per_page = 3
if 'review_flags' not in st.session_state:
    st.session_state.review_flags = {}

# メインコンテンツエリア
if generate_button:
    with st.spinner("AIで問題を生成中…"):
        json_str = generate_questions(
            selected_exam["exam_id"],
            selected_exam["exam_name"],
            q_num=5
        )
        # 生成した問題をセッション状態に保存
        st.session_state.questions = json.loads(json_str)
        st.session_state.current_page = 0  # ページをリセット

# 問題の表示（セッション状態から）
if st.session_state.questions:
    questions = st.session_state.questions["questions"]
    total_pages = (len(questions) + st.session_state.questions_per_page - 1) // st.session_state.questions_per_page
    
    # 現在のページの問題を表示
    start_idx = st.session_state.current_page * st.session_state.questions_per_page
    end_idx = min(start_idx + st.session_state.questions_per_page, len(questions))
    
    for q in questions[start_idx:end_idx]:
        st.markdown(f"**Q. {q['question']}**")
        
        # 選択肢を表示（デフォルト選択なし）
        selected_choice = st.radio("", q["choices"], key=f"{q['id']}", index=None)
        
        # 選択された場合のみ回答を表示
        if selected_choice:
            selected_index = q["choices"].index(selected_choice)
            is_correct = selected_index == q["answer_index"]
            
            # 正解/不正解の表示
            if is_correct:
                st.success("正解です！")
            else:
                st.error(f"不正解です。正解は: {q['choices'][q['answer_index']]}")
            
            # 解説は折りたたみ
            with st.expander("解説"):
                st.write(q["explanation"])
        
        st.markdown("---")  # 問題間の区切り線
    
    # ページネーションコントロール
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"**ページ {st.session_state.current_page + 1} / {total_pages}**")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.session_state.current_page > 0:
            if st.button("前へ"):
                st.session_state.current_page -= 1
                st.rerun()
    with col3:
        if st.session_state.current_page < total_pages - 1:
            if st.button("次へ"):
                st.session_state.current_page += 1
                st.rerun()
