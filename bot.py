import telebot
import requests
import schedule
import time
import threading
import os
from flask import Flask

# --- ส่วนตั้งค่า (Config) ---
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Web Server (สำหรับ UptimeRobot) ---
@app.route('/')
def home():
    return "✅ Bot is Online! (Binance US + Thai Gold)"

def run_web_server():
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- 1. ฟังก์ชันดึงทองไทย (96.5%) ---
def get_thai_gold():
    try:
        # API ของสมาคมฯ (ผ่าน chnwt)
        url = "https://api.chnwt.dev/thai-gold-api/latest"
        response = requests.get(url, timeout=10)
        data = response.json()
        
        if data['status'] == 'success':
            price = data['response']['price']['gold']
            # เช็คว่าเป็นตัวเลขไหม ถ้าไม่มีให้คืนค่าเดิม
            return {
                "sell": price['sell'],
                "buy": price['buy'],
                "date": data['response']['date'],
                "time": data['response']['update_time']
            }
    except Exception as e:
        print(f"Thai Gold Error: {e}")
    return None

# --- 2. ฟังก์ชันดึงทองนอก (99.99%) USD ---
# ใช้ Binance US หรือ CoinGecko เพราะ Server Render อยู่เมกา
def get_world_gold():
    price = None
    
    # ทางเลือกที่ A: Binance US (ดูเหรียญ PAXG ซึ่งราคา = ทองคำ 1 oz)
    try:
        url = "https://api.binance.us/api/v3/ticker/price?symbol=PAXGUSD"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            price = float(r.json()['price'])
    except Exception as e:
        print(f"Binance US Error: {e}")

    # ทางเลือกที่ B: CoinGecko (ถ้า Binance พัง ให้ใช้ตัวนี้แทน)
    if price is None:
        try:
            url = "https://api.coingecko.com/api/v3/simple/price?ids=pax-gold&vs_currencies=usd"
            headers = {'User-Agent': 'Mozilla/5.0'}
            r = requests.get(url, headers=headers, timeout=5)
            if r.status_code == 200:
                price = r.json()['pax-gold']['usd']
        except Exception as e:
            print(f"CoinGecko Error: {e}")
            
    return price

# --- รวมข้อความเพื่อส่ง ---
def get_final_message():
    thai = get_thai_gold()
    world_price = get_world_gold()
    
    msg = "📊 **ราคาทองคำ Real-Time** ⚡\n"
    msg += "━━━━━━━━━━━━━━\n"
    
    # ส่วนทองไทย
    if thai:
        msg += f"🇹🇭 **ทองไทย 96.5% (บาท)**\n"
        msg += f"🗓 {thai['date']} | 🕒 {thai['time']}\n"
        msg += f"🔴 ขายออก: **{thai['sell']}**\n"
        msg += f"🟢 รับซื้อ: **{thai['buy']}**\n"
    else:
        msg += "🇹🇭 ทองไทย: (เชื่อมต่อไม่ได้)\n"
        
    msg += "━━━━━━━━━━━━━━\n"
    
    # ส่วนทองนอก
    if world_price:
        msg += f"🌎 **ทองคำโลก 99.99% (Spot)**\n"
        msg += f"🇺🇸 **XAU/USD:** ${world_price:,.2f}\n"
    else:
        msg += "🌎 ทองโลก: (เชื่อมต่อไม่ได้)\n"
    
    msg += "━━━━━━━━━━━━━━\n"
    msg += "DATA: Gold Traders Assoc. & Binance US"
    
    return msg

# --- คำสั่ง Telegram ---
@bot.message_handler(commands=['start', 'gold'])
def send_gold(message):
    bot.reply_to(message, "🔍 กำลังดึงข้อมูล...")
    try:
        text = get_final_message()
        # ลบข้อความเก่าแล้วส่งใหม่ หรือแก้ไขข้อความเดิมก็ได้ (ที่นี้ส่งใหม่)
        bot.send_message(message.chat.id, text, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(message.chat.id, "เกิดข้อผิดพลาดในการส่งข้อมูล")

# --- ตั้งเวลาแจ้งเตือนอัตโนมัติ ---
def run_schedule():
    target_chat_id = os.getenv('TELEGRAM_CHAT_ID')
    
    def job():
        if target_chat_id:
            try:
                bot.send_message(target_chat_id, get_final_message(), parse_mode='Markdown')
            except Exception as e:
                print(f"Schedule Error: {e}")

    # ตั้งเวลาส่ง (เปลี่ยนเวลาตรงนี้ได้)
    schedule.every().day.at("09:30").do(job)
    schedule.every().day.at("14:00").do(job)
    schedule.every().day.at("16:00").do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

# --- Main Loop ---
if __name__ == "__main__":
    # รัน Web Server (เพื่อให้ Render ไม่หลับ)
    t_web = threading.Thread(target=run_web_server)
    t_web.start()
    
    # รัน Scheduler (ตัวจับเวลา)
    t_sched = threading.Thread(target=run_schedule)
    t_sched.start()
    
    print("🚀 Bot Started Successfully!")
    bot.infinity_polling()
