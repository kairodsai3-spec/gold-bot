import telebot
import requests
import schedule
import time
import threading
import os
from flask import Flask

# --- ตั้งค่า ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Web Server หลอกๆ (กัน Render หลับ) ---
@app.route('/')
def home():
    return "Bot is running with Binance API..."

def run_web_server():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- 1. ดึงทองไทย 96.5% (THB) ---
def get_thai_gold():
    try:
        # API นี้ดึงจากสมาคมฯ มาแคชไว้ให้แล้ว (เสถียรมาก)
        url = "https://api.chnwt.dev/thai-gold-api/latest"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        if data['status'] == 'success':
            return data['response']['price']['gold']
    except Exception as e:
        print(f"Thai API Error: {e}")
    return None

# --- 2. ดึงทองนอก 99.99% (USD) จาก Binance ---
def get_spot_gold_binance():
    try:
        # ดึงราคา XAUUSDT (Gold Spot) จาก Binance Futures API
        # ข้อดี: ฟรี, Real-time 100%, ไม่มีการบล็อก IP
        url = "https://fapi.binance.com/fapi/v1/ticker/price?symbol=XAUUSDT"
        response = requests.get(url, timeout=5)
        data = response.json()
        
        # คืนค่าราคาเป็นตัวเลข (float)
        return float(data['price'])
    except Exception as e:
        print(f"Binance API Error: {e}")
        return None

# --- สร้างข้อความ ---
def get_message():
    thai = get_thai_gold()
    spot_usd = get_spot_gold_binance()
    
    msg = "📊 **ราคาทองคำ Real-Time** ⚡\n"
    msg += "━━━━━━━━━━━━━━\n"
    
    # ส่วนที่ 1: ทองไทย (บาท)
    if thai:
        msg += "🇹🇭 **ทองไทย 96.5% (บาท)**\n"
        msg += f"🔴 ขายออก: **{thai['sell']}**\n"
        msg += f"🟢 รับซื้อ: **{thai['buy']}**\n"
    else:
        msg += "🇹🇭 ทองไทย: (เชื่อมต่อไม่ได้)\n"
        
    msg += "━━━━━━━━━━━━━━\n"
    
    # ส่วนที่ 2: ทองนอก (USD)
    if spot_usd:
        msg += "🌎 **ทองคำโลก 99.99% (Spot)**\n"
        msg += f"🇺🇸 **XAU/USD:** ${spot_usd:,.2f}\n"
        # (แถม) แปลงเป็นบาทคร่าวๆ (สมมติเรท 35.5 หรือดึงเพิ่มก็ได้)
        # แต่นี้เอาแค่ USD ตามโจทย์
    else:
        msg += "🌎 ทองโลก: (เชื่อมต่อไม่ได้)\n"
    
    msg += "━━━━━━━━━━━━━━\n"
    msg += "(Source: Binance API & Thai Gold API)"
    
    return msg

# --- คำสั่ง Bot ---
@bot.message_handler(commands=['start', 'gold'])
def send_gold(message):
    bot.reply_to(message, get_message())

# --- ตั้งเวลาส่ง ---
def run_schedule():
    target_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    def job():
        if target_chat_id:
            bot.send_message(target_chat_id, get_message())
            
    # ตั้งเวลาตามต้องการ
    schedule.every().day.at("09:30").do(job)
    schedule.every().day.at("14:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    t_web = threading.Thread(target=run_web_server)
    t_web.start()
    
    t_sched = threading.Thread(target=run_schedule)
    t_sched.start()
    
    print("🚀 Bot Started (Binance Edition)!")
    bot.infinity_polling()
