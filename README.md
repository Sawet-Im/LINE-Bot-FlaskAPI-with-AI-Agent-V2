# LINE Bot Flask with AI Agent 
โปรเจคนี้คือบอทอัจฉริยะที่ช่วยตอบข้อมูลเมนูร้านอาหาร โปรโมชั่นผ่านการสนทนา ผู้ใช้สามารถสั่งการบอทได้ง่ายๆ ค้นหาข้อมูลเมนูโดยไม่ต้องเขียนโค้ด SQL ด้วยตัวเอง พร้อมเว็บแอปพลิเคชันที่สร้างด้วย Flask สำหรับเชื่อมต่อกับ LINE Messaging API โดยจะทำหน้าที่เป็น Webhook เพื่อรับ-ส่งข้อความ และสามารถบันทึกข้อมูล Channel API ลงในฐานข้อมูล SQLite ได้

# คุณสมบัติหลัก
* บอทอัจฉริยะที่ช่วยตอบข้อมูลเมนูร้านอาหาร โปรโมชั่นผ่านการสนทนา
* การตั้งค่า Webhook อัตโนมัติ: เมื่อกรอกข้อมูล Channel API จะทำการอัปเดต Webhook URL บน LINE Developers ให้โดยอัตโนมัติ
* การจัดเก็บข้อมูล: จัดเก็บ Channel Secret และ Channel Access Token ไว้ในฐานข้อมูล SQLite ที่สร้างขึ้นภายในเครื่อง
* การจัดการ Webhook แบบไดนามิก: สามารถจัดการ Webhook สำหรับผู้ใช้หลายคนโดยใช้ User ID เป็นตัวระบุ

# 1. โครงสร้างโปรเจกต์
โปรดสร้างไฟล์และโฟลเดอร์ตามโครงสร้างด้านล่างนี้:
```
├── my_app/
│   ├── index.html        # การตั้งค่า Webhook อัตโนมัติ
│   ├── api_app.py        # Flask API สำหรับรับข้อความจาก LINE
│   ├── admin_app.py      # Streamlit UI สำหรับ Admin
│   ├── ai_processor.py   # สคริปต์หลักสำหรับประมวลผลคำตอบของ AI
│   ├── database.py       # ไฟล์จัดการฐานข้อมูล SQLite
│   └── agent_setup.py    # ไฟล์ตั้งค่า AI Agent
├── .env                  # ไฟล์เก็บตัวแปร Environment
└── requirements.txt      # รายการไลบรารีที่จำเป็น
```

# 2. การติดตั้งและการตั้งค่า

## 2.1. สิ่งที่ต้องมีก่อนเริ่ม
* Python 3.7 หรือใหม่กว่า
* pip (ตัวจัดการแพ็กเกจของ Python)
* ngrok (สำหรับเปิด Local Server ให้เข้าถึงได้จากภายนอก)

## 2.2. ติดตั้งแพ็กเกจที่จำเป็น
ไฟล์ requirements.txt
ติดตั้งไลบรารีที่จำเป็นทั้งหมดด้วยคำสั่ง:
```
pip install -r requirements.txt
```

ไฟล์นี้มีรายการดังต่อไปนี้:
```
streamlit
python-dotenv
langchain
langchain-google-genai
langchain-community
langchain-core
langchain-ollama
Flask
line-bot-sdk
```

## 2.3 ตั้งค่าตัวแปรสภาพแวดล้อม (Environment Variables)
### สร้างไฟล์ชื่อ .env ในโฟลเดอร์เดียวกับไฟล์ api_app.py และเพิ่ม Channel Secret ของคุณลงไปในบรรทัดแรก:
```
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
```
### สำหรับการเชื่อมต่อกับ LINE API
```
LINE_CHANNEL_ACCESS_TOKEN="YOUR_LINE_CHANNEL_ACCESS_TOKEN"
LINE_CHANNEL_SECRET="YOUR_LINE_CHANNEL_SECRET"
```

# 3. รันโปรเจกต์และตั้งค่า ngrok
## 3.1 เปิด Terminal1 รันคำสั่ง ngrok เพื่อเปิด Public URL:
```
ngrok http 9000
```
คุณจะได้รับ Public URL ที่ขึ้นต้นด้วย https:// (เช่น https://example.ngrok-free.app) โปรด คัดลอก URL นี้ไว้
## 3.2 ขั้นตอนสำคัญ: เปิดไฟล์ api_app.py แล้วนำ URL ที่คัดลอกมาไปวางแทนที่ค่าของตัวแปร base_url ตามโค้ดตัวอย่างด้านล่าง:
```
# V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V
#
# >>> ขั้นตอนที่สำคัญมาก: โปรดนำ Public URL จาก ngrok มาวางที่นี่
#
# ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^
#
base_url = "[https://example.ngrok-free.app](https://example.ngrok-free.app)" # วาง URL ngrok ของคุณที่นี่

```
## 3.3 Terminal 2 (สำหรับ Flask API):
เปิด Terminal หน้าที่สองและรันคำสั่ง:
```
source venv/bin/activate 
cd my_app
python api_app.py
```
## 3.4 Terminal 3 (สำหรับ AI Processor):
```
source venv/bin/activate 
cd my_app
python ai_processor.py
```

## 3.5 Terminal 4 (สำหรับ Admin UI):
```
source venv/bin/activate 
cd my_app
streamlit run admin_app.py
```

# 4. ตั้งค่าบนหน้าเว็บ
## 4.1เปิดเว็บเบราว์เซอร์แล้วไปที่ http://localhost:9000
## 4.2กรอก Channel Secret และ Channel Access Token ของคุณ
## 4.3กดปุ่ม "บันทึกและสร้าง Webhook"
หากทุกอย่างถูกต้อง หน้าเว็บจะแสดงข้อความว่า "Webhook URL updated successfully." พร้อมกับ Webhook URL ที่สมบูรณ์

# 5. การใช้งาน
เมื่อ Webhook URL ได้รับการอัปเดตแล้ว คุณสามารถส่งข้อความไปยัง LINE Official Account ของคุณได้เลยครับ
ระบบจะทำงานตามโค้ดที่คุณเขียนไว้ในฟังก์ชัน callback เพื่อรับข้อความและตอบกลับโดยอัตโนมัติ

หากมีข้อสงสัยหรือปัญหาเพิ่มเติม สามารถสอบถามได้เลยครับ
# LINE-Bot-Flask-with-AI-Agent-V1
