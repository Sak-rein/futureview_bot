import discord
from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
import io
import os
import asyncio
import requests  # 務必確保 requirements.txt 有加 requests

OWNER_ID = 123456789012345678

class FutureView(commands.Cog):
    def __init__(self, bot):
        self.bot = bot  

    # 封裝下載邏輯，避免崩潰
    def get_image_from_url(self, url):
        if not url or str(url).strip().lower() in ['none', 'nan', '']:
            return None
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return Image.open(io.BytesIO(response.content)).convert("RGBA")
        except Exception as e:
            print(f"下載圖片錯誤: {e}")
        return None

    def generate_image(self, row_data):
        canvas_w, canvas_h = 850, 520
        canvas = Image.new("RGBA", (canvas_w, canvas_h), color=(255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        font_path = os.path.join(project_root, "NotoSansJP-Regular.ttf")

        try:
            font_main = ImageFont.truetype(font_path, 20)
            font_title = ImageFont.truetype(font_path, 20)
        except:
            font_main = ImageFont.load_default()
            font_title = ImageFont.load_default()

        # 1. Banner ( URL 抓取)
        image_url = row_data.get('banner_url')
        banner_img = self.get_image_from_url(image_url)
        if banner_img:
            banner_img = banner_img.resize((850, 282))
            canvas.paste(banner_img, (0, 1), banner_img)
        else:
            draw.rectangle([(0, 1), (850, 283)], fill=(230, 230, 230))
            draw.text((425, 140), "Banner 載入失敗", fill=(100, 100, 100), anchor="mm")

        # 表格格線
        draw.line([(0, 285), (canvas_w, 285)], fill=(0, 0, 0), width=2)
        draw.line([(0, 320), (canvas_w, 320)], fill=(0, 0, 0), width=1)
        draw.line([(0, 380), (canvas_w, 380)], fill=(0, 0, 0), width=2)
        
        # 提取文字
        period, mode = row_data.get('期數', ''), row_data.get('模式', '')
        start_d, end_d = row_data.get('開活日', ''), row_data.get('結活日', '')
        title = row_data.get('活動名稱', '')

        draw.text((45, 302), f"{period}", fill=(0, 0, 0), font=font_main, anchor="mm")
        draw.text((110, 302), f"{mode}", fill=(0, 0, 0), font=font_main, anchor="mm")
        draw.line([(158, 320.5), (158, 285)], fill=(200, 200, 200), width=2)
        draw.text((220, 302), f"{start_d}", fill=(0, 0, 0), font=font_main, anchor="mm")
        draw.line([(288, 320.5), (288, 285)], fill=(200, 200, 200), width=2)
        draw.text((355, 302), f"{end_d}", fill=(0, 0, 0), font=font_main, anchor="mm")
        draw.line([(423, 320.5), (423, 285)], fill=(200, 200, 200), width=2)
        draw.text((637, 302), f"{title}", fill=(27, 38, 59), font=font_title, anchor="mm")

        # 屬性 (本地讀取)
        attr_name = str(row_data.get('attribute', '')).lower().strip()
        attr_path = f"assets/attribute/{attr_name}.png"
        if os.path.exists(attr_path):
            attr_img = Image.open(attr_path).convert("RGBA").resize((100, 100))
            canvas.paste(attr_img, (30, 400), attr_img)

        # 樂隊logo (本地讀取)
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

        # 頂艦卡片（Google Drive）
        card_raw = str(row_data.get('頂艦', ''))
        card_list = [c.strip() for c in card_raw.split(',') if c.strip()]
        card_start_x = 160
        card_spacing = 135

        for i, card_name in enumerate(card_list):

            card_img = self.bot.card_cache.get(card_name)

            if card_img:
                x_pos = card_start_x + (i * card_spacing)
                canvas.paste(card_img,(x_pos, 390),card_img)
    
        img_buffer = io.BytesIO()
        canvas.save(img_buffer, format="PNG")
        img_buffer.seek(0)
        return img_buffer
        
    @app_commands.command(name="sync_cards",description="update")
    async def sync_cards(self, interaction: discord.Interaction):

        if interaction.user.id != OWNER_ID:
            return
        await interaction.response.defer(thinking=True)

        try:
            await self.bot.preload_cards()
            await interaction.followup.send(f"共 {len(self.bot.card_cache)} 張卡圖同步完成",ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"同步失敗：{e}",ephemeral=True)

    @app_commands.command(name="期數", description="臺邦未來活動情報")
    @app_commands.describe(period="請輸入期數（不含316之前）")
    
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def Events(self, interaction: discord.Interaction, period: int):
        await interaction.response.defer(thinking=True)
        try:
            records = self.bot.sheets_cache or await asyncio.get_event_loop().run_in_executor(None, self.bot.sht.get_all_records)
            target_row = next((r for r in
            records if str(r.get('期數')) == str(period)), None)
            
            if not target_row:
                await interaction.followup.send(f"找不到第 {period} 期的資料。")
                return

            img_stream = self.generate_image(target_row)
            await interaction.followup.send(content=f"臺邦 {period} 期未來視：", file=discord.File(img_stream, filename=f"event_{period}.png"))
            
        except Exception as e:
            await interaction.followup.send(f"處理失敗，錯誤: {e}")

    @app_commands.command(name="sync_cards",description="同步 Google Drive 卡圖")
    async def sync_cards(self,interaction: discord.Interaction):
        await interaction.response.defer(thinking=True)
        try:
            await self.bot.preload_cards()
            await interaction.followup.send(f"共 {len(self.bot.card_cache)} 張卡圖同步完成")

        except Exception as e:
            await interaction.followup.send(f"同步失敗：{e}")

async def setup(bot):
    await bot.add_cog(FutureView(bot))