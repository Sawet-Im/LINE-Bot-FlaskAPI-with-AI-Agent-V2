# LINE Bot Flask with AI Agent V2
โปรเจคนี้คือบอทอัจฉริยะที่ใช้โมเดลภาษาขนาดใหญ่ (LLM) อย่าง Google Gemini ร่วมกับเฟรมเวิร์ก LangChain เพื่อทำหน้าที่เป็น AI Agent ในการจัดการและตอบคำถามเกี่ยวกับสินค้า/บริการของร้านค้า โดยสามารถเข้าถึงฐานข้อมูล SQL (SQLite) เพื่อค้นหาข้อมูลเมนู โปรโมชัน ด้วยตัวเอง พร้อมFlaskAPI สำหรับเชื่อมต่อกับ LINE Messaging API โดยจะทำหน้าที่เป็น Webhook เพื่อรับ-ส่งข้อความ และสามารถบันทึกข้อมูล Channel API ลงในฐานข้อมูล SQLite ได้

# 🌟 คุณสมบัติหลัก
* SQL Access via Agent: Agent สามารถสร้างและรันคำสั่ง SQL (SELECT, INSERT, UPDATE) กับฐานข้อมูล SQLite เพื่อดึงข้อมูลแบบ Real-time
* Dynamic Context & Filtering: Agent ถูกตั้งค่าให้รับ Store ID และ Store Name ตั้งแต่เริ่มต้น ทำให้การกรองข้อมูลใน SQL แม่นยำและป้องกันการข้ามร้านค้าได้
* Conversation Memory: ใช้ ConversationBufferMemory เพื่อเก็บประวัติการสนทนา ทำให้ Agent จดจำข้อจำกัดของลูกค้า (เช่น "ไม่ทานเนื้อ", "แพ้อาหารทะเล") และรวมเงื่อนไขในการค้นหาเมนูได้
* API Integration: เชื่อมต่อกับ LINE Messaging API ผ่าน Webhook และใช้ Flask/Gunicorn เพื่อรองรับการทำงานใน Production
* เชื่อมต่อ Webhook LINE ให้อัตโนมัติ
* สามารถเลือกให้ AI ตอบอัตโนมัติ หรือ AI สร้างข้อความให้ admin แก้ไขคำตอบได้

# 1. โครงสร้างโปรเจกต์
โปรดสร้างไฟล์และโฟลเดอร์ตามโครงสร้างด้านล่างนี้:
```
├── templates/
│   ├── dashboard.html    # dashboard สำหรับดูแชท
│   ├── setup.html        # กรอก Channel Secret และ Channel Access Token ของคุณ
├── my_app/
│   ├── api_app.py        # ไฟล์ FlaskAPI หลักสำหรับรัน Webhook
│   ├── admin_app.py      # Streamlit UI สำหรับ Admin
│   ├── ai_processor.py   # Logic หลัก: รับ task, เรียก Agent, จัดการ Error/Retry Logic
│   ├── database.py       # จัดการการเชื่อมต่อ SQLite, การดึง Store Info และ Chat History
│   └── agent_setup.py    # จัดการการสร้าง LLM, SQL Toolkit, Memory, และ Agent Executor
├── .env                  # ตัวอย่างไฟล์ตั้งค่า API Key และ DB URI
├── requirements.txt      # รายการไลบรารีที่จำเป็น
└── README.md             # ไฟล์คู่มือนี้
```

# 2. การติดตั้งและการตั้งค่า

## 2.1. สิ่งที่ต้องมีก่อนเริ่ม
* Python 3.7 หรือใหม่กว่า
* pip (ตัวจัดการแพ็กเกจของ Python)
* ngrok (สำหรับเปิด Local Server ให้เข้าถึงได้จากภายนอก)

## 2.2. สร้าง Environment และติดตั้ง Dependencies:
```
python -m venv venv
source venv/bin/activate  # บน Windows ใช้ `venv\Scripts\activate`
```
ไฟล์ requirements.txt
ติดตั้งไลบรารีที่จำเป็นทั้งหมดด้วยคำสั่ง:
```
pip install -r requirements.txt
```

## 2.3 สร้างฐานข้อมูลเริ่มต้น:
รันฟังก์ชัน initialize_db() ใน database.py หรือใช้เครื่องมือที่คุณถนัด เพื่อสร้างไฟล์ agent_db.sqlite พร้อมตารางที่จำเป็น (stores, menu, promotions, tasks, ingredients)

