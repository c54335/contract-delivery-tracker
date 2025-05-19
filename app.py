import streamlit as st
import pandas as pd
import datetime
from io import StringIO
from PyPDF2 import PdfReader
import re

st.set_page_config(page_title="AI 履約助手", layout="wide")
st.title("📄 AI 契約清理 + 履約進度更新 系統")

# --------- 功能區塊 1：上傳契約 ----------
st.header("📤 步驟一：上傳契約 PDF")
uploaded_file = st.file_uploader("請上傳契約 PDF 檔案", type=["pdf"])
contract_text = ""

if uploaded_file:
    reader = PdfReader(uploaded_file)
    contract_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())
    st.success("✅ 契約上傳成功，共讀取 {} 字元".format(len(contract_text)))
    
    # 顯示部分原文
    with st.expander("查看部分契約內容"):
        st.text_area("契約文字內容", contract_text[:3000], height=300)

# --------- 功能區塊 2：輸入起算日 ----------
st.header("🗓️ 步驟二：輸入起算基準日")
col1, col2 = st.columns(2)
with col1:
    sign_date = st.date_input("簽約日", value=datetime.date.today())
with col2:
    award_date = st.date_input("決標日", value=datetime.date.today())

# --------- 功能區塊 3：契約條文自動擷取（樣板） ----------
def extract_deliverables(text):
    pattern = r"第[一二三四五六七八九十]+條[\s\S]{0,20}?乙方[\s\S]{0,150}?須[於在]?[\s\S]{0,100}?(\d{1,3})[日天]內"
    matches = re.findall(pattern, text)
    return [f"乙方須於 {day} 日內交付項目" for day in matches]

deliverables = extract_deliverables(contract_text) if contract_text else []

# --------- 功能區塊 4：預覽時程表格 ----------
st.header("📋 步驟三：預覽交辦事項與推算期程")
if deliverables:
    df = pd.DataFrame({
        "工作項目": deliverables,
        "契約起算日": sign_date,
        "契約規定天數": [int(re.findall(r'(\d+)', d)[0]) for d in deliverables],
    })
    df["應提送日"] = df["契約起算日"] + pd.to_timedelta(df["契約規定天數"], unit="D")
    st.dataframe(df, use_container_width=True)

    # 匯出 CSV
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="⬇️ 下載履約主控表 CSV",
        data=csv,
        file_name="履約主控表.csv",
        mime="text/csv",
    )
else:
    st.info("📎 請上傳契約並擷取期程條款後，自動生成交辦列表")

# --------- 功能區塊 5：自然語句進度輸入 ----------
st.header("💬 步驟四：輸入進度語句來自動回填")
user_sentence = st.text_input("請輸入類似『我3/15送出期中報告』、『3/20已核定期末設計』等語句：")

if user_sentence:
    action = "提送" if any(k in user_sentence for k in ["送", "提交", "交", "提"]) else ("核定" if "核" in user_sentence or "通過" in user_sentence else "")
    date_match = re.search(r"(\d{1,2})[\/\.月](\d{1,2})", user_sentence)
    if action and date_match:
        month, day = map(int, date_match.groups())
        year = datetime.date.today().year
        roc_date = f"{year - 1911}.{month:02d}.{day:02d}"
        st.success(f"✅ 系統辨識為：{action}日 → {roc_date}")
    else:
        st.warning("⚠️ 無法從語句判斷日期或提送/核定行為")
