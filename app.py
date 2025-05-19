import streamlit as st
import pandas as pd
import datetime
import json
import re
from io import BytesIO
from PyPDF2 import PdfReader
from openai import OpenAI

st.set_page_config(page_title="AI 履約助手", layout="wide")
st.title("📄 AI 契約清理 + 履約進度更新 系統")

# --------- 功能區塊 1：上傳契約 ----------
st.header("📤 步驟一：上傳契約 PDF")
uploaded_file = st.file_uploader("請上傳契約 PDF 檔案", type=["pdf"])
contract_text = ""

if uploaded_file:
    pdf_stream = BytesIO(uploaded_file.read())
    reader = PdfReader(pdf_stream)
    contract_text = "\n".join(page.extract_text() for page in reader.pages if page.extract_text())

    st.success("✅ 契約上傳成功，共讀取 {} 字元".format(len(contract_text)))

    with st.expander("查看部分契約內容"):
        st.text_area("契約文字內容", contract_text[:3000], height=300)

# --------- 功能區塊 2：輸入起算日 ----------
st.header("🗓️ 步驟二：輸入起算基準日")
col1, col2 = st.columns(2)
with col1:
    sign_date = st.date_input("簽約日", value=datetime.date.today())
with col2:
    award_date = st.date_input("決標日", value=datetime.date.today())

# --------- GPT 履約交辦項目解析 ----------
st.header("📋 步驟三：預覽交辦事項與推算期程")

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

def gpt_extract_deliverables(contract_text):
    prompt = f"""
你是一個工程契約分析助手，請根據以下契約內容，找出乙方需要交付的所有項目與期限，格式請用 JSON 陣列輸出，每筆格式如下：
{{
  "工作項目": "期中報告",
  "契約依據": "第七條第2款",
  "期程文字": "簽約日後30日內",
  "起算基準": "簽約日",
  "天數": 30
}}
請注意：
1. 每個項目請用合約內的原文作為「工作項目」
2. 如果時間沒寫明天數，可以只填「期程文字」其餘空白
3. 結果請直接回傳 JSON 陣列，不要加說明文字
以下是契約全文：
```
{contract_text[:5000]}
```
    """
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    raw = response.choices[0].message.content.strip()
    try:
        data = json.loads(raw)
        return data
    except Exception as e:
        return [{"工作項目": "解析失敗", "契約依據": "", "期程文字": raw, "錯誤": str(e)}]

if contract_text:
    with st.spinner("🔍 GPT 正在解析契約條文，請稍候..."):
        gpt_data = gpt_extract_deliverables(contract_text)

    df = pd.DataFrame(gpt_data)
    if "天數" in df.columns:
        df["應提送日期"] = df["天數"].apply(lambda d: sign_date + pd.to_timedelta(d, unit="D") if isinstance(d, int) else "")
    st.dataframe(df, use_container_width=True)

    csv = df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("⬇️ 下載履約主控表（GPT解析）", csv, file_name="履約主控表.csv", mime="text/csv")
else:
    st.info("📎 請上傳契約並擷取交辦條款後，自動生成交辦列表")

# --------- 功能區塊 4：自然語句進度輸入 ----------
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