## 2.4 การตั้งค่า API Key
### สร้างไฟล์ชื่อ .env ในโฟลเดอร์เดียวกับไฟล์ api_app.py และเพิ่มค่าที่จำเป็นลงไปดังนี้:
```
GOOGLE_API_KEY="YOUR_GEMINI_API_KEY"
# สำหรับการตอบกลับด้วย LINE API
LINE_CHANNEL_ACCESS_TOKEN="YOUR_LINE_ACCESS_TOKEN"
LINE_CHANNEL_SECRET="YOUR_LINE_CHANNEL_SECRET"
#ngrok url
BASE_URL="NGROK_URL"
```

# 3. รันโปรเจกต์และตั้งค่า ngrok
##### 3.1 เปิด Terminal1 รันคำสั่ง ngrok เพื่อเปิด Public URL:
```
ngrok http 9000
```
คุณจะได้รับ Public URL ที่ขึ้นต้นด้วย https:// (เช่น https://example.ngrok-free.app) โปรด คัดลอก URL นี้ไว้
##### 3.2 ขั้นตอนสำคัญ: เปิดไฟล์ api_app.py แล้วนำ URL ที่คัดลอกมาไปวางแทนที่ค่าของตัวแปร base_url ตามโค้ดตัวอย่างด้านล่าง:
```
# V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V
#
# >>> ขั้นตอนที่สำคัญมาก: โปรดนำ Public URL จาก ngrok มาวางที่นี่
#
# ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^
#
BASE_URL = "[https://example.ngrok-free.app](https://example.ngrok-free.app)" # วาง URL ngrok ของคุณที่นี่

```
## 3.3 Terminal 2 (สำหรับ Flask API):
เปิด Terminal หน้าที่สองและรันคำสั่ง:
```
source venv/bin/activate 
cd my_app
python api_app.py
```

# 4. ตั้งค่าบนหน้าเว็บ
##### 1. เปิดเว็บเบราว์เซอร์แล้วไปที่ http://localhost:9000
##### 2. กรอก Channel Secret และ Channel Access Token ของคุณ
##### 3. กดปุ่ม "บันทึกและสร้าง Webhook"
##### หากทุกอย่างถูกต้อง หน้าเว็บจะแสดงข้อความว่า "Webhook URL updated successfully." พร้อมกับ Webhook URL ที่สมบูรณ์


# 5. Flow การทำงานของระบบ (System Data Flow)
## 5.1. ภาพรวม Flow การทำงาน
##### 1. Incoming Request (LINE): ลูกค้าส่งข้อความผ่าน LINE
##### 2. API Gateway (Flask/Gunicorn): LINE Webhook ส่ง Payload มายัง api_app.py
##### 3. Core Logic (ai_processor.py): เริ่มต้นการประมวลผล Task
##### 4. Context Loading (database.py): ดึง Store ID, Store Name, และ Chat History จาก SQLite โดยตรง
##### 5. Agent Initialization (agent_setup.py): สร้าง Agent โดยใช้ Prompt ที่มีบริบท (Store ID) และ Memory (Chat History) ที่โหลดมา
##### 6. Agent Invocation: Agent ประมวลผลข้อความ
##### 7. Response Generation: Agent แปลงผลลัพธ์ SQL เป็นคำตอบภาษาไทยที่เป็นมิตร
##### 8. Output Response (LINE): ส่งข้อความตอบกลับไปยังลูกค้าผ่าน LINE

## 5.2. ลำดับการประมวลผล (Sequential Steps)
Step | ไฟล์ที่ทำงาน | รายละเอียดการทำงานและ Context
----- | ----- | -----
1.Receive Task | line_handler.py -> ai_processor.py | รับ user_id, line_id, และ user_message
2.Load Context | database.py | 🟢 ดึง Context ก่อนสร้าง Agent: เรียก get_store_info_direct(user_id) เพื่อหา store_id และ store_name
3.Build Prompt | agent_setup.py | ใช้ store_id และ store_name ที่ได้มาสร้าง AGENT_PREFIX แบบ Dynamic เพื่อบังคับการกรองข้อมูล
4.Initialize Agent | agent_setup.py | สร้าง SQLDatabaseToolkit และ AgentExecutor โดยใช้ Prompt ที่มี Context และ Memory ที่มี Chat History
5.Invoke Agent | ai_processor.py | เรียก agent_executor.invoke({"input": user_message})
6.SQL Execution | Agent Tools -> SQLite | Agent สร้าง SQL ที่มี WHERE store_id = [ID] และรันกับฐานข้อมูล
7.Respond | ai_processor.py -> line_handler.py | ส่งคำตอบสุดท้ายกลับไปให้ LINE

