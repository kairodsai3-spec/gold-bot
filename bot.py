import telebot
import requests
import time
import threading
import os
import pandas as pd
import pandas_ta as ta
import yfinance as yf
from flask import Flask

# --- ตั้งค่า (Config) ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Web Server (สำหรับ UptimeRobot) ---
@app.route('/')
def home():
    return "✅ Gold RSI Bot is Running..."

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- ฟังก์ชันคำนวณ RSI (หัวใจสำคัญ) ---
def get_technical_analysis():
    try:
        # ดึงข้อมูลทองคำ Gold Futures (GC=F) ย้อนหลัง 5 วัน ราย 15 นาที
        # ใช้ yfinance แทน ccxt เพื่อหนีการโดนบล็อก IP
        df = yf.download("GC=F", period="5d", interval="15m", progress=False)
        
        if df.empty:
            return None, None

        # คำนวณ RSI (14) ด้วย pandas_ta (เหมือนโค้ดที่คุณให้มา)
        df.ta.rsi(length=14, append=True)
        
        last_price = df['Close'].iloc[-1].item() # ราคาปิดล่าสุด
        last_rsi = df['RSI_14'].iloc[-1].item()   # ค่า RSI ล่าสุด

        return last_price, last_rsi
    except Exception as e:
        print(f"Error Calculating RSI: {e}")
        return None, None

# --- ฟังก์ชันข้อความสวยๆ ---
def format_message(price, rsi, alert_type=None):
    msg = ""
    if alert_type == "HIGH":
        msg += "🔥 **แจ้งเตือน: RSI สูงผิดปกติ!** 🔥\n"
        msg += "⚠️ ระวังแรงเทขาย (Overbought)\n"
    elif alert_type == "LOW":
        msg += "⚡ **แจ้งเตือน: RSI ต่ำน่าซื้อ!** ⚡\n"
        msg += "✅ จังหวะช้อนซื้อ (Oversold)\n"
    else:
        msg += "📊 **สถานะตลาดปัจจุบัน**\n"

    msg += "━━━━━━━━━━━━━━\n"
    msg += f"💰 ราคา: **${price:,.2f}**\n"
    msg += f"📈 RSI (15m): **{rsi:.2f}**\n"
    
    # คำแนะนำตาม RSI
    if rsi >= 70:
        msg += "🚩 Status: **Overbought (แพงไป)**"
    elif rsi <= 30:
        msg += "🚩 Status: **Oversold (ถูกมาก)**"
    else:
        msg += "⚖️ Status: Neutral (ปกติ)"
        
    return msg

# --- บอทเฝ้าระวัง (Watchdog) ---
def run_watchdog():
    print("👀 เริ่มต้นระบบเฝ้าระวัง RSI...")
    while True:
        try:
            price, rsi = get_technical_analysis()
            
            if price and rsi:
                print(f"Check: Price={price:.1f}, RSI={rsi:.1f}")
                
                # เงื่อนไขแจ้งเตือน (RSI > 70 หรือ < 30)
                # เช็คว่ามี Chat ID ไหม ถ้ามีให้ส่ง
                if CHAT_ID:
                    if rsi >= 70:
                        bot.send_message(CHAT_ID, format_message(price, rsi, "HIGH"), parse_mode='Markdown')
                        time.sleep(900) # ถ้าเตือนแล้ว ให้พัก 15 นาที (กันรัว)
                    elif rsi <= 30:
                        bot.send_message(CHAT_ID, format_message(price, rsi, "LOW"), parse_mode='Markdown')
                        time.sleep(900) # ถ้าเตือนแล้ว ให้พัก 15 นาที
            
            # ตรวจสอบทุกๆ 1 นาที
            time.sleep(60) 
            
        except Exception as e:
            print(f"Watchdog Error: {e}")
            time.sleep(60)

# --- คำสั่งเช็คสถานะเอง ---
@bot.message_handler(commands=['start', 'check', 'rsi'])
def send_status(message):
    bot.reply_to(message, "🔄 กำลังวิเคราะห์กราฟ...")
    price, rsi = get_technical_analysis()
    
    if price:
        bot.reply_to(message, format_message(price, rsi), parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ ดึงข้อมูลกราฟไม่ได้ ลองใหม่แป๊บหนึ่งครับ")

# --- Main ---
if __name__ == "__main__":
    # 1. รัน Web Server กันหลับ
    t_web = threading.Thread(target=run_web_server)
    t_web.start()
    
    # 2. รันระบบเฝ้าระวัง (Loop ตรวจจับ RSI)
    t_watch = threading.Thread(target=run_watchdog)
    t_watch.start()
    
    print("🚀 Hybrid Bot (RSI Alert) Started!")
    bot.infinity_polling()
