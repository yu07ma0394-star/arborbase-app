import streamlit as st
import pdfplumber
import pandas as pd
import re
import io

st.set_page_config(page_title="納品書管理アプリ", layout="wide")

st.title("📄 納品書データ化システム")
st.markdown("納品書PDFをアップロードすると、詳細情報（住所・商品オプション含む）を抽出します。")

# データ抽出ロジック
def extract_data_from_pdf(file):
    # 初期値
    data = {
        "注文ID": "", 
        "注文日": "", 
        "顧客名": "", 
        "お届け先住所": "",  # 追加
        "合計金額": "", 
        "商品詳細": "",      # 変更（全テキスト）
        "ファイル名": file.name
    }
    
    try:
        with pdfplumber.open(file) as pdf:
            page = pdf.pages[0]
            text = page.extract_text() or ""
            tables = page.extract_tables()

            # --- 1. 基本情報の抽出 ---
            
            # 注文ID
            id_match = re.search(r'注文ID:([A-Za-z0-9]+)', text)
            if id_match: data["注文ID"] = id_match.group(1)

            # 注文日
            date_match = re.search(r'注文日:(\d{4}/\d{1,2}/\d{1,2})', text)
            if date_match: data["注文日"] = date_match.group(1)

            # 合計金額
            amount_match = re.search(r'合計金額\s*([¥\d,]+)', text)
            if amount_match: data["合計金額"] = amount_match.group(1)

            # --- 2. 顧客名と住所の抽出 ---
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if "お届け先:" in line and i + 1 < len(lines):
                    # お届け先: の次の行は「名前」
                    data["顧客名"] = lines[i+1].replace("様", "").strip()
                    
                    # その次の行から「Tel:」または「Mail:」が出るまでを「住所」とする
                    address_lines = []
                    for j in range(i + 2, len(lines)):
                        check_line = lines[j]
                        if "Tel:" in check_line or "Mail:" in check_line or "請求先:" in check_line:
                            break
                        address_lines.append(check_line.strip())
                    
                    data["お届け先住所"] = " ".join(address_lines)
                    break

            # --- 3. 商品名の抽出（小文字・オプション含む） ---
            if tables:
                product_texts = []
                for table in tables:
                    # ヘッダー行("商品名"が含まれる行)をスキップする簡易ロジック
                    for row in table:
                        # 行の2列目（インデックス1）が商品名と仮定
                        if len(row) > 1:
                            item_text = row[1] # 商品名列
                            
                            # Noneチェック と ヘッダー除外
                            if item_text and "商品名" not in item_text:
                                # 改行を維持するか、スペースで繋ぐか（ここでは見やすく改行を維持）
                                product_texts.append(item_text)
                
                # リストを結合して一つの文字列にする
                data["商品詳細"] = "\n".join(product_texts).strip()

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
        # 表示列の指定（並び順）
        cols = ["注文日", "注文ID", "顧客名", "お届け先住所", "商品詳細", "合計金額", "ファイル名"]
        
        # 存在しない列は除外して表示
        show_cols = [c for c in cols if c in df.columns]
        
        # テーブル表示（高さを自動調整して全文が見えるように設定などはStreamlitの仕様による）
        st.dataframe(df[show_cols], use_container_width=True)
        
        # CSVダウンロード
        csv = df[show_cols].to_csv(index=False).encode('utf-8_sig')
        st.download_button("CSVダウンロード", data=csv, file_name="invoice_list_full.csv", mime="text/csv")
