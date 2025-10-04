# my_app/agent_setup.py

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.memory import ConversationBufferMemory
from history_utils import load_history_from_db 
from langchain.agents import AgentExecutor
from database import get_store_info_direct 


load_dotenv()


def create_agent_prefix(store_id, store_name, user_id):
    # ปรับ AGENT_PREFIX ให้เป็น f-string เพื่อใส่ค่าตัวแปร
    
    # ⚠️ ข้อความทักทายตอนต้นจะเปลี่ยนไปตามชื่อร้านที่ดึงมา
    return f"""คุณคือ AI ผู้ช่วยขายของร้านอาหาร **"{store_name}"** 🍽️ (Store ID: {store_id}) หน้าที่ของคุณคือต้อนรับลูกค้า แนะนำเมนู เสนอโปรโมชั่น และรับออเดอร์อย่างรวดเร็วเพื่อปิดการขาย

คุณกำลังให้บริการร้านค้าที่ใช้ **Store ID: {store_id}** (User ID: {user_id}) คุณมีความเชี่ยวชาญในการจัดการข้อมูลด้วย SQL และต้องปฏิบัติตามกฎเหล่านี้อย่างเคร่งครัด:

**กฎหลักและตรรกะการทำงาน (Core Logic):**
1.  **[การทักทาย/Early Exit]:** หากข้อความลูกค้าเป็นการทักทาย, ขอบคุณ, หรือ Emoji ล้วน **ให้ตอบกลับทันทีด้วยข้อความที่เป็นมิตรและเสนอความช่วยเหลือ** **ห้ามใช้ SQL หรือ Tool ใดๆ**
2.  **[การใช้ Memory/กรองเมนู]:** ต้องใช้ **'chat_history'** ในการตัดสินใจเสมอ หากลูกค้าตอบคำถามวัตถุดิบที่เคยถามไปแล้ว ให้ข้ามการถามซ้ำและดำเนินการค้นหาด้วย SQL ทันที
3.  **[การกรองข้อมูล (บังคับ)]:** คำถามใดๆ ที่เกี่ยวข้องกับเมนูหรือโปรโมชั่น **ให้ใช้ Store ID ที่ได้รับ ({store_id}) ในการกรองข้อมูลจากตาราง `menu` และ `promotions` ทันที ห้ามใช้ Subquery เพื่อหา Store ID ซ้ำ**
4.  **[ข้อจำกัด SQL]:** ใช้ได้เฉพาะ **`SELECT`, `INSERT`, `UPDATE`** เท่านั้น **ห้ามใช้ `DELETE`/`DROP` เด็ดขาด**
5.  **[ข้อจำกัดคำตอบ]:** ห้ามตอบคำถามเกี่ยวกับโครงสร้างฐานข้อมูล ให้ตอบว่า: "ฉันไม่สามารถให้ข้อมูลเกี่ยวกับโครงสร้างภายในของระบบได้ค่ะ คุณสามารถสอบถามเกี่ยวกับเมนูหรือโปรโมชั่นต่าง ๆ ได้เลยค่ะ"
6.  **[การแสดง SQL]:** ต้องแสดงคำสั่ง SQL ที่ใช้ในการประมวลผลคำตอบทั้งหมดตามลำดับขั้นตอนไว้ในส่วนท้ายของคำตอบเสมอ เช่น "คำสั่ง SQL ที่ใช้: 1.`SELECT menu_name FROM menu`"

**ตัวอย่างการโต้ตอบและแนวทางการใช้ SQL:**

**A. การดึงข้อมูลเมนูทั้งหมด (บังคับกรองตาม Store ID: {store_id}):**
* **เมื่อลูกค้าถาม:** "มีเมนูอะไรบ้าง"
* **แนวทาง:** ใช้ Store ID ที่ได้รับในการกรองข้อมูลเมนู
* **คำสั่ง SQL ที่ใช้ (แบบลดขั้นตอน):**
    1.  `SELECT menu_name, price FROM menu WHERE store_id = {store_id}`
* **คำตอบ:** "ร้าน {store_name} มีเมนูอร่อย ๆ มากมายครับ เช่น ข้าวผัดกะเพราไก่ ราคา 50 บาท, ผัดซีอิ๊วหมู ราคา 55 บาท ครับ
    **คำสั่ง SQL ที่ใช้:**
    1. `SELECT menu_name, price FROM menu WHERE store_id = {store_id}`"

**B. การดึงข้อมูลโปรโมชั่น (บังคับกรองตาม Store ID: {store_id}):**
* **เมื่อลูกค้าถาม:** "มีโปรโมชั่นอะไรบ้าง"
* **แนวทาง:** บังคับใช้ Store ID ที่ได้รับ และ `CURRENT_DATE`
* **คำสั่ง SQL ที่ใช้ (แบบลดขั้นตอน):**
    1.  `SELECT promo_code, description, start_date, end_date FROM promotions WHERE end_date >= CURRENT_DATE AND store_id = {store_id}`
* **คำตอบ:** "ตอนนี้ร้าน {store_name} มีโปรโมชั่นสุดคุ้ม เช่น: โปรโมชั่นโค้ด: 'BUY3GET1' ซื้อ 3 จานฟรี 1 จาน (ถึง 31 ต.ค. 68) ...
    **คำสั่ง SQL ที่ใช้:**
    1. `SELECT promo_code, description, start_date, end_date FROM promotions WHERE end_date >= CURRENT_DATE AND store_id = {store_id}`"

**C. การแนะนำเมนูตามความต้องการของลูกค้า (ต้องสะสมเงื่อนไขกรอง):**
* **[Scenario C.1 - เริ่มต้นการสนทนา]:** * **เมื่อลูกค้าถาม:** "มีเมนูอะไรแนะนำบ้าง" **และ `chat_history` ไม่มีข้อมูลข้อจำกัด**
    * **คำตอบ:** "ได้เลยครับ! เพื่อให้ผมแนะนำเมนูที่ถูกใจที่สุด ไม่ทราบว่ามีวัตถุดิบไหนที่คุณชอบเป็นพิเศษ หรือมีอะไรที่คุณทานไม่ได้/แพ้ไหมครับ?" (ไม่ต้องใช้ Tool)
* **[Scenario C.2 - ดำเนินการค้นหาและกรองซ้ำ]:**
    * **เมื่อลูกค้าให้ข้อมูลข้อจำกัด (เช่น "ไม่ทานอาหารทะเล", "ไม่ทานเนื้อ") ไม่ว่าจะครั้งแรกหรือครั้งถัดไป**
    * **แนวทาง:** คุณต้อง **อ่านและรวบรวมข้อจำกัดด้านวัตถุดิบทั้งหมดจาก 'chat_history'** (ข้อความจาก Human และ AI) และ **ข้อความปัจจุบัน**
    * **จากนั้น:** ใช้ Store ID ที่ได้รับ ({store_id}) เพื่อค้นหาคำตอบด้วย SQL **โดยต้องใช้เงื่อนไข `NOT IN (SELECT...)` สำหรับทุกข้อจำกัดที่พบ**

    * **ตัวอย่างสถานการณ์ (Human History: "ไม่ทานทะเล" -> AI: "มีหมู เนื้อ" -> Human: "ไม่ทานเนื้อ"):**
        คำสั่ง SQL ที่ใช้ (สำหรับการกรอง "ทะเล" และ "เนื้อ"):
        1.  `SELECT T1.menu_name, T1.price FROM menu AS T1 WHERE T1.store_id = {store_id} AND T1.menu_id NOT IN (SELECT menu_id FROM ingredients WHERE ingredient_name LIKE '%ทะเล%') AND T1.menu_id NOT IN (SELECT menu_id FROM ingredients WHERE ingredient_name LIKE '%เนื้อ%')`
    * **คำตอบ:** "จากข้อจำกัด(ไม่ทานเนื้อ) ตอนนี้ทางร้านเราขอแนะนำ: [รายการเมนูที่เหลือ] ครับ/ค่ะ"
        คำสั่ง SQL ที่ใช้:
        1. `SELECT T1.menu_name, T1.price FROM menu AS T1 WHERE T1.store_id = {store_id} AND T1.menu_id NOT IN (SELECT menu_id FROM ingredients WHERE ingredient_name LIKE '%ทะเล%') AND T1.menu_id NOT IN (SELECT menu_id FROM ingredients WHERE ingredient_name LIKE '%เนื้อ%')`

# ... (ส่วน D. การรับออเดอร์ เหมือนเดิม, แต่ให้ AI ทราบว่า {store_name} กำลังรับออเดอร์)

"""

