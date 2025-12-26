import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="納品書管理アプリ", layout="wide")

st.title("📄 納品書データ化システム")
st.markdown("納品書PDFをアップロードすると、一覧表を作成してCSVでダウンロードできます。")

# データ抽出ロジック
def extract_data_from_pdf(file):
    data = {"注文ID": "", "注文日": "", "顧客名": "", "合計金額": "", "商品概要": "", "ファイル名": file.name}
    try:
        with pdfplumber.open(file) as pdf:
            page = pdf.pages[0]
            text = page.extract_text() or ""
            tables = page.extract_tables()

            # 注文ID
            id_match = re.search(r'注文ID:([A-Za-z0-9]+)', text)
            if id_match: data["注文ID"] = id_match.group(1)

            # 注文日
            date_match = re.search(r'注文日:(\d{4}/\d{1,2}/\d{1,2})', text)
            if date_match: data["注文日"] = date_match.group(1)

            # 顧客名（"お届け先:"の次行）
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if "お届け先:" in line and i + 1 < len(lines):
                    data["顧客名"] = lines[i+1].replace("様", "").strip()
                    break

            # 合計金額
            amount_match = re.search(r'合計金額\s*([¥\d,]+)', text)
            if amount_match: data["合計金額"] = amount_match.group(1)

            # 商品概要（表の1行目を取得）
            if tables:
                try:
                    # 荒竹様・森様のフォーマットに対応
                    first_item = tables[0][1][1] # 行1, 列1(商品名)
                    data["商品概要"] = first_item.split('\n')[0] # 改行があれば1行目のみ
                except:
                    pass
    except Exception as e:
        st.error(f"エラー: {file.name} - {str(e)}")
    
    return data

# アップローダー
uploaded_files = st.file_uploader("PDFファイルをここにドロップ", type="pdf", accept_multiple_files=True)

if uploaded_files:
    all_data = []
    for file in uploaded_files:
        all_data.append(extract_data_from_pdf(file))
    
    df = pd.DataFrame(all_data)
    
    if not df.empty:
        # 表示列の整理
        cols = ["注文日", "注文ID", "顧客名", "商品概要", "合計金額", "ファイル名"]
        # 存在しない列は除外して表示
        show_cols = [c for c in cols if c in df.columns]
        
        st.dataframe(df[show_cols], use_container_width=True)
        
        # CSVダウンロード
        csv = df[show_cols].to_csv(index=False).encode('utf-8_sig')
        st.download_button("CSVダウンロード", data=csv, file_name="invoice_list.csv", mime="text/csv")