# 6. การเพิ่ม Memory และการใช้ Chat History ใน Agent
การใช้หน่วยความจำ (Memory) เป็นหัวใจสำคัญที่ทำให้ Chatbot นี้สามารถจดจำการสนทนาที่ผ่านมาและนำข้อมูลนั้นมาประกอบการตัดสินใจและการสร้างคำสั่ง SQL ที่ถูกต้องและซับซ้อนได้
## 6.1. โครงสร้างและการโหลดประวัติการสนทนา
องค์ประกอบ | รายละเอียด | ไฟล์ที่รับผิดชอบ
----- | ----- | -----
Chat History Storage | ประวัติการสนทนา (User Message และ AI Response) จะถูกบันทึกไว้ในตาราง tasks ในฐานข้อมูล SQLite | database.py
Function | ฟังก์ชัน get_chat_history_for_memory() ใน database.py จะดึงข้อความย้อนหลังตาม user_id และ line_id ในรูปแบบที่ LangChain ต้องการ (มักจะจำกัดที่ 8-10 คู่สนทนาล่าสุด) | database.py
Memory Setup | ใช้ ConversationBufferMemory ของ LangChain เพื่อจัดเก็บประวัติที่โหลดมาจากฐานข้อมูลไว้ในตัว Agent | agent_setup.py
## 6.2. การใช้หน่วยความจำเพื่อสะสมเงื่อนไขกรอง
การใช้ Memory ในโปรเจกต์นี้ไม่ได้มีเพียงแค่การจดจำเท่านั้น แต่เป็นการ บังคับ Agent ให้รวมข้อจำกัดหลายชั้น เข้าด้วยกันก่อนจะรัน SQL:
##### 1.การอ่าน History: ในไฟล์ agent_setup.py ส่วน initialize_sql_agent จะมีการโหลด chat_history และส่งเข้าใน memory
##### 2.การนำไปใช้ใน Prompt: AGENT_PREFIX ถูกเขียนขึ้นเพื่อสั่งให้ Agent ต้องอ่าน ข้อความใน chat_history ทุกครั้งที่มีการขอแนะนำเมนู
##### 3.การสะสม Logic: เมื่อลูกค้าตอบว่า "ไม่ทานทะเล" แล้วตามด้วย "ไม่ทานเนื้อ" Agent จะเห็นข้อจำกัดทั้งสองใน Memory และถูกบังคับให้รวมทั้งสองเงื่อนไขเข้าด้วยกันในคำสั่ง SQL เดียว เช่น:
```
... WHERE T1.store_id = {store_id} 
AND T1.menu_id NOT IN (SELECT menu_id FROM ingredients WHERE ingredient_name LIKE '%ทะเล%') 
AND T1.menu_id NOT IN (SELECT menu_id FROM ingredients WHERE ingredient_name LIKE '%เนื้อ%')
```

# 7. แนวทางการพัฒนา Prompt และ Logic
## 7.1. การจัดการบริบทของร้านค้า
##### ไฟล์: agent_setup.py และ database.py
* Dynamic Prompt: ฟังก์ชัน create_agent_prefix() จะสร้าง Prompt ขึ้นมาใหม่ทุกครั้งที่ Agent ถูกเรียก โดยมี store_id และ store_name ที่ดึงจาก database.py (ฟังก์ชัน get_store_info_direct)
* การบังคับกรอง: ในส่วน Core Rules ของ Prompt ถูกกำหนดให้ Agent ต้อง ใช้ {store_id} ในทุกคำสั่ง SELECT ที่เข้าถึงตาราง menu หรือ promotions เพื่อป้องกันการเรียก Subquery ซ้ำ
## 7.2. การสะสมเงื่อนไขการกรองเมนู
##### ไฟล์: agent_setup.py (ใน AGENT_PREFIX ส่วน C. การแนะนำเมนู)
* Agent ถูกสั่งให้ อ่านและรวบรวมข้อจำกัดด้านวัตถุดิบทั้งหมด ที่อยู่ใน chat_history (Memory)
* เมื่อลูกค้าเพิ่มข้อจำกัดใหม่ (เช่น "ไม่ทานเนื้อ" หลัง "ไม่ทานทะเล") Agent จะต้องสร้างคำสั่ง SQL ที่ใช้เงื่อนไข AND T1.menu_id NOT IN (SELECT...) หลายชั้น เพื่อให้แน่ใจว่าผลลัพธ์สุดท้ายจะกรองทุกข้อจำกัดที่สะสมมา