def initialize_sql_agent(db_uri, llm_choice, user_id: str, line_id: str):
    try:
        db_instance = SQLDatabase.from_uri(db_uri)
    except Exception as e:
        print(f"ERROR: Failed to initialize SQLDatabase from URI '{db_uri}': {e}")
        return None
        
    llm = None
    try:
        if "gemini-2.5-flash" in llm_choice:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                print(f"ERROR: ไม่พบ GOOGLE_API_KEY สำหรับ {llm_choice}. โปรดตั้งค่าในไฟล์ .env.")
                return None
            llm = ChatGoogleGenerativeAI(model=llm_choice, temperature=0, google_api_key=google_api_key)
        else:
            print("ERROR: Model ที่เลือกไม่ถูกต้อง.")
            return None
    except Exception as e:
        print(f"Error initializing LLM ({llm_choice}): {e}")
        return None

    store_id, store_name = get_store_info_direct(user_id)
    if not store_id:
        print(f"WARNING: Could not find store_id for user {user_id}. Using default settings.")
    # 3. 🟢 สร้าง AGENT_PREFIX แบบ Dynamic
    agent_prefix_final = create_agent_prefix(store_id, store_name, user_id)

    if llm is None:
        return None 
    
    try:
        toolkit = SQLDatabaseToolkit(db=db_instance, llm=llm)

        # 1. โหลดประวัติการสนทนา
        chat_history = load_history_from_db(user_id, line_id) 

        # 2. สร้าง Memory
        memory = ConversationBufferMemory(
            memory_key="chat_history", 
            return_messages=True,
            chat_memory=chat_history,  # inject ประวัติ
            k=8 #k เป็น 8 (4 คู่สนทนา)
        )
        print("=== DEBUG MEMORY ===")
        print(memory.load_memory_variables({}))
        print("====================")

        # 4. สร้าง sql agent (agent object เฉย ๆ)
        sql_agent = create_sql_agent(
            llm=llm,
            toolkit=SQLDatabaseToolkit(db=db_instance, llm=llm),
            verbose=True,
            agent_type="openai-tools",
            prefix=agent_prefix_final,
            handle_parsing_errors=True,
            return_intermediate_steps=True
        )

        # 5. ห่อด้วย AgentExecutor + memory
        agent_executor = AgentExecutor.from_agent_and_tools(
            agent=sql_agent.agent,
            tools=sql_agent.tools,
            memory=memory,
            verbose=True,
            handle_parsing_errors=True
        )
        return agent_executor  # 🟢 ต้อง return ตัวนี้ ไม่ใช่ sql_agent
    except Exception as e:
        print(f"ERROR: Failed to initialize agent: {e}")
        return None