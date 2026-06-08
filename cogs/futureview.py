import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw
from PIL import ImageFont
import io
import os
import asyncio

class FutureView(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  

    def generate_image(self, row_data):
        """利用 Pillow 繪製未來視圖片畫布排版"""
        canvas_w, canvas_h = 850, 520 # 畫布寬高
        canvas = Image.new("RGBA", (canvas_w, canvas_h), color=(255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        # 自動計算最外層 NotoSansJP-Regular.ttf 的絕對路徑
        current_dir = os.path.dirname(os.path.abspath(__file__)) # cogs 資料夾路徑
        project_root = os.path.dirname(current_dir) # 最外層資料夾路徑
        font_path = os.path.join(project_root, "NotoSansJP-Regular.ttf")

        try:
            # 使用絕對路徑讀取
            font_main = ImageFont.truetype(font_path, 20)
            font_title = ImageFont.truetype(font_path, 20)
            print(f"成功載入中日字型：{font_path}")
        except Exception as font_error:
            print(f"絕對路徑載入依舊失敗，原因: {font_error}")
            font_main = ImageFont.load_default()
            font_title = ImageFont.load_default()

        # 1. Banner
        banner_name = str(row_data.get('banner', '')).strip()
        banner_path = f"assets/banner/{banner_name}.png"
        banner_name and os.path.exists(banner_path)
        banner_img = Image.open(banner_path).convert("RGBA")
        banner_img = banner_img.resize((canvas_w, 282))
        canvas.paste(banner_img, (0, 1), banner_img)

        # 表格格線繪製
        draw.line([(0, 285), (canvas_w, 285)], fill=(0, 0, 0), width=2) # 頂部粗橫線
        draw.line([(0, 320), (canvas_w, 320)], fill=(0, 0, 0), width=1) # 中間細橫線
        draw.line([(0, 380), (canvas_w, 380)], fill=(0, 0, 0), width=2) # 下方粗橫線
        
        # 提取文字與日期欄位
        period = row_data.get('期數', '')
        mode = row_data.get('模式', '')
        start_d = row_data.get('開活日', '')
        end_d = row_data.get('結活日', '')
        title = row_data.get('活動名稱', '')

        # 第一層文字區塊排版
        draw.text((45, 302), f"{period} ", fill=(0, 0, 0), font=font_main, anchor="mm")
        draw.text((110, 302), f"{mode} ", fill=(0, 0, 0), font=font_main, anchor="mm")
        draw.line([(158, 320.5), (158, 285)], fill=(200, 200, 200), width=2) # 縱向直條分隔線
    
        draw.text((220, 302), f"{start_d}", fill=(0, 0, 0), font=font_main, anchor="mm")
        draw.line([(288, 320.5), (288, 285)], fill=(200, 200, 200), width=2) # 縱向直條分隔線
    
        draw.text((355, 302), f"{end_d}", fill=(0, 0, 0), font=font_main, anchor="mm")
        draw.line([(423, 320.5), (423, 285)], fill=(200, 200, 200), width=2) # 縱向直條分隔線

        draw.text((637, 302), f"{title}", fill=(27, 38, 59), font=font_title, anchor="mm") # 活動名稱

        # 屬性
        attr_name = str(row_data.get('attribute', '')).lower().strip()
        attr_path = f"assets/attribute/{attr_name}.png"
        if os.path.exists(attr_path):
            attr_img = Image.open(attr_path).convert("RGBA").resize((100, 100))
            canvas.paste(attr_img, (30, 400), attr_img)

        # 樂隊logo
        logo_name = str(row_data.get('logo', '')).lower().strip()
        
        # 定位
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        logo_path = os.path.join(project_root, "assets", "logos", f"{logo_name}.png")

        if os.path.exists(logo_path):
            logo_img = Image.open(logo_path).convert("RGBA").resize((140, 70))
            canvas.paste(logo_img, (12, 317), logo_img)

        # 角色大頭貼
        chibi_raw = str(row_data.get('出場角色', ''))
        chibi_list = [c.strip() for c in chibi_raw.split(',') if c.strip()]
        chibi_start_x = 197  
        chibi_spacing = 135   
        for i, name in enumerate(chibi_list):
            chibi_path = f"assets/chibi/{name.lower()}.png"
            if os.path.exists(chibi_path):
                chibi_img = Image.open(chibi_path).convert("RGBA").resize((48, 48))
                x_pos = chibi_start_x + (i * chibi_spacing) 
                canvas.paste(chibi_img, (x_pos, 327), chibi_img)

        # 5. 頂艦卡片
        card_raw = str(row_data.get('頂艦', ''))
        card_list = [c.strip() for c in card_raw.split(',') if c.strip()]
        card_start_x = 160  
        card_spacing = 135  
        card_size = (120, 120) 
        for i, card_name in enumerate(card_list):
            card_path = f"assets/cards/{card_name}.png"
            if os.path.exists(card_path):
                card_img = Image.open(card_path).convert("RGBA").resize(card_size) 
                x_pos = card_start_x + (i * card_spacing) 
                canvas.paste(card_img, (x_pos, 390), card_img)

        img_buffer = io.BytesIO()
        canvas.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return img_buffer
    
    # 定義斜線指令 (Slash Command)
    @app_commands.command(name="期數", description="臺邦未來活動情報")
    @app_commands.describe(period="請輸入期數（不含316之前）")
    
    # 1. 設定安裝類型：允許伺服器安裝 (guild) 與 使用者隨身安裝 (user)
    @app_commands.allowed_installs(guilds=True, users=True)
    # 2. 設定執行環境：允許伺服器內 (guilds)、機器人私訊 (bot_dms)、私人小群 (private_channels)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def Events(self, interaction: discord.Interaction, period: int):
        await interaction.response.defer(thinking=True)
        
        try:
            records = self.bot.sheets_cache
            if not records:
                loop = asyncio.get_event_loop()
                records = await loop.run_in_executor(None, self.bot.sht.get_all_records)
            
            target_row = None
            for row in records:
                if str(row.get('期數')) == str(period):
                    target_row = row
                    break
            
            if not target_row:
                await interaction.followup.send(f"找不到第 {period} 期的資料。")
                return

            img_stream = self.generate_image(target_row)
            discord_file = discord.File(img_stream, filename=f"event_{period}.png")
            await interaction.followup.send(content=f"臺邦 {period} 期未來視：", file=discord_file)

        except Exception as e:
            print(f"指令內部報錯: {e}")
            await interaction.followup.send(f"處理失敗，錯誤訊息: {e}")

# setup 函式向主程式註冊此 Cog
async def setup(bot):
    await bot.add_cog(FutureView(bot))
