import telebot
import requests
import yfinance as yf
import schedule
import time
import threading
import os
from flask import Flask

# --- ส่วนตั้งค่า ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- ส่วนหน้าเว็บปลอมๆ ---
@app.route('/')
def home():
    return "I am alive! (Bot is running)"

def run_web_server():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- ฟังก์ชันแยกส่วน (Safe Mode) ---

def get_thai_gold():
    try:
        url = "https://api.chnwt.dev/thai-gold-api/latest"
        r = requests.get(url, timeout=5).json() # ลด timeout เหลือ 5 วิ
        if r['status'] == 'success':
            return r['response']['price']['gold']
    except Exception as e:
        print(f"Thai Gold Error: {e}")
    return None

def get_world_gold():
    try:
        # ใช้ yfinance แบบระบุ session (แก้ทาง Yahoo บล็อก)
        # แต่ถ้ายังโดนบล็อก จะคืนค่า None แทนที่จะ Error
        ticker = yf.Ticker("XAUUSD=X")
        spot = ticker.history(period="1d")
        
        if not spot.empty:
            return spot['Close'].iloc[-1]
    except Exception as e:
        print(f"World Gold Error: {e}")
    return None

def get_thb_rate():
    try:
        ticker = yf.Ticker("THB=X")
        data = ticker.history(period="1d")
        if not data.empty:
            return data['Close'].iloc[-1]
    except:
        return None

# --- ฟังก์ชันรวมร่าง (The Avenger) ---
def get_final_message():
    thai = get_thai_gold()
    spot = get_world_gold()
    thb = get_thb_rate()
    
    # ถ้าพังทุกอย่าง
    if not thai and not spot:
        return "⚠️ ระบบต้นทางล่มชั่วคราวครับ (รอสักครู่)"

    msg = "📊 **ราคาทองคำล่าสุด** 🚀\n━━━━━━━━━━━━━━\n"
    
    # 1. แสดงทองไทย (ถ้ามี)
    if thai:
        msg += f"🇹🇭 **ทองคำไทย 96.5%**\n"
        msg += f"🔴 ขายออก: {thai['sell']}\n"
        msg += f"🟢 รับซื้อ: {thai['buy']}\n"
    else:
        msg += "🇹🇭 ทองไทย: (เชื่อมต่อไม่ได้)\n"
    
    msg += "━━━━━━━━━━━━━━\n"

    # 2. แสดงตลาดโลก (ถ้ามี)
    if spot and thb:
        msg += f"🌎 **Market Real-time**\n"
        msg += f"🇺🇸 Gold Spot: ${spot:,.2f}\n"
        msg += f"💵 USD/THB: {thb:.2f} B\n"
    else:
        msg += "🌎 ตลาดโลก: (Yahoo บล็อก IP)\n"
        
    return msg

# --- คำสั่ง Chat ---
@bot.message_handler(commands=['start', 'gold'])
def send_gold(message):
    bot.reply_to(message, get_final_message())

# --- Schedule ---
def run_schedule():
    # ส่งเข้ากลุ่มตามเวลา (ใส่ Chat ID ใน Render หรือยัง?)
    target_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    def job():
        if target_chat_id:
            bot.send_message(target_chat_id, get_final_message())
            
    schedule.every().day.at("09:30").do(job)
    schedule.every().day.at("13:00").do(job)
    schedule.every().day.at("16:30").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    t_web = threading.Thread(target=run_web_server)
    t_web.start()
    
    t_sched = threading.Thread(target=run_schedule)
    t_sched.start()
    
    print("🚀 Bot Started (Robust Mode)!")
    bot.infinity_polling()
