import discord
import json
import gspread
import os
import asyncio
from dotenv import load_dotenv
load_dotenv()

from flask import Flask
from threading import Thread
from discord.ext import commands

app = Flask('')

@app.route('/')
def home():
    return "Bot is alive"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# 使用者安裝型（全域），伺服器變數放著以防萬一
GUILD_ID = 728929244830498857

class MyClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

        # 設定 Google API 憑證路徑
        google_creds_str = os.getenv("GOOGLE_CREDENTIALS")
        
        if not google_creds_str:
            raise ValueError("GOOGLE_CREDENTIALS 未設定")
        google_creds = json.loads(google_creds_str)
        
        # 綁定 Google 試算表
        self.gc = gspread.service_account_from_dict(google_creds)

        self.spreadsheet = self.gc.open("FUTUREVIEW")

        self.sht = self.spreadsheet.sheet1
        self.user_log = self.spreadsheet.worksheet("UserLog") 
        
        # 建立全域記憶體快取清單存放活動資料 (供 Cog 內部訪問)
        self.sheets_cache = []

    async def setup_hook(self):
        # Cogs 模組載入與全域指令同步。
        # 自動載入 cogs 資料夾內所有的 .py 檔案
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'成功載入模組: {filename}，進行全域指令同步...')
        
        synced = await self.tree.sync() # 直接同步到全域
        print(f"【同步成功】全域同步 {len(synced)} 個斜線指令")

    async def on_ready(self):
        """機器人成功與 Discord 建立連線並上線後，才在背景下載試算表。"""
        print(f"機器人已成功登入為: {self.user.name}")
        
        # 如果快取是空的，就啟動背景執行緒去撈 Google 試算表
        if not self.sheets_cache:
            print("正在下載 Google 試算表資料至全域快取...")
            loop = asyncio.get_running_loop()
            try:
                # 利用 run_in_executor 避免抓資料時卡住機器人的其他網路回應
                records = await loop.run_in_executor(None, self.sht.get_all_records)
                self.sheets_cache = records
                print(f"【快取成功】預載入 {len(self.sheets_cache)} 筆活動資料")
            except Exception as e:
                print(f"預載入試算表失敗，錯誤訊息: {e}")

# 實例化 Bot 物件
bot = MyClient()

# 啟動網頁伺服器（Keep Alive）
t = Thread(target=run_web)
t.start()

# 啟動機器人
bot.run(os.getenv("BOT_TOKEN"))