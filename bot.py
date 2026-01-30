import telebot
import requests
import time
import threading
import os
import pandas as pd
import yfinance as yf
from flask import Flask

# --- ตั้งค่า (Config) ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Web Server ---
@app.route('/')
def home():
    return "✅ Gold Bot (Manual RSI) is Running..."

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- ฟังก์ชันคำนวณ RSI (สูตรคณิตศาสตร์) ---
# เราเขียนเอง ไม่ง้อ pandas_ta แล้ว เพื่อแก้ปัญหา Error 404
def calculate_rsi(df, period=14):
    # หาความเปลี่ยนแปลงของราคา
    delta = df['Close'].diff()
    
    # แยกขาขึ้น (Gain) และขาลง (Loss)
    gain = (delta.where(delta > 0, 0))
    loss = (-delta.where(delta < 0, 0))

    # คำนวณค่าเฉลี่ยแบบ Exponential (Wilder's Smoothing) ให้เหมือน TradingView
    avg_gain = gain.ewm(alpha=1/period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, adjust=False).mean()

    # คำนวณ RS และ RSI
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- ฟังก์ชันดึงข้อมูลและวิเคราะห์ ---
def get_technical_analysis():
    try:
        # ดึงกราฟทองคำ (GC=F) ย้อนหลัง 5 วัน แท่งละ 15 นาที
        df = yf.download("GC=F", period="5d", interval="15m", progress=False)
        
        if df.empty or len(df) < 15:
            return None, None

        # เรียกใช้สูตรคำนวณ RSI ที่เราเขียนเอง
        df['RSI'] = calculate_rsi(df)
        
        # เอาค่าล่าสุด
        last_price = float(df['Close'].iloc[-1])
        last_rsi = float(df['RSI'].iloc[-1])

        return last_price, last_rsi
    except Exception as e:
        print(f"Error: {e}")
        return None, None

# --- จัดรูปแบบข้อความ ---
def format_message(price, rsi, alert_type=None):
    msg = ""
    if alert_type == "HIGH":
        msg += "🔥 **แจ้งเตือน: RSI สูง (Overbought)** 🔥\n"
        msg += "⚠️ ระวังแรงเทขาย\n"
    elif alert_type == "LOW":
        msg += "⚡ **แจ้งเตือน: RSI ต่ำ (Oversold)** ⚡\n"
        msg += "✅ จังหวะน่าเข้าซื้อ\n"
    else:
        msg += "📊 **สถานะทองคำล่าสุด**\n"

    msg += "━━━━━━━━━━━━━━\n"
    msg += f"💰 ราคา: **${price:,.2f}**\n"
    msg += f"📈 RSI (15m): **{rsi:.2f}**\n"
    
    if rsi >= 70: msg += "🚩 สถานะ: แพงเกินไป (ระวังดอย)"
    elif rsi <= 30: msg += "🚩 สถานะ: ถูกมาก (ของดีราคาถูก)"
    else: msg += "⚖️ สถานะ: ทั่วไป (Neutral)"
        
    return msg

# --- ระบบเฝ้าระวัง ---
def run_watchdog():
    print("👀 Watchdog Started...")
    while True:
        try:
            price, rsi = get_technical_analysis()
            if price and rsi:
                print(f"Monitor: ${price:.2f} | RSI: {rsi:.2f}")
                
                if CHAT_ID:
                    if rsi >= 70:
                        bot.send_message(CHAT_ID, format_message(price, rsi, "HIGH"), parse_mode='Markdown')
                        time.sleep(900) # พัก 15 นาที
                    elif rsi <= 30:
                        bot.send_message(CHAT_ID, format_message(price, rsi, "LOW"), parse_mode='Markdown')
                        time.sleep(900)
            
            time.sleep(60) # ตรวจทุก 1 นาที
        except Exception as e:
            print(f"Watchdog Error: {e}")
            time.sleep(60)

# --- คำสั่ง Telegram ---
@bot.message_handler(commands=['start', 'check', 'rsi'])
def send_status(message):
    bot.reply_to(message, "🔄 กำลังคำนวณ RSI...")
    price, rsi = get_technical_analysis()
    if price:
        bot.send_message(message.chat.id, format_message(price, rsi), parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ ไม่สามารถดึงข้อมูลได้ขณะนี้")

# --- Main ---
if __name__ == "__main__":
    t_web = threading.Thread(target=run_web_server)
    t_web.start()
    
    t_watch = threading.Thread(target=run_watchdog)
    t_watch.start()
    
    print("🚀 Gold Bot (Native Calculation) Started!")
    bot.infinity_polling()
