import telebot
import requests
import yfinance as yf
import schedule
import time
import threading
import os
from flask import Flask # เพิ่มตัวนี้มาสร้างเว็บ

# --- ส่วนตั้งค่า ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__) # สร้างแอปเว็บจำลอง

# --- ส่วนหน้าเว็บปลอมๆ (ให้ UptimeRobot ยิงเข้ามา) ---
@app.route('/')
def home():
    return "I am alive! (Bot is running)"

def run_web_server():
    # ให้รันที่ Port ที่ Render กำหนด หรือ Port 8080
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- ฟังก์ชันบอท (เหมือนเดิม) ---
def get_final_message():
    try:
        # 1. ทองไทย
        url = "https://api.chnwt.dev/thai-gold-api/latest"
        r = requests.get(url, timeout=10).json()
        thai = r['response']['price']['gold'] if r['status']=='success' else None
        
        # 2. ตลาดโลก
        tickers = yf.Tickers("XAUUSD=X THB=X")
        spot = tickers.tickers['XAUUSD=X'].history(period='1d')['Close'].iloc[-1]
        thb = tickers.tickers['THB=X'].history(period='1d')['Close'].iloc[-1]
        
        msg = "📊 **ราคาทองคำ & ตลาดโลก** 🚀\n━━━━━━━━━━━━━━\n"
        if thai:
            msg += f"🇹🇭 ขายออก: {thai['sell']} | รับซื้อ: {thai['buy']}\n"
        msg += f"🌎 Spot: ${spot:,.2f} | THB: {thb:.2f} B\n"
        return msg
    except Exception as e:
        print(e)
        return "⚠️ Error retrieving data"

@bot.message_handler(commands=['start', 'gold'])
def send_gold(message):
    bot.reply_to(message, get_final_message())

def run_schedule():
    schedule.every().day.at("09:30").do(lambda: bot.send_message(os.getenv('TELEGRAM_CHAT_ID'), get_final_message()))
    schedule.every().day.at("13:00").do(lambda: bot.send_message(os.getenv('TELEGRAM_CHAT_ID'), get_final_message()))
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # 1. รันเว็บ Server (Thread 1)
    t_web = threading.Thread(target=run_web_server)
    t_web.start()
    
    # 2. รันตัวนับเวลา (Thread 2)
    t_sched = threading.Thread(target=run_schedule)
    t_sched.start()
    
    # 3. รันบอท (Main Process)
    print("🚀 Bot + Web Server Started!")
    bot.infinity_polling()