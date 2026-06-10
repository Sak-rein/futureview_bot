import discord
import json
import gspread
import os
import asyncio
import io
from flask import Flask
from threading import Thread
from discord.ext import commands
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
from googleapiclient.http import MediaIoBaseDownload
from PIL import Image
from dotenv import load_dotenv
load_dotenv()

# --- Flask Web Server ---
app = Flask('')
@app.route('/')
def home():
    return "Bot on line"

def run_web():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)

# --- Bot Implementation ---
class MyClient(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())
        
        # 初始化快取變數
        self.card_cache = {}
        self.card_file_map = {}
        self.sheets_cache = []

        # 設定 Google API 憑證路徑
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        key_path = os.path.join(BASE_DIR, "key.json")
        
        with open(key_path, "r", encoding="utf-8") as f:
            info = json.load(f)
        
        # 綁定 Google 服務
        self.gc = gspread.service_account_from_dict(info)
        creds = Credentials.from_service_account_info(
            info, scopes=["https://www.googleapis.com/auth/drive.readonly"]
        )
        self.drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)
        self.sht = self.gc.open("未來活動時程 data").sheet1

    async def setup_hook(self):

        # 自動載入 Cogs
        cog_dir = './cogs'
        if os.path.exists(cog_dir):
            for filename in os.listdir(cog_dir):
                if filename.endswith('.py'):
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'成功載入模組: {filename}')
        
        # 同步全域指令
        synced = await self.tree.sync()
        print(f"【同步成功】全域同步 {len(synced)} 個斜線指令！")

    async def preload_cards(self):
        FOLDER_ID = "1HHwr7mgqZ3UvShunByHGKxoQF4MllvbB"
        print("開始同步卡圖...")
        
        try:
            results = self.drive_service.files().list(q=f"'{FOLDER_ID}' in parents and trashed=false",
            fields="files(id,name)"
            ).execute()
            files = results.get("files", [])
            print(f"Drive 共 {len(files)} 個檔案")

            self.card_cache.clear()
            self.card_file_map.clear()

            for file in files:
                file_name = file["name"]
                if not file_name.lower().endswith(".png"):
                    continue
                
                card_name = file_name[:-4]
                try:
                    request = self.drive_service.files().get_media(fileId=file["id"])
                    file_buffer = io.BytesIO()
                    downloader = MediaIoBaseDownload(file_buffer, request)
                    done = False
                    while not done:
                        _, done = downloader.next_chunk()
                    file_buffer.seek(0)

                    img = Image.open(file_buffer).convert("RGBA").resize((120, 120))
                    self.card_cache[card_name] = img
                    self.card_file_map[card_name] = file["id"]
                    print(f"已載入卡圖: {card_name}")

                except Exception as e:
                    print(f"載入單張卡圖失敗 {card_name}: {e}")
            
            print(f"卡圖共 {len(self.card_cache)} 張同步完成")

        except Exception as e:
            print(f"存取 Google Drive 失敗: {e}")

    async def on_ready(self):
        print(f"機器人已成功登入為: {self.user.name}")
        
        if not self.sheets_cache:
            try:
                print("正在下載 Google 試算表資料...")
                loop = asyncio.get_event_loop()

                self.sheets_cache = await loop.run_in_executor(None, self.sht.get_all_records)
                print(f"成功預載入 {len(self.sheets_cache)} 筆活動資料")
                
                # 背景同步卡圖
                asyncio.create_task(self.preload_cards())

            except Exception as e:
                print(f"on_ready 初始化失敗: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # 啟動網頁伺服器線程
    t = Thread(target=run_web)
    t.start()

    # 取得 Token (優先使用環境變數，若無則讀取檔案)
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        BASE_DIR = os.path.dirname(os.path.abspath(__file__))
        token_path = os.path.join(BASE_DIR, "token.txt")
        with open(token_path, "r", encoding="utf-8") as f:
            bot_token = f.read().strip()

    bot = MyClient()
    bot.run(bot_token)