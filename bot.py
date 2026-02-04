import ccxt
import time
import requests
from bs4 import BeautifulSoup
import os

# ... (ส่วนตั้งค่า Binance API ของเดิมของคุณ เก็บไว้เหมือนเดิม) ...
# exchange = ccxt.binance(...) 

# ==========================================
# 🔴 ฟังก์ชั่นดึงราคาจาก Investing.com (Thai)
# ==========================================
def get_investing_price():
    url = "https://th.investing.com/currencies/xau-usd"
    # ต้องปลอมตัวเป็น Browser คนจริง เพื่อไม่ให้เว็บกันบอท
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, "html.parser")
            
            # หาตัวเลขราคา (Class นี้แม่นยำที่สุดสำหรับ Investing.com ปัจจุบัน)
            price_tag = soup.find("div", {"data-test": "instrument-price-last"})
            
            if price_tag:
                # แปลงข้อความ "2,735.50" ให้เป็นตัวเลข 2735.50
                price_text = price_tag.text.strip().replace(',', '')
                return float(price_text)
    except Exception as e:
        print(f"⚠️ ดึงราคา Investing ไม่ได้: {e}")
    
    return None

# ==========================================
# 🔄 Loop การทำงานหลัก (Main Loop)
# ==========================================
def run_bot():
    print("🚀 Bot Started: ใช้ราคาจาก Investing.com...")
    
    while True:
        try:
            # 1. ดึงราคาจาก Investing.com
            investing_price = get_investing_price()
            
            if investing_price:
                print(f"💰 ราคา Investing: ${investing_price:,.2f}")
                
                # --- เงื่อนไขการเข้าออเดอร์ (Logic) ---
                # สมมติเงื่อนไขเดิมของคุณคือเช็ค RSI หรือราคา
                # ตอนนี้เราใช้ investing_price เป็นตัวตัดสินใจหลักได้เลย
                
                # ตัวอย่าง: ถ้าอยากดึง RSI จาก Investing ด้วยจะยากกว่ามาก 
                # แนะนำให้ใช้ราคาจาก Investing เป็นตัวกรองเทรนด์ 
                # แล้วใช้ RSI จาก Binance (ที่คำนวณในโค้ดเดิม) เป็นจังหวะเข้าจะเสถียรกว่าครับ
                
            else:
                print("❌ ไม่ได้ราคาจาก Investing... รอรอบถัดไป")

            time.sleep(10) # เช็คราคาทุก 10 วินาที (อย่าถี่มาก เดี๋ยวโดนบล็อก IP)

        except Exception as e:
            print(f"Error: {e}")
            time.sleep(10)

if __name__ == "__main__":
    run_bot()
