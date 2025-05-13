# 試験情報をDynamoDBに保存する
import os
import boto3
from datetime import datetime
import streamlit as st
import json

# Streamlit SecretsからAWS認証情報を取得
aws_access_key_id = st.secrets["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = st.secrets["AWS_SECRET_ACCESS_KEY"]
aws_region = st.secrets["AWS_DEFAULT_REGION"]

# DynamoDBリソース初期化
dynamodb = boto3.resource(
    "dynamodb",
    region_name=aws_region,
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key
)
table = dynamodb.Table("ExamInfo")

st.title("DynamoDB 試験情報 登録・取得アプリ")

# JSON入力欄
st.markdown("itemのJSONを下に貼り付けて編集できます。")
item_json = st.text_area(
    "itemのJSON",
    height=400,
    value="""{
  "PK": "EXAM#SAA-C02",
  "SK": "META",
  "exam_id": "SAA-C02",
  "exam_name": "AWS Certified Solutions Architect – Associate"
}"""
)

col1, col2 = st.columns(2)

with col1:
    if st.button("DynamoDBに登録"):
        try:
            item = json.loads(item_json)
            table.put_item(Item=item)
            st.success("DynamoDBに登録しました！")
        except Exception as e:
            st.error(f"登録に失敗しました: {e}")

with col2:
    st.markdown("#### PKとSKを指定してDynamoDBから取得")
    pk = st.text_input("PK", value="EXAM#SAA-C02")
    sk = st.text_input("SK", value="META")
    if st.button("最新の登録内容を取得"):
        try:
            response = table.get_item(Key={"PK": pk, "SK": sk})
            item = response.get("Item")
            if item:
                st.code(json.dumps(item, ensure_ascii=False, indent=2), language="json")
            else:
                st.warning("該当データが見つかりませんでした。")
        except Exception as e:
            st.error(f"取得に失敗しました: {e}")