# 8. การจัดการปัญหา Rate Limit และ Quota
##### ระบบนี้มีการจัดการเบื้องต้นสำหรับปัญหาการจำกัดการใช้งานจาก API ดังนี้:
ปัญหา | ไฟล์ที่จัดการ | กลยุทธ์ที่ใช้
----- | ----- | -----
Gemini Rate Limit (429/503) | ai_processor.py | Exponential Backoff: มี Logic ในการหน่วงเวลาและ Retry คำขอไปยัง Gemini API อัตโนมัติ (ตั้งค่า MAX_RETRIES และ BASE_WAIT_TIME ในโค้ด)
ประสิทธิภาพ LLM| .env และ agent_setup.py | Model Choice: แนะนำให้ใช้ LLM_MODEL="gemini-2.5-flash" เพื่อความเร็วและประสิทธิภาพของโควตา

# 9. การอัปเดต LINE Webhook อัตโนมัติ
ระบบของเราออกแบบมาเพื่อลดขั้นตอนการตั้งค่า Webhook ใน LINE Developers Console โดยการใช้ฟังก์ชัน update_line_webhook เพื่อเชื่อมต่อ Channel ของร้านค้าเข้ากับระบบหลังบ้าน (Backend) ของเราโดยอัตโนมัติ
##### 1. ฟังก์ชันหลัก: update_line_webhook
รายละเอียด | กลไกการทำงาน 
----- | ----- 
วัตถุประสงค์ | อัปเดตปลายทาง (Endpoint) ที่ LINE จะส่งข้อความจากลูกค้าเข้ามาให้ระบบของเราประมวลผล 
พารามิเตอร์ | รับ access_token (Channel Access Token) และ webhook_url (URL ที่ระบบของเราสร้างขึ้น)
กลไก API | ส่งคำขอแบบ PUT ไปยัง LINE Messaging API Endpoint (https://api.line.me/v2/bot/channel/webhook/endpoint) พร้อมแนบ Access Token ใน Header เพื่อยืนยันสิทธิ์
ผลลัพธ์ | หากสำเร็จ (สถานะ 200 OK) LINE Channel จะเปลี่ยนไปชี้ Webhook URL มาที่เซิร์ฟเวอร์ของเราทันที
##### 2. Flow การทำงาน: ตั้งค่า Webhook อัตโนมัติ
ขั้นตอน | การทำงานและไฟล์ที่เกี่ยวข้อง | ผลลัพธ์ที่ได้
----- | ----- | -----
1.ป้อนข้อมูล | ผู้ใช้กรอก Channel Secret และ Access Token ใน Frontend (หน้าตั้งค่า) และคลิกบันทึก | ส่งข้อมูล Credentials ผ่าน POST Request ไปยัง Backend Endpoint: /save_credentials/[user_id]
2.ประมวลผลและสร้าง URL| ฟังก์ชัน save_credentials ใน Backend (api_app.py) บันทึก Credentials ลงฐานข้อมูล และ สร้าง Webhook URL เฉพาะร้าน (เช่น https://[BASE_URL]/webhook/[user_id]) | Webhook URL ที่ไม่ซ้ำกันสำหรับ Channel นั้นถูกสร้างขึ้น
3.อัปเดต Webhook| Backend เรียกใช้ฟังก์ชัน update_line_webhook ส่ง Access Token และ Webhook URL ที่สร้างขึ้นไป | LINE API อัปเดต Webhook URL ของ Channel นั้นให้ชี้มาที่เซิร์ฟเวอร์ของเรา
4.ยืนยันผล| Backend รับสถานะสำเร็จจาก LINE และส่งข้อความยืนยันพร้อมแสดง Webhook URL ที่อัปเดตแล้วกลับไปที่ Frontend | ระบบพร้อมใช้งานทันทีสำหรับการรับ-ส่งข้อความ

การทำงานแบบอัตโนมัตินี้ทำให้มั่นใจได้ว่าเมื่อผู้ใช้ตั้งค่าข้อมูล API เข้ามา ระบบจะทำการเชื่อมต่อกับ LINE Channel ให้พร้อมใช้งานสำหรับการรับ-ส่งข้อความโดย ไม่ต้องมีการตั้งค่าด้วยตนเอง ใน LINE Developer Console อีกต่อไป