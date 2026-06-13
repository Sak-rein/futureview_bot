import discord
import io
import os
import asyncio
import time

from discord.ext import commands
from discord import app_commands
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

class FutureView(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        # 優化：字型在初始化時只載入一次，避免每次畫圖都重複讀取硬碟
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        font_path = os.path.join(project_root, "NotoSansJP-Regular.ttf")
        try:
            self.font_main = ImageFont.truetype(font_path, 20)
            self.font_title = ImageFont.truetype(font_path, 20)
        except Exception as e:
            print(f"字型載入失敗，使用預設字型: {e}")
            self.font_main = ImageFont.load_default()
            self.font_title = ImageFont.load_default()

    # 在 Cog 載入時，自動觸發第一次資料非同步快取
    async def cog_load(self):
        asyncio.create_task(self.update_cache())

    # 非同步更新快取的內建模組
    async def update_cache(self):
        try:
            print("正在從 Google Sheets 同步未來視資料至快取...")
            records = await asyncio.to_thread(self.bot.sht.get_all_records)
            self.bot.sheets_cache = records
            print(f"快取同步成功，共 {len(self.bot.sheets_cache)} 筆資料。")
            return True
        except Exception as e:
            print(f"快取同步失敗: {e}")
            return False

    # 🛠️ 修正 1：徹底移除原本的 on_app_command_completion 監聽器！
    # 避免它在後台偷偷戳 Google Sheets 的 append_row 導致 Event Loop 再次塞車

    def generate_image(self, row_data):
        canvas_w, canvas_h = 850, 520
        canvas = Image.new("RGBA", (canvas_w, canvas_h), color=(255, 255, 255, 255))
        draw = ImageDraw.Draw(canvas)
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)

        # 1. Banner (本地快取讀取)
        banner_name = str(row_data.get('banner', '')).strip()
        banner_path = os.path.join(project_root, "assets", "banner", f"{banner_name}.png")

        banner_img = None
        if banner_name and os.path.exists(banner_path):
            try:
                banner_img = Image.open(banner_path).convert("RGBA")
            except Exception as e:
                print(f"讀取本地 Banner 錯誤: {e}")

        if banner_img:
            banner_img = banner_img.resize((850, 282))
            canvas.paste(banner_img, (0, 1), banner_img)
        else:
            draw.rectangle([(0, 1), (850, 283)], fill=(230, 230, 230))
            draw.text((425, 140), "Banner 本地檔案不存在", fill=(100, 100, 100), anchor="mm")

        # 表格格線
        draw.line([(0, 285), (canvas_w, 285)], fill=(0, 0, 0), width=2)
        draw.line([(0, 320), (canvas_w, 320)], fill=(0, 0, 0), width=1)
        draw.line([(0, 380), (canvas_w, 380)], fill=(0, 0, 0), width=2)
        
        # 提取文字
        period, mode = row_data.get('期數', ''), row_data.get('模式', '')
        start_d, end_d = row_data.get('開活日', ''), row_data.get('結活日', '')
        title = row_data.get('活動名稱', '')

        # 使用優化重用後的字型
        draw.text((45, 302), f"{period}", fill=(0, 0, 0), font=self.font_main, anchor="mm")
        draw.text((110, 302), f"{mode}", fill=(0, 0, 0), font=self.font_main, anchor="mm")
        draw.line([(158, 320.5), (158, 285)], fill=(200, 200, 200), width=2)
        draw.text((220, 302), f"{start_d}", fill=(0, 0, 0), font=self.font_main, anchor="mm")
        draw.line([(288, 320.5), (288, 285)], fill=(200, 200, 200), width=2)
        draw.text((355, 302), f"{end_d}", fill=(0, 0, 0), font=self.font_main, anchor="mm")
        draw.line([(423, 320.5), (423, 285)], fill=(200, 200, 200), width=2)
        draw.text((637, 302), f"{title}", fill=(27, 38, 59), font=self.font_title, anchor="mm")

        # 屬性
        attr_name = str(row_data.get('attribute', '')).lower().strip()
        attr_path = os.path.join(project_root, "assets", "attribute", f"{attr_name}.png")
        if os.path.exists(attr_path):
            attr_img = Image.open(attr_path).convert("RGBA").resize((100, 100))
            canvas.paste(attr_img, (30, 400), attr_img)

        # 樂隊logo
        logo_name = str(row_data.get('logo', '')).lower().strip()
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
            chibi_path = os.path.join(project_root, "assets", "chibi", f"{name.lower()}.png")
            if os.path.exists(chibi_path):
                chibi_img = Image.open(chibi_path).convert("RGBA").resize((48, 48))
                x_pos = chibi_start_x + (i * chibi_spacing) 
                canvas.paste(chibi_img, (x_pos, 327), chibi_img)

        # 頂艦卡片
        card_raw = str(row_data.get('頂艦', ''))
        card_list = [c.strip() for c in card_raw.split(',') if c.strip()]
        card_start_x = 160  
        card_spacing = 135  
        card_size = (120, 120) 
        for i, card_name in enumerate(card_list):
            card_path = os.path.join(project_root, "assets", "cards", f"{card_name}.png")
            if os.path.exists(card_path):
                card_img = Image.open(card_path).convert("RGBA").resize(card_size) 
                x_pos = card_start_x + (i * card_spacing) 
                canvas.paste(card_img, (x_pos, 390), card_img)

        # 🛠️ 優化可選：改儲存為 JPEG 格式以換取極致的 Discord 上傳速度（600KB -> 50KB）
        # 如果你想維持原本的 PNG，請把下面這段換回你原本的三行即可。
        final_canvas = canvas.convert("RGB")
        img_buffer = io.BytesIO()
        final_canvas.save(img_buffer, format="JPEG", quality=85, optimize=True)
        img_buffer.seek(0)
        return img_buffer

    @app_commands.command(name="期數", description="臺邦未來活動情報")
    @app_commands.describe(period="請輸入期數 (不含316之前)", visibility="顯示方式")
    @app_commands.choices(visibility=[
        app_commands.Choice(name="公開", value="public"),
        app_commands.Choice(name="僅自己可見", value="private")
    ])
    @app_commands.allowed_installs(guilds=True, users=True)
    @app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
    async def Events(self, interaction: discord.Interaction, period: int, visibility: app_commands.Choice[str] = None):
        
        # 🛠️ 修正 2：在進門 defer 之前，先把時間基準點與 extras 暫存區打點好
        t_start = time.perf_counter()
        wall_time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        interaction.extras["start_perf_time"] = t_start
        interaction.extras["start_wall_time"] = wall_time_str

        is_private = True if visibility is None else visibility.value == "private"
        await interaction.response.defer(thinking=True, ephemeral=is_private)
        
        try:
            # 1. 記憶體搜尋資料
            t_cache_start = time.perf_counter()
            records = self.bot.sheets_cache
            if not records:
                records = await asyncio.to_thread(self.bot.sht.get_all_records)
                self.bot.sheets_cache = records
                
            target_row = next((r for r in records if str(r.get('期數')) == str(period)), None)
            t_cache_end = time.perf_counter()
            t_step2 = t_cache_end - t_cache_start
            
            if not target_row:
                await interaction.followup.send(f"找不到第 {period} 期的資料。")
                return
            
            # 2. Pillow 繪圖流程
            t_draw_start = time.perf_counter()
            img_stream = await asyncio.to_thread(self.generate_image, target_row)
            t_draw_end = time.perf_counter()
            t_step3 = t_draw_end - t_draw_start

            # 3. Discord 圖片上傳發送
            t_send_start = time.perf_counter()
            
            # 🛠️ 修正 3：對應上面如果改了 JPEG，這裡副檔名要同步改成 .jpg
            await interaction.followup.send(
                content=f"臺邦 {period} 期未來視：", 
                file=discord.File(img_stream, filename=f"event_{period}.jpg")
            )
            t_send_end = time.perf_counter()
            t_step4 = t_send_end - t_send_start
            
            # 4. 計算總耗時
            t_total = time.perf_counter() - t_start
            
            # 拼裝寫入本地日誌的文字串
            log_line = (
                f"[{wall_time_str}] 使用者: {interaction.user.name} ({interaction.user.id}) | "
                f"查詢期數: {period} | "
                f"快取搜尋: {t_step2:.4f}秒 | 繪圖: {t_step3:.4f}秒 | 上傳: {t_step4:.4f}秒 | "
                f"指令總耗時: {t_total:.4f}秒\n"
            )
            
            # 定義本地端極速寫入函式
            def save_to_local_file():
                with open("bot_perf_logs.txt", "a", encoding="utf-8") as f:
                    f.write(log_line)
                    
            asyncio.create_task(asyncio.to_thread(save_to_local_file))
            
        except Exception as e:
            await interaction.followup.send(f"處理失敗，錯誤: {e}")

    # 手動同步雲端最新資料的指令
    @app_commands.command(name="更新未來視快取", description="重新手動從 Google Sheets 同步資料至 Bot 記憶體")
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_cache(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        success = await self.update_cache()
        if success:
            await interaction.followup.send("未來視快取資料更新成功！")
        else:
            await interaction.followup.send("更新失敗，請檢查後台終端機錯誤訊息。")

async def setup(bot):
    await bot.add_cog(FutureView(bot))