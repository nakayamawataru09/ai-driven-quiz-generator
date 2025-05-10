import streamlit as st
import json
import time
from generate import generate_questions

# ページ設定
st.set_page_config(page_title="AWS クイズ", layout="centered")
st.title("AWS 認定試験 クイズ")

# --- JSON からクイズを読み込む機能 ---
st.sidebar.header("クイズ JSON 読込")
json_input = st.sidebar.text_area("ここにクイズの JSON を貼り付けてください:", height=250)
if st.sidebar.button("クイズ開始"):  # Load Quiz → クイズ開始
    try:
        data = json.loads(json_input)
        st.session_state.quiz_data = data
        # クイズ開始時刻と制限時間（秒）をセッションに保存
        st.session_state.start_time = time.time()
        # JSON の time_limit は "15 minutes" のような文字列なので数値を抽出
        minutes = int(''.join(filter(str.isdigit, data["exam_info"]["time_limit"])))
        st.session_state.time_limit_sec = minutes * 60
    except Exception as e:
        st.sidebar.error(f"JSON 読込エラー: {e}")

# --- クイズ画面 ---
if "quiz_data" in st.session_state:
    data = st.session_state.quiz_data
    exam = data["exam_info"]

    # タイマー
    timer_ph = st.empty()
    elapsed = time.time() - st.session_state.start_time
    remaining = int(st.session_state.time_limit_sec - elapsed)
    if remaining <= 0:
        timer_ph.markdown("**時間切れ！**")
        st.stop()
    else:
        mins, secs = divmod(remaining, 60)
        timer_ph.markdown(f"**残り時間: {mins:02d}分{secs:02d}秒**")

    st.subheader("試験情報")
    st.markdown(f"- カテゴリ: **{exam['category']}**  
- 制限時間: **{exam['time_limit']}**")
    st.markdown("---")

    st.subheader("問題")
    for q in data.get("questions", []):
        st.markdown(f"**Q: {q['question']}**")
        for idx, choice in enumerate(q["choices"]):
            st.write(f"{idx + 1}. {choice}")  # 1始まり表示
        if st.button(f"解答を見る (Q{q['id']})", key=q['id']):
            correct = q['choices'][q['answer_index']]
            st.success(f"正解: {correct}")
            st.info(q['explanation'])
        st.markdown("---")

# --- 問題生成機能 ---
st.sidebar.markdown("---")
st.sidebar.header("問題を自動生成")
# プルダウンで試験カテゴリを選択
exam_options = ["AWS: Solutions Architect", "AWS: Developer", "AWS: SysOps Administrator"]
cert = st.sidebar.selectbox("認定試験を選択:", exam_options)
q_num = st.sidebar.number_input("問題数:", min_value=1, max_value=100, value=5)
time_limit = st.sidebar.number_input("制限時間(分):", min_value=1, max_value=60, value=15)
if st.sidebar.button("問題を生成"):  # Generate Questions → 問題を生成
    try:
        json_str = generate_questions(cert, q_num, time_limit)
        st.sidebar.success("問題を生成しました。上部の JSON 入力欄に貼り付けて［クイズ開始］を押してください。")
        st.sidebar.code(json_str)
    except Exception as e:
        st.sidebar.error(f"生成エラー: {e}")
