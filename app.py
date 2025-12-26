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
                else:
                    # もし2行目が取れていなければ、郵便番号抽出などを試みる（予備策）
                    pass

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
        # エラー時は画面に表示せずログに残す（空データとして返す）
        print(f"Error reading {file.name}: {e}")
    
    return data
