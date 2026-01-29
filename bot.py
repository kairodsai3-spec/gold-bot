import telebot
import requests
from bs4 import BeautifulSoup
import schedule
import time
import threading
import os
import urllib3
from flask import Flask

# ปิดแจ้งเตือนความปลอดภัย SSL (เพื่อให้ดึงข้อมูลได้ลื่นๆ)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# --- ตั้งค่า ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- หน้าเว็บหลอกๆ กันบอทหลับ ---
@app.route('/')
def home():
    return "Bot is watching Gold Prices..."

def run_web_server():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

# --- ฟังก์ชันดึงข้อมูล (ดึงจากนำเชียง ทีเดียวจบ) ---
def get_gold_data():
    try:
        url = "https://www.namchiang.com/th/"
        # หลอกว่าเป็นคนเปิดเว็บ (ไม่ใช่บอท)
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.content, 'html.parser')

        # ดึงข้อมูลตาม ID หน้าเว็บเขา
        data = {
            "sell_965": soup.find(id='lblBLSell').text.strip(),
            "buy_965": soup.find(id='lblBLBuy').text.strip(),
            "sell_99": soup.find(id='lbl99Sell').text.strip(),
            "buy_99": soup.find(id='lbl99Buy').text.strip(),
            "gold_spot": soup.find(id='lblSpot').text.strip(), # นี่คือ Gold US ที่คุณอยากได้
            "thb_usd": soup.find(id='lblUS').text.strip(),
            "update_time": soup.find(id='lblTime').text.strip()
        }
        return data

    except Exception as e:
        print(f"Error scraping: {e}")
        return None

# --- จัดหน้าตาข้อความ ---
def get_message():
    data = get_gold_data()
    
    if not data:
        return "⚠️ กำลังดึงข้อมูล... (ลองกดใหม่ใน 1 นาที)"

    msg = (
        f"📊 **ราคาทองคำ Real-Time** 🚀\n"
        f"🕒 เวลา: {data['update_time']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🇹🇭 **ทองคำแท่ง 96.5% (บาท)**\n"
        f"🔴 ขายออก: {data['sell_965']}\n"
        f"🟢 รับซื้อ: {data['buy_965']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"✨ **ทองคำ 99.99% (บาท)**\n"
        f"🔴 ขายออก: {data['sell_99']}\n"
        f"🟢 รับซื้อ: {data['buy_99']}\n"
        f"━━━━━━━━━━━━━━\n"
        f"🌎 **ตลาดโลก (Global)**\n"
        f"🇺🇸 **Gold US:** {data['gold_spot']} USD\n" # ตรงนี้ครับ
        f"💵 **Exchange:** {data['thb_usd']} THB/USD\n"
        f"━━━━━━━━━━━━━━\n"
        f"(Data: Nam Chiang)"
    )
    return msg

# --- ส่วนบอท ---
@bot.message_handler(commands=['start', 'gold'])
def send_gold(message):
    bot.reply_to(message, get_message())

# --- ตั้งเวลาแจ้งเตือน ---
def run_schedule():
    target_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    def job():
        if target_chat_id:
            bot.send_message(target_chat_id, get_message())
            
    schedule.every().day.at("09:35").do(job)
    schedule.every().day.at("14:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    # รัน 2 ระบบพร้อมกัน
    t_web = threading.Thread(target=run_web_server)
    t_web.start()
    
    t_sched = threading.Thread(target=run_schedule)
    t_sched.start()
    
    print("🚀 Gold Bot (Nam Chiang Edition) Started!")
    bot.infinity_polling()
