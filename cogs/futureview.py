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
            print(f"同步成功，共 {len(self.bot.sheets_cache)} 筆資料。")
            return True
        except Exception as e:
            print(f"快取同步失敗: {e}")
            return False

    # 監聽器：只要 Bot 的任何斜線指令「成功執行完畢」且前端解除模糊後，才會偷偷在背景執行
    @commands.Cog.listener()
    async def on_app_command_completion(self, interaction: discord.Interaction, command: app_commands.Command):
        # 限制只紀錄「期數」指令，其餘指令不處理
        if command.name != "期數":
            return

        # 從 extras 安全暫存區取出指令觸發時的時間戳，防範死鎖
        start_perf_time = interaction.extras.get("start_perf_time", time.perf_counter())
        start_wall_time = interaction.extras.get("start_wall_time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        
        end_wall_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        duration = time.perf_counter() - start_perf_time

        # 撈出使用者當時輸入的參數拼裝完整指令
        filled_options = [f"{opt['name']}: {opt['value']}" for opt in interaction.data.get("options", [])]
        full_command = f"/期數 {' '.join(filled_options)}"

        try:
            # 丟到背景線程默默寫入 Google Sheets 的 Log 頁面
            asyncio.create_task(
                asyncio.to_thread(
                    self.bot.user_log.append_row,
                    [
                        start_wall_time,               # 指令觸發時間
                        end_wall_time,                 # 圖片成功發送時間
                        f"{duration:.2f} 秒",          # 實際總耗時
                        interaction.user.id,
                        interaction.user.name,
                        interaction.user.display_name,
                        full_command                   # 完整指令內容
                    ]
                )
            )
        except Exception as e:
            print(f"UserLog 背景紀錄失敗: {e}")

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

        img_buffer = io.BytesIO()
        canvas.save(img_buffer, format="PNG", optimize=True)
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
        
        # 將時間戳安全暫存在 extras 區，供背景監聽器存取
        interaction.extras["start_perf_time"] = time.perf_counter()
        interaction.extras["start_wall_time"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        is_private = True if visibility is None else visibility.value == "private"
        await interaction.response.defer(thinking=True, ephemeral=is_private)

        try:
            # 優化：如果開機時還沒抓完快取，才臨時現場讀取；平時直接走記憶體
            if not self.bot.sheets_cache:
                records = await asyncio.to_thread(self.bot.sht.get_all_records)
                self.bot.sheets_cache = records
            else:
                records = self.bot.sheets_cache
            
            # 從記憶體快取中秒讀目標期數資料 (耗時近乎 0 毫秒)
            target_row = next((r for r in records if str(r.get('期數')) == str(period)), None)
            
            if not target_row:
                await interaction.followup.send(f"找不到第 {period} 期的資料。")
                return
            
            # 2. 繪圖流程放進線程跑
            img_stream = await asyncio.to_thread(self.generate_image, target_row)

            # 3. 發送結果（發送完畢後，畫面立刻解鎖顯示圖片）
            await interaction.followup.send(
                content=f"臺邦 {period} 期未來視：", 
                file=discord.File(img_stream, filename=f"event_{period}.png")
            )
            
            # 當這個函式安全結束後，Discord.py 會自動觸發上面的 on_app_command_completion 進行背景紀錄。
        except Exception as e:
            await interaction.followup.send(f"處理失敗，錯誤: {e}")

async def setup(bot):
    await bot.add_cog(FutureView(bot))