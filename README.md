AI-Powered Menu Management Bot
โครงการนี้คือบอทอัจฉริยะที่ช่วยจัดการฐานข้อมูลเมนูร้านอาหารผ่านการสนทนา ผู้ใช้สามารถสั่งการบอทได้ง่ายๆ เพื่อเพิ่ม, แก้ไข, ลบ หรือค้นหาข้อมูลเมนูโดยไม่ต้องเขียนโค้ด SQL ด้วยตัวเอง
# 1. โครงสร้างโปรเจกต์
โปรดสร้างไฟล์และโฟลเดอร์ตามโครงสร้างด้านล่างนี้:
```
├── my_app/
│   ├── api_app.py        # Flask API สำหรับรับข้อความจาก LINE
│   ├── admin_app.py      # Streamlit UI สำหรับ Admin
│   ├── ai_processor.py   # สคริปต์หลักสำหรับประมวลผลคำตอบของ AI
│   ├── database.py       # ไฟล์จัดการฐานข้อมูล SQLite
│   └── agent_setup.py    # ไฟล์ตั้งค่า AI Agent
├── .env                  # ไฟล์เก็บตัวแปร Environment
└── requirements.txt      # รายการไลบรารีที่จำเป็น
```

# 2. การตั้งค่าเริ่มต้น
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


####ไฟล์ .env
ไฟล์นี้ใช้สำหรับเก็บ API Key และข้อมูลการเชื่อมต่อที่สำคัญ:
```
GOOGLE_API_KEY="YOUR_GOOGLE_API_KEY"
```
### สำหรับการเชื่อมต่อกับ LINE API
```
LINE_CHANNEL_ACCESS_TOKEN="YOUR_LINE_CHANNEL_ACCESS_TOKEN"
LINE_CHANNEL_SECRET="YOUR_LINE_CHANNEL_SECRET"
```

# 3. ภาพรวมการทำงาน
### ระบบนี้ใช้หลักการ LLM as a Router และ SQL Agent เพื่อแปลงคำสั่งที่เป็นภาษาธรรมชาติของผู้ใช้ให้เป็นคำสั่ง SQL ที่ถูกต้อง
## Flow การทำงานหลัก
1. รับคำสั่ง: ผู้ใช้พิมพ์คำสั่งผ่านช่องแชท
2. วิเคราะห์เจตนา: LLM จะวิเคราะห์คำสั่งของผู้ใช้และใช้ AGENT_PREFIX (คำแนะนำ) เพื่อตัดสินใจว่าควรสร้างคำสั่ง SQL ประเภทใด (เช่น SELECT, INSERT)
3. สร้างคำสั่ง: LLM สร้างคำสั่ง SQL ที่เหมาะสม
4. รันคำสั่ง: คำสั่ง SQL จะถูกส่งไปยัง Tool sql_db_query เพื่อทำงานกับฐานข้อมูล
5. สรุปผล: Agent สรุปผลลัพธ์ที่ได้จากการรันคำสั่ง และสร้างคำตอบที่เข้าใจง่ายสำหรับผู้ใช้ พร้อมแสดงคำสั่ง SQL ที่ใช้
## ตัวอย่าง Flow การทำงาน
## Flow สำหรับการค้นหาข้อมูล (SELECT)
* คำสั่ง: "มีเมนูอะไรบ้าง"
* กระบวนการ: LLM สร้างคำสั่ง SELECT menu_name FROM menu
* ผลลัพธ์: บอทแสดงรายการเมนูทั้งหมด และคำสั่ง SQL ที่ใช้

Terminal 1 (สำหรับ Flask API):
```
cd my_app
python api_app.py
```

Terminal 2 (สำหรับ AI Processor):
```
cd my_app
python ai_processor.py
```

Terminal 3 (สำหรับ Admin UI):
```
cd my_app
streamlit run admin_app.py
```

