import telebot
import requests
import time
import threading
import os
import pandas as pd
import yfinance as yf
import matplotlib
matplotlib.use('Agg') # ตั้งค่าให้ทำงานแบบไม่มีหน้าจอ (สำคัญสำหรับ Cloud)
import matplotlib.pyplot as plt
import io
from flask import Flask

# --- Config ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Web Server ---
@app.route('/')
def home():
    return "✅ Gold Bot V.3 (Chart Master) is Running..."

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- 🧠 สมองคำนวณ Indicator (Math Core) ---
def calculate_indicators(df):
    # RSI (14)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    loss = (-delta.where(delta < 0, 0)).ewm(alpha=1/14, adjust=False).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD (12, 26, 9)
    k = df['Close'].ewm(span=12, adjust=False, min_periods=12).mean()
    d = df['Close'].ewm(span=26, adjust=False, min_periods=26).mean()
    df['MACD'] = k - d
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False, min_periods=9).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    return df

# --- 🎨 จิตรกรวาดกราฟ (Chart Artist) ---
def create_chart_image(df):
    # สร้างกระดานวาดภาพ 3 ช่องแนวตั้ง (Price, RSI, MACD)
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(10, 12), gridspec_kw={'height_ratios': [2, 1, 1]})
    plt.style.use('seaborn-v0_8-darkgrid') # ธีมมืดสวยๆ

    # ช่องที่ 1: ราคาทอง (Price)
    ax1.set_title('Gold Spot (GC=F) - 15m Timeframe', fontsize=14, fontweight='bold', color='white', backgroundcolor='#1f77b4')
    ax1.plot(df.index, df['Close'], label='Price (USD)', color='#FFD700', linewidth=2)
    ax1.set_ylabel('Price ($)')
    ax1.legend(loc='upper left')

    # ช่องที่ 2: RSI
    ax2.set_title('RSI (14)', fontsize=12)
    ax2.plot(df.index, df['RSI'], color='#00BFFF', linewidth=1.5)
    ax2.axhline(70, color='red', linestyle='--', alpha=0.5) # เส้น Overbought
    ax2.axhline(30, color='green', linestyle='--', alpha=0.5) # เส้น Oversold
    ax2.fill_between(df.index, df['RSI'], 70, where=(df['RSI']>=70), facecolor='red', alpha=0.3)
    ax2.fill_between(df.index, df['RSI'], 30, where=(df['RSI']<=30), facecolor='green', alpha=0.3)
    ax2.set_ylabel('RSI')
    ax2.set_ylim(0, 100)

    # ช่องที่ 3: MACD
    ax3.set_title('MACD (12,26,9)', fontsize=12)
    ax3.plot(df.index, df['MACD'], label='MACD', color='cyan', linewidth=1.5)
    ax3.plot(df.index, df['MACD_Signal'], label='Signal', color='magenta', linestyle='--', linewidth=1)
    # วาด Histogram
    colors = ['green' if val >= 0 else 'red' for val in df['MACD_Hist']]
    ax3.bar(df.index, df['MACD_Hist'], color=colors, alpha=0.5, width=0.01)
    ax3.set_ylabel('MACD')
    ax3.legend(loc='upper left')

    plt.tight_layout()
    
    # บันทึกภาพลงหน่วยความจำ (ไม่เซฟลงไฟล์)
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    plt.close(fig) # ปิดกระดานเพื่อคืน Ram
    return buf

# --- 🔍 ดึงข้อมูลรวม ---
def get_market_data_and_chart():
    try:
        tickers = "GC=F THB=X"
        data = yf.download(tickers, period="5d", interval="15m", progress=False, group_by='ticker')
        
        # ข้อมูลทอง + คำนวณ
        gold_df = data['GC=F'].copy()
        if gold_df.empty or len(gold_df) < 30: return None, None
        gold_df = calculate_indicators(gold_df)
        
        # ข้อมูลเงินบาท
        thb_price = float(data['THB=X']['Close'].iloc[-1])

        # สร้างรูปภาพ
        chart_buffer = create_chart_image(gold_df)

        # ข้อมูลสรุปตัวเลข
        summary = {
            "price": float(gold_df['Close'].iloc[-1]),
            "rsi": float(gold_df['RSI'].iloc[-1]),
            "macd": float(gold_df['MACD'].iloc[-1]),
            "macds": float(gold_df['MACD_Signal'].iloc[-1]),
            "thb": thb_price
        }
        return summary, chart_buffer

    except Exception as e:
        print(f"Error: {e}")
        return None, None

# --- 💬 จัดข้อความ Caption ---
def format_caption(data, alert_type=None):
    msg = ""
    if alert_type == "HIGH": msg += "🔥 **แจ้งเตือน: RSI สูงเดือด! (Overbought)**\n"
    elif alert_type == "LOW": msg += "⚡ **แจ้งเตือน: RSI ต่ำน่าเก็บ! (Oversold)**\n"
    else: msg += "📸 **Gold Technical Chart (15m)**\n"

    msg += f"💰 XAU/USD: **${data['price']:,.2f}**\n"
    msg += f"🇹🇭 USD/THB: **{data['thb']:.2f} บ.**\n"
    msg += "━━━━━━━━━━━━━━\n"
    
    rsi = data['rsi']
    rsi_icon = "🔴" if rsi >= 70 else ("🔵" if rsi <= 30 else "🟢")
    msg += f"{rsi_icon} RSI: **{rsi:.2f}**\n"

    macd_msg = "Bullish (ขาขึ้น) 📈" if data['macd'] > data['macds'] else "Bearish (ขาลง) 📉"
    msg += f"🌊 MACD: **{macd_msg}**"
    
    return msg

# --- 🐕 เฝ้าบ้าน (ส่งรูปเมื่อเตือน) ---
def run_watchdog():
    print("👀 Watchdog V.3 Started...")
    while True:
        try:
            data, chart = get_market_data_and_chart()
            if data and chart and CHAT_ID:
                rsi = data['rsi']
                print(f"Check: ${data['price']:.1f} | RSI: {rsi:.1f}")
                
                alert = None
                if rsi >= 70: alert = "HIGH"
                elif rsi <= 30: alert = "LOW"
                
                if alert:
                    # ส่งทั้งรูปและข้อความ
                    bot.send_photo(CHAT_ID, chart, caption=format_caption(data, alert), parse_mode='Markdown')
                    time.sleep(900) # พัก 15 นาที
            
            time.sleep(60)
        except Exception as e:
            print(f"Watchdog Error: {e}")
            time.sleep(60)

# --- Commands (ส่งรูปเมื่อสั่ง) ---
@bot.message_handler(commands=['start', 'check', 'chart'])
def send_status(message):
    bot.send_chat_action(message.chat.id, 'upload_photo') # ขึ้นสถานะว่ากำลังอัปรูป
    data, chart = get_market_data_and_chart()
    if data and chart:
        bot.send_photo(message.chat.id, chart, caption=format_caption(data), parse_mode='Markdown')
    else:
        bot.send_message(message.chat.id, "❌ สร้างกราฟไม่สำเร็จ ลองใหม่ครับ")

# --- Run ---
if __name__ == "__main__":
    # ตั้งค่า Matplotlib สำหรับ Cloud
    plt.switch_backend('Agg') 
    
    t_web = threading.Thread(target=run_web_server)
    t_web.start()
    t_watch = threading.Thread(target=run_watchdog)
    t_watch.start()
    bot.infinity_polling()
