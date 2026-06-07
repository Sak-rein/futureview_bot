import discord
import json
import gspread
import os
import asyncio 
from discord.ext import commands

# 使用者安裝型（全域），伺服器變數放著以防萬一
GUILD_ID = 728929244830498857

class MyClient(commands.Bot):
    def __init__(self):
        # 使用 os.path 路徑防呆
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(BASE_DIR, "key.json")
        
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        
        # 初始化時讀取 Google 憑證
        with open(key_path, "r", encoding="utf-8") as f:
            info = json.load(f)
        
        # 綁定 Google 試算表
        self.gc = gspread.service_account_from_dict(info)
        self.sht = self.gc.open("未來活動時程 data").sheet1
        
        # 建立記憶體快取清單存放活動資料
        self.sheets_cache = []

    async def setup_hook(self):

        # Cogs 模組載入與全域指令同步。
        print("正在載入 Cogs 模組...")
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                await self.load_extension(f'cogs.{filename[:-3]}')
                print(f'成功載入模組: {filename}')

        print("進行全域指令同步...")
        
        synced = await self.tree.sync() # 直接同步到全域
        print(f"【同步成功】全域同步 {len(synced)} 個斜線指令！")

    async def on_ready(self):

        """機器人成功與 Discord 建立連線並上線後，才在背景默默下載試算表。"""

        print(f"機器人已成功登入為: {self.user.name}")
        
        # 如果快取是空的，就啟動背景執行緒去撈 Google 試算表
        if not self.sheets_cache:
            print("正在下載 Google 試算表資料...")
            loop = asyncio.get_event_loop()
            try:
                # 利用 run_in_executor 避免抓資料時卡住機器人的其他網路回應
                self.sheets_cache = await loop.run_in_executor(None, self.sht.get_all_records)
                print(f"成功預載入 {len(self.sheets_cache)} 筆活動資料")
            except Exception as e:
                print(f"預載入試算表失敗，錯誤訊息: {e}")

# 實例化 Bot 物件
bot = MyClient()

# 使用 os.path 絕對路徑讀取 token.txt 內的 Discord Token
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
token_path = os.path.join(BASE_DIR, "token.txt")
with open(token_path, "r", encoding="utf-8") as f:
    BOT_TOKEN = f.read().strip()

# 啟動機器人
bot.run(os.getenv("BOT_TOKEN"))