import streamlit as st
import pandas as pd
import datetime
import re

st.set_page_config(page_title="履約進度追蹤系統", layout="wide")
st.title("📊 履約管理主控系統")

# ---------- 上傳履約時程表 ----------
st.header("📥 步驟一：上傳履約時程表")
uploaded = st.file_uploader("請上傳事先清理好的 Excel 或 CSV 履約表格：", type=["csv", "xlsx"])

if "sign_date" not in st.session_state:
    st.session_state["sign_date"] = datetime.date.today()
if "award_date" not in st.session_state:
    st.session_state["award_date"] = datetime.date.today()

if uploaded:
    if uploaded.name.endswith(".csv"):
        df = pd.read_csv(uploaded)
    else:
        df = pd.read_excel(uploaded)

    st.header("📅 步驟二：輸入起算基準日")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state["sign_date"] = st.date_input("簽約日", st.session_state["sign_date"])
    with col2:
        st.session_state["award_date"] = st.date_input("決標日", st.session_state["award_date"])

    # ---------- 自動計算應交日期 ----------
    def compute_due(row):
        base = st.session_state["sign_date"] if row["起算基準"] == "簽約日" else st.session_state["award_date"]
        try:
            return base + datetime.timedelta(days=int(row["天數"]))
        except:
            return ""

    df["應交日期"] = df.apply(compute_due, axis=1)

    # ---------- 自動更新狀態欄 ----------
    def check_status(row):
        if not isinstance(row["應交日期"], datetime.date):
            return "--"
        if pd.notna(row["核定日"]):
            return "✅ 已核定"
        elif pd.notna(row["提送日"]):
            return "📤 已送出" if row["提送日"] <= row["應交日期"] else "⚠️ 逾期送出"
        else:
            return "⏳ 未提送" if datetime.date.today() <= row["應交日期"] else "❌ 逾期未送"

    df["狀態"] = df.apply(check_status, axis=1)

    # ---------- 顯示資料表 ----------
    st.header("📋 步驟三：履約時程概覽")
    st.dataframe(df, use_container_width=True)

    # ---------- 步驟四：自然語句更新進度 ----------
    st.header("💬 步驟四：輸入履約進度語句")
    input_text = st.text_input("請輸入如『我3/12送出期中報告』、『4月2日核定期末設計』等語句：")

    if input_text:
        action = "提送日" if any(k in input_text for k in ["送", "提交", "提"]) else ("核定日" if "核" in input_text or "通過" in input_text else None)
        date_match = re.search(r"(\d{1,2})[月/\.]?(\d{1,2})日?", input_text)
        item_match = next((item for item in df["工作項目"] if item in input_text), None)

        if action and date_match and item_match:
            month, day = map(int, date_match.groups())
            year = datetime.date.today().year
            parsed_date = datetime.date(year, month, day)
            df.loc[df["工作項目"] == item_match, action] = parsed_date
            st.success(f"✅ 已更新『{item_match}』的{action}為 {parsed_date}")

            # 重新運算狀態欄
            df["狀態"] = df.apply(check_status, axis=1)
            st.dataframe(df, use_container_width=True)
        else:
            st.warning("⚠️ 無法從語句判斷日期或對應項目")

    # ---------- 可匯出 Excel ----------
    st.download_button("⬇️ 匯出更新後履約表", df.to_csv(index=False).encode("utf-8-sig"), file_name="履約追蹤更新表.csv")
else:
    st.info("請先上傳清理好的履約主控表，欄位需包含：工作項目、契約依據、起算基準、天數、提送日、核定日。")
