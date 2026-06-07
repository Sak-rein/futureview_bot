import io
import os
from PIL import Image, ImageDraw, ImageFont

# ─── 🎛️ 模擬 Google 試算表回傳的資料 ───
# 你可以在這裡自由改動文字或圖片檔名，測試不同資料長度下的排版外觀
MOCK_DATA = {
    '期數': '321',
    '模式': 'Medley',
    '開活日': '06/06',
    '結活日': '06/15',
    '活動名稱': '輝きを抱くステラ',
    'logo':'PoppinParty',
    'banner':'banner_321',      # 對應 assets/banner/banner_314.png
    '屬性': 'POWERFUL',          # 對應 assets/frame/powerful.png
    '出場角色': 'saaya,kasumi,rimi,arisa,tae',  # 模擬大頭貼清單
    '頂艦': 'saaya_321,kasumi_321,rimi_321,arisa_321,tae_321'    # 模擬 5 張頂艦卡片
}

def generate_preview_image(row_data):
    """
    完全複製自你的 Cog 繪圖邏輯。
    調整此處的 X, Y 座標、尺寸與間距，即可即時看到排版變化！
    """
    
    # 📐 畫布寬高：(寬度, 高度) -> 目前設定為 850 * 400 像素
    canvas_w, canvas_h = 850, 520 
    
    # 🎨 建立空白畫布，底色為純白 (RGBA 255, 255, 255, 255)
    canvas = Image.new("RGBA", (canvas_w, canvas_h), color=(255, 255, 255, 255))
    draw = ImageDraw.Draw(canvas)
    
    # 🔤 字體路徑偵測與大小設定
    font_paths = ["C:\\Windows\\Fonts\\msjh.ttc", "msjh.ttc", "assets/fonts/msjh.ttc"]
    font_main, font_title = None, None
    for path in font_paths:
        if os.path.exists(path):
            try:
                # 參數解釋：ImageFont.truetype(字型路徑, 字體大小像素)
                font_main = ImageFont.truetype(path, 18)   # 內文字體大小 (18)
                font_title = ImageFont.truetype(path, 18)  # 活動名稱字體大小 (18)
                break
            except: continue
    if font_main is None:
        font_main = ImageFont.load_default()
        font_title = ImageFont.load_default()

    # 🖼️ 1. Banner 區塊排版
    banner_name = str(row_data.get('banner', '')).strip()
    banner_path = f"assets/banner/{banner_name}.png"
    if banner_name and os.path.exists(banner_path):
        banner_img = Image.open(banner_path).convert("RGBA")
        
        # ⚠️ 參數解釋：.resize((新寬度, 新高度))
        # 你的代碼中把高度改成了 280，寬度拉滿 850（會蓋到下方的 Y=180~260 區塊）
        banner_img = banner_img.resize((canvas_w, 280)) 
        
        # ⚠️ 參數解釋：.paste(要貼的圖, (X座標, Y座標), 透明遮罩圖層)
        canvas.paste(banner_img, (0, 0), banner_img)
    else:
        # 若無 Banner 圖片，畫一個灰色矩形墊底：[左上X, 左上Y, 右下X, 右下Y]
        draw.rectangle([0, 0, canvas_w, 230], fill=(220, 220, 220))
        draw.text((canvas_w//2 - 80, 100), "( 暫無 Banner 圖片 )", fill=(100, 100, 100), font=font_main)

    # 📏 2. 表格格線繪製
    # 參數解釋：draw.line([(起點X, 起點Y), (終點X, 終點Y)], fill=(RGB顏色), width=線條粗細)
    draw.line([(0, 285), (canvas_w, 285)], fill=(0, 0, 0), width=2) # 頂部粗橫線
    draw.line([(0, 320), (canvas_w, 320)], fill=(0, 0, 0), width=1) # 中間細橫線
    draw.line([(0, 380), (canvas_w, 380)], fill=(0, 0, 0), width=2) # 下方粗橫線

    # 3. 提取文字與日期欄位
    period = row_data.get('期數', '')
    mode = row_data.get('模式', '')
    start_d = row_data.get('開活日', '')
    end_d = row_data.get('結活日', '')
    title = row_data.get('活動名稱', '')

    # ✍️ 4. 第一層文字區塊排版
    # 參數解釋：draw.text((文字起始X, 文字起始Y), "文字內容", fill=(R,G,B色), font=字型物件)
    draw.text((45, 303), f"{period} ", fill=(0, 0, 0), font=font_main, anchor="mm")
    draw.text((110, 303), f"{mode} ", fill=(0, 0, 0), font=font_main, anchor="mm")
    draw.line([(158, 320.5), (158, 285)], fill=(200, 200, 200), width=2) # 縱向直條分隔線
    
    draw.text((220, 303), f"{start_d}", fill=(0, 0, 0), font=font_main, anchor="mm")
    draw.line([(288, 320.5), (288, 285)], fill=(200, 200, 200), width=2) # 縱向直條分隔線
    
    draw.text((355, 303), f"{end_d}", fill=(0, 0, 0), font=font_main, anchor="mm")
    draw.line([(423, 320.5), (423, 285)], fill=(200, 200, 200), width=2) # 縱向直條分隔線

    draw.text((637, 303), f"{title}", fill=(27, 38, 59), font=font_title, anchor="mm") # 活動名稱

    # 🌟 5. 屬性球位置排版
    attr_name = str(row_data.get('屬性', '')).lower().strip()
    attr_path = f"assets/attribute/{attr_name}.png"
    if os.path.exists(attr_path):
        # 縮放屬性球尺寸
        attr_img = Image.open(attr_path).convert("RGBA").resize((100, 100))
    
        canvas.paste(attr_img, (30, 400), attr_img)
    
    # 樂隊logo
    logo_name = str(row_data.get('logo', '')).lower().strip()
    logo_path = f"assets/logos/{logo_name}.png"
    if os.path.exists(logo_path):
        logo_img = Image.open(logo_path).convert("RGBA").resize((140, 70))

        canvas.paste(logo_img, (15, 315), logo_img)

    # 👥 6. 出場角色大頭貼排版 (迴圈向右遞增)
    chibi_raw = str(row_data.get('出場角色', ''))
    chibi_list = [c.strip() for c in chibi_raw.split(',') if c.strip()]
    
    chibi_start_x = 197  # 💡 第一個大頭貼的起始 X 座標
    chibi_spacing = 135   # 💡 每張大頭貼之間的橫向間距（像素）
    
    for i, name in enumerate(chibi_list):
        chibi_path = f"assets/chibi/{name.lower()}.png"
        if os.path.exists(chibi_path):
            chibi_img = Image.open(chibi_path).convert("RGBA").resize((48, 48)) 
            # 計算公式：當前 X = 起始點 + ( 第幾個大頭貼 * 間距 )
            x_pos = chibi_start_x + (i * chibi_spacing) 
            
            
            # 💡💡💡💡💡
            canvas.paste(chibi_img, (x_pos, 327), chibi_img) # Y 軸固定在 330

    # 🃏 7. 頂艦卡片排版
    card_raw = str(row_data.get('頂艦', ''))
    card_list = [c.strip() for c in card_raw.split(',') if c.strip()]
    
    card_start_x = 160  # 💡 第一張大卡片的起始 X 座標
    card_spacing = 135  # 💡 每張卡片之間的橫向間距
    card_size = (120, 120) # 💡 卡片的縮放寬高尺寸
    
    for i, card_name in enumerate(card_list):
        card_path = f"assets/cards/{card_name}.png"
        if os.path.exists(card_path):
            card_img = Image.open(card_path).convert("RGBA").resize(card_size) 
            # 計算公式：當前卡片 X = 起始點 + ( 第幾張卡 * 橫向間距 )
            x_pos = card_start_x + (i * card_spacing) 
            
            # 將大卡片貼在畫布最底層 (X, Y=320)
            canvas.paste(card_img, (x_pos, 390), card_img)

    return canvas

if __name__ == "__main__":
    print("🎨 正在生成排版預覽圖...")
    result_image = generate_preview_image(MOCK_DATA)
    
    # 將測試圖存檔到專案目錄下，檔名為 layout_preview.png
    output_filename = "layout_preview.png"
    result_image.save(output_filename)
    print(f"💾 預覽圖片已儲存至: {os.path.abspath(output_filename)}")
    
    # 🚀 自動調用作業系統預設的相片檢視器跳出圖片視窗
    try:
        result_image.show()
    except Exception as e:
        print(f"無法自動彈出視窗，請手動打開目錄下的 {output_filename} 查看！")