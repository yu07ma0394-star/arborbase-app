import streamlit as st
import pdfplumber
import pandas as pd
import re

# --- ページ設定 ---
st.set_page_config(page_title="納品書管理アプリ", layout="wide")

st.title("📄 納品書データ化システム")
st.markdown("PDFをアップロードすると、顧客名・住所・商品詳細（オプション含む）をすべて抽出します。")

# --- データ抽出ロジック（修正版） ---
def extract_data_from_pdf(file):
    # 初期値
    data = {
        "注文ID": "", 
        "注文日": "", 
        "顧客名": "", 
        "お届け先住所": "",
        "合計金額": "", 
        "商品詳細": "",
        "ファイル名": file.name
    }
    
    try:
        with pdfplumber.open(file) as pdf:
            page = pdf.pages[0]
            text = page.extract_text() or ""
            tables = page.extract_tables()

            # --- 1. 基本情報の抽出 ---
            # 注文ID
            id_match = re.search(r'注文ID:\s*([A-Za-z0-9]+)', text)
            if id_match: data["注文ID"] = id_match.group(1)

            # 注文日
            date_match = re.search(r'注文日:\s*(\d{4}/\d{1,2}/\d{1,2})', text)
            if date_match: data["注文日"] = date_match.group(1)

            # 合計金額
            amount_match = re.search(r'合計金額\s*([¥\d,]+)', text)
            if amount_match: data["合計金額"] = amount_match.group(1)

            # --- 2. 顧客名と住所の強力な抽出ロジック ---
            lines = text.split('\n')
            capture_mode = False
            captured_lines = []
            
            for line in lines:
                clean_line = line.strip()
                
                # 「お届け先」を見つけたら取り込み開始モードにする
                if "お届け先" in clean_line:
                    capture_mode = True
                    # もし「お届け先: 山田太郎」のように同じ行に名前がある場合への対応
                    content_after = clean_line.replace("お届け先", "").replace(":", "").strip()
                    if content_after:
                        captured_lines.append(content_after)
                    continue # 次の行へ
                
                if capture_mode:
                    # 終了条件のキーワード（これらが出たら住所エリア終了とみなす）
                    stop_keywords = ["Tel:", "Mail:", "請求先:", "購入金額:", "No.", "注文ID", "発送元:"]
                    if any(keyword in clean_line for keyword in stop_keywords):
                        capture_mode = False
                        break
                    
                    # 空行でなければリストに追加
                    if clean_line:
                        captured_lines.append(clean_line)
            
            # 拾った行を「名前」と「住所」に振り分け
            if captured_lines:
                # 1行目は確実に名前とみなす
                data["顧客名"] = captured_lines[0].replace("様", "").strip()
                
                # 2行目以降があれば、それをすべて結合して住所とする
                if len(captured_lines) > 1:
                    data["お届け先住所"] = " ".join(captured_lines[1:])

            # --- 3. 商品名の抽出 ---
            if tables:
                product_texts = []
                for table in tables:
                    for row in table:
                        # 行にデータがあり、かつ2列目が存在する場合
                        if row and len(row) > 1:
                            item_text = row[1]
                            # ヘッダー行や空行を除外
                            if item_text and "商品名" not in item_text:
                                product_texts.append(item_text)
                
                data["商品詳細"] = "\n".join(product_texts).strip()

    except Exception as e:
        # エラー時は画面に表示せずログに残す
        print(f"Error reading {file.name}: {e}")
    
    return data

# --- メイン画面の処理 ---
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
        
        st.success(f"{len(df)} 件のデータを抽出しました。")
        st.dataframe(df[show_cols], use_container_width=True)
        
        # CSVダウンロード
        csv = df[show_cols].to_csv(index=False).encode('utf-8_sig')
        st.download_button("CSVダウンロード", data=csv, file_name="invoice_list_full.csv", mime="text/csv")
