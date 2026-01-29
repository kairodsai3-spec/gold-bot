# ใช้น้ำยา Python ตัวเล็กเบาๆ
FROM python:3.9-slim

# ตั้งโฟลเดอร์ทำงาน
WORKDIR /app

# ตั้งเวลาให้ตรงกับไทย (สำคัญมาก ไม่งั้นบอทจะงงเวลา)
RUN apt-get update && apt-get install -y tzdata
ENV TZ=Asia/Bangkok

# ก๊อปปี้ไฟล์รายการของ และติดตั้ง
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ก๊อปปี้โค้ดบอททั้งหมดลงไป
COPY . .

# คำสั่งรันเมื่อเปิดตู้
CMD ["python", "bot.py"]