import ccxt
import time
import requests
import os
import sys
from bs4 import BeautifulSoup
from flask import Flask
from threading import Thread

# =======================================================
# ⚙️ ส่วนตั้งค่า (CONFIG)
# =======================================================
# แนะนำให้ตั้งค่าใน Render -> Environment Variables เพื่อความปลอดภัย
# หรือถ้าทดสอบจะใส่ตรงๆ ตรงนี้ก็ได้ (ไม่แนะนำให้เผยแพร่)
TG_TOKEN = os.environ.get('TG_TOKEN', 'ใส่_TOKEN_ของคุณ_ถ้าไม่ตั้งในRender')
TG_CHAT_ID = os.environ.get('TG_CHAT_ID', 'ใส่_CHAT_ID_ของคุณ_ถ้าไม่ตั้งในRender')

API_KEY = os.environ.get('BINANCE_API_KEY', 'ใส่_API_KEY')
API_SECRET = os.environ.get('BINANCE_SECRET_KEY', 'ใส่_SECRET_KEY')

SYMBOL = 'XAU/USDT'  # หรือ XAU/USD แล้วแต่ Exchange

# =======================================================
# 🟢 1. Web Server (เพื่อให้ Render ไม่หลับ)
# =======================================================
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Bot is Alive! (Gold Trader Running...)"

def run_web_server():
    # Render จะส่งค่า PORT มาให้เอง
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# =======================================================
# 🔵 2. ระบบแจ้งเตือน Telegram
# =======================================================
def send_telegram(message):
    try:
        if 'ใส่_' in TG_TOKEN or 'ใส่_' in TG_CHAT_ID:
            print("⚠️ กรุณาตั้งค่า TG_TOKEN และ TG_CHAT_ID ก่อน")
            return

        url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
        params = {'chat_id': TG_CHAT_ID, 'text': message}
        requests.get(url, params=params, timeout=5)
        print(f"💬 ส่ง Telegram: {message}")
    except Exception as e:
        print(f"❌ ส่ง Telegram ไม่ผ่าน: {e}")

# =======================================================
# 🟡 3. ดึงราคาจาก Investing.com
# =======================================================
def get_investing_price():
    url = "https://th.investing.com/currencies/xau-usd"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://www.google.com/"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            # หา Element ราคา (อาจต้องอัปเดตถ้าเว็บเปลี่ยนโครงสร้าง)
            price_tag = soup.find("div", {"data-test": "instrument-price-last"})
            
            if price_tag:
                price_text = price_tag.text.strip().replace(',', '')
                return float(price_text)
    except Exception as e:
        print(f"⚠️ ดึงราคา Investing ผิดพลาด: {e}")
    
    return None

# =======================================================
# 🟣 4. ระบบ Auto TP 6 ไม้ (Smart Take Profit)
# =======================================================
def place_smart_tp(exchange, symbol, entry_price, position_size, side='sell'):
    print(f"⚡ เริ่มวางแผน TP 6 ไม้ สำหรับ {symbol} ขา {side}...")
    
    tp_percents = [0.005, 0.010, 0.020, 0.030, 0.050, 0.100] # 0.5% - 10%
    qty_splits = [0.15, 0.15, 0.15, 0.15, 0.20, 0.20] # รวมได้ 100%

    try:
        for i in range(len(tp_percents)):
            percent = tp_percents[i]
            split = qty_splits[i]
            
            if side == 'sell': # ขา Short -> ตั้ง Buy คืน
                target_price = entry_price * (1 - percent)
                order_side = 'buy'
            else: # ขา Long -> ตั้ง Sell คืน
                target_price = entry_price * (1 + percent)
                order_side = 'sell'

            amount = position_size * split
            
            # ปรับทศนิยมให้ตรงกฎ Exchange (สำคัญมาก)
            amount = exchange.amount_to_precision(symbol, amount)
            target_price = exchange.price_to_precision(symbol, target_price)

            # ส่งคำสั่ง Limit (Reduce Only)
            # หมายเหตุ: uncomment บรรทัดล่างเมื่อต่อ API จริง
            # exchange.create_order(symbol, 'limit', order_side, amount, target_price, params={'reduceOnly': True})
            
            msg = f"🎯 TP{i+1}: ตั้ง {order_side} {amount} หน่วย @ ${target_price}"
            print(msg)
            # send_telegram(msg) # ส่งบอกในไลน์ด้วยก็ได้
            
            time.sleep(0.2) # พักนิดนึง

        send_telegram(f"✅ ตั้ง TP 6 ไม้ ครบเรียบร้อย! (Entry: {entry_price})")

    except Exception as e:
        print(f"❌ ตั้ง TP ล้มเหลว: {e}")
        send_telegram(f"❌ Error ตั้ง TP: {e}")

# =======================================================
# 🚀 5. ส่วนควบคุมหลัก (Main Loop)
# =======================================================
def run_bot_logic():
    print("🤖 บอทเริ่มทำงาน... (รอราคาแป๊บนึง)")
    send_telegram("🚀 Serverless Gold Bot เริ่มทำงานแล้วครับ!")

    # เชื่อมต่อ Binance (ถ้าไม่มี Key จะข้ามการเชื่อมต่อ)
    exchange = None
    try:
        if 'ใส่_' not in API_KEY:
            exchange = ccxt.binance({
                'apiKey': API_KEY,
                'secret': API_SECRET,
                'options': {'defaultType': 'future'} # เทรดฟิวเจอร์
            })
            print("✅ เชื่อมต่อ Binance สำเร็จ")
    except Exception as e:
        print(f"⚠️ เชื่อมต่อ Binance ไม่ได้: {e}")

    # ตัวแปรจำสถานะ
    last_price = 0
    
    while True:
        try:
            # 1. ดึงราคา
            current_price = get_investing_price()
            
            if current_price:
                print(f"💰 Investing Gold Price: ${current_price:,.2f}")
                
                # --- LOGIC การเทรด ใส่ตรงนี้ ---
                # ตัวอย่าง: ถ้าราคาเปลี่ยนเยอะๆ ให้แจ้งเตือน
                if last_price > 0 and abs(current_price - last_price) > 10:
                    send_telegram(f"🔔 ราคาทองขยับแรง! ตอนนี้ ${current_price:,.2f}")
                
                # ตัวอย่าง: สมมติว่า RSI บอกให้ขาย (ใส่ Logic จริงของคุณแทนตรงนี้)
                # if rsi > 70 and exchange:
                #     order = exchange.create_market_sell_order(SYMBOL, 0.01)
                #     place_smart_tp(exchange, SYMBOL, order['price'], 0.01, 'sell')

                last_price = current_price
            else:
                print("⏳ กำลังดึงราคา...")

            # พัก 20 วินาที (Investing กันบอท ถ้าถี่เกินจะโดนแบน)
            time.sleep(20)

        except Exception as e:
            print(f"❌ Main Loop Error: {e}")
            time.sleep(20)

# =======================================================
# 🔥 เริ่มต้นการทำงาน (Threading)
# =======================================================
if __name__ == "__main__":
    # 1. รัน Web Server แยกไปอีก Thread
    t_server = Thread(target=run_web_server)
    t_server.start()

    # 2. รันบอทเทรดที่ Thread หลัก
    run_bot_logic()
