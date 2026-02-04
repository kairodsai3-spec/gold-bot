import ccxt
import time
import requests
import os
import telebot # ใช้ตัวนี้แทน requests ดิบๆ
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread

# =======================================================
# ⚙️ CONFIG
# =======================================================
TG_TOKEN = os.environ.get('TG_TOKEN', '7628151103')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID', '8599862112:AAEDAQ3cSIhVyKSX8qGeBLkKA5XDxmEWsy4')

# ตั้งค่า Bot Telegram (Listening Mode)
bot = telebot.TeleBot(TG_TOKEN)

# =======================================================
# 💬 ส่วนรับคำสั่งจากคุณ (Telegram Commands)
# =======================================================

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "สวัสดีครับนายท่าน! 🤖\nพิมพ์ /price เพื่อดูราคาทอง\nพิมพ์ /status เพื่อเช็คสถานะบอท")

@bot.message_handler(commands=['price'])
def check_price_command(message):
    price = get_investing_price()
    if price:
        bot.reply_to(message, f"💰 ราคาทองล่าสุด: ${price:,.2f}")
    else:
        bot.reply_to(message, "⚠️ ดึงราคาไม่ได้ชั่วคราวครับ")

@bot.message_handler(commands=['status'])
def check_status_command(message):
    bot.reply_to(message, "✅ บอททำงานปกติครับ\n- Web Server: Online\n- Bot Loop: Running")

def run_telegram_listener():
    # สั่งให้บอทรอรับข้อความตลอดเวลา
    try:
        print("👂 Telegram Listener Started...")
        bot.infinity_polling()
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# =======================================================
# 🟢 Web Server & Bot Logic (ของเดิม)
# =======================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "Bot is Alive!"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

def get_investing_price():
    # ... (ฟังก์ชั่นดึงราคา เหมือนเดิมเป๊ะ) ...
    url = "https://th.investing.com/currencies/xau-usd"
    headers = {"User-Agent": "Mozilla/5.0 ..."} # ย่อไว้นะครับ ใช้ของเดิมได้เลย
    try:
        response = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            price_tag = soup.find("div", {"data-test": "instrument-price-last"})
            if price_tag:
                return float(price_tag.text.strip().replace(',', ''))
    except:
        pass
    return None

def send_alert(msg):
    # ฟังก์ชั่นส่งแจ้งเตือน (ใช้ bot.send_message แทน requests)
    try:
        bot.send_message(TG_CHAT_ID, msg)
    except Exception as e:
        print(f"Send Error: {e}")

def run_bot_logic():
    print("🚀 Bot Logic Started...")
    send_alert("🤖 บอทอัปเกรดใหม่! รองรับคำสั่งแล้วครับ (ลองพิมพ์ /price ดูสิ)")
    
    last_price = 0
    while True:
        try:
            price = get_investing_price()
            if price:
                print(f"Price: {price}")
                # Logic เดิมของคุณ...
            time.sleep(20)
        except Exception as e:
            print(f"Bot Error: {e}")
            time.sleep(20)

# =======================================================
# 🔥 Main Execution (รัน 3 อย่างพร้อมกัน)
# =======================================================
if __name__ == "__main__":
    # 1. Web Server Thread
    t1 = Thread(target=run_web_server)
    t1.start()

    # 2. Telegram Listener Thread (เพิ่มใหม่!)
    t2 = Thread(target=run_telegram_listener)
    t2.start()

    # 3. Bot Logic Thread
    run_bot_logic()

