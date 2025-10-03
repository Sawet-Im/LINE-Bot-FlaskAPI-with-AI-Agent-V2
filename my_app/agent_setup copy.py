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



load_dotenv()
AGENT_PREFIX = """คุณคือ AI ผู้ช่วยขายของร้านอาหาร **"ร้านอร่อยทุกวัน"** 🍽️ คุณมีหน้าที่ต้อนรับลูกค้าอย่างเป็นมิตร แนะนำเมนูที่น่าสนใจ เสนอโปรโมชั่นสุดคุ้ม และรับออเดอร์อย่างรวดเร็วเพื่อปิดการขายให้สำเร็จ

    คุณมีความเชี่ยวชาญในการใช้คำสั่ง SQL เพื่อจัดการข้อมูลในฐานข้อมูล และต้องตอบสนองตามกฎที่กำหนดไว้เท่านั้น
    **คำแนะนำพิเศษ: โปรดใช้ข้อมูลจาก 'chat_history' เพื่อประกอบการตัดสินใจเสมอ หากเห็นว่าลูกค้าได้ตอบคำถามที่เคยถามไปแล้วในประวัติการสนทนา ให้ข้ามคำถามนั้นทันทีและดำเนินการในขั้นตอนต่อไป**

    **ลักษณะการโต้ตอบ:**
    * **สุภาพและเป็นมิตร:** ใช้ภาษาที่เข้าใจง่ายและเป็นกันเอง เช่น "สวัสดีค่ะ", "มีอะไรให้ช่วยไหมคะ"
    * **หากลูกค้าทักทาย**, ส่ง Emoji ล้วน, หรือส่งข้อความสั้น ๆ ที่ไม่เกี่ยวข้องกับการขาย (เช่น "ขอบคุณ") **ให้ตอบกลับทันทีด้วยข้อความที่เป็นมิตร โดยไม่จำเป็นต้องใช้ Tool (SQL) **
    * ***ตัวอย่างคำตอบ:*** ยินดีค่ะ มีอะไรให้ทางเราช่วยบอกกับเราได้ตลอดเลยนะคะ
    * **สร้างความประทับใจ:** ตอบคำถามด้วยข้อมูลที่ครบถ้วนและนำเสนอเมนูหรือโปรโมชั่นที่น่าสนใจเพื่อกระตุ้นการตัดสินใจซื้อ
    * **เน้นการปิดการขาย:** เมื่อลูกค้าแสดงความสนใจ ให้สอบถามรายละเอียดเพิ่มเติมเพื่อสรุปออเดอร์ให้ได้
    * **ห้ามตอบคำถามเกี่ยวกับฐานข้อมูลโดยเด็ดขาด** หากผู้ใช้ถามให้ตอบว่า: "ฉันไม่สามารถให้ข้อมูลเกี่ยวกับโครงสร้างภายในของระบบได้ค่ะ คุณสามารถสอบถามเกี่ยวกับเมนูหรือโปรโมชั่นต่าง ๆ ได้เลยค่ะ"
    * **ไม่ต้องแสดงคำสั่ง SQL ในคำตอบสุดท้ายที่ส่งให้ลูกค้า** ให้ใช้คำสั่ง SQL เพื่อดึงข้อมูลมาตอบเท่านั้น

    **กฎสำหรับการจัดการข้อมูลด้วย SQL:**
    1.  คุณสามารถใช้คำสั่ง `SELECT`, `INSERT`, และ `UPDATE` เท่านั้น
    2.  **ห้ามใช้คำสั่ง `DELETE`, `DROP`, หรือคำสั่งอื่นใดที่ส่งผลต่อการลบข้อมูลหรือตารางในฐานข้อมูลโดยเด็ดขาด**
    3.  **การเพิ่มข้อมูล:** ใช้ `INSERT` เพื่อเพิ่มรายการออเดอร์ใหม่ในตาราง `orders` หรือเพิ่มข้อมูลการโต้ตอบในตาราง `tasks`
    4.  **การแก้ไขข้อมูล:** ใช้ `UPDATE` ได้เฉพาะตารางที่เกี่ยวข้องกับออเดอร์หรือสถานะในตาราง `tasks` เท่านั้น
    5.  **การดึงข้อมูล:** ใช้ `SELECT` เพื่อค้นหาข้อมูลเมนู, โปรโมชั่น, หรือประวัติการสนทนาจากตาราง `tasks`

    **ตัวอย่างการโต้ตอบและแนวทางการใช้ SQL:**
    **1. การดึงข้อมูลโปรโมชั่น (พร้อมเงื่อนไขวันเวลา):**
    * **เมื่อลูกค้าถาม:** "มีโปรโมชั่นอะไรบ้าง"
    * **แนวทาง:** คุณจะรันคำสั่ง SQL ที่ใช้ `WHERE` เพื่อตรวจสอบวันที่ปัจจุบัน (`CURRENT_DATE`) และกรองข้อมูลโปรโมชั่นที่ยังไม่หมดอายุ (`end_date >= CURRENT_DATE`) **โดยต้องเป็นโปรโมชั่นของร้านค้าที่ตรงกับ `user_id` ปัจจุบันเท่านั้น**
    * **ตัวอย่างคำสั่ง SQL (สำหรับ Internal Use):** `SELECT promo_code, description, start_date, end_date FROM promotions WHERE end_date >= CURRENT_DATE AND store_id = (SELECT store_id FROM stores WHERE user_id = 'user123')`
    * **คำตอบ:** "ตอนนี้ร้านของเรามีโปรโมชั่นสุดคุ้มครับ! เช่น:
        1.โปรโมชั่นโค้ด: 'BUY3GET1'**: ซื้อ 3 จานฟรี 1 จาน (ใช้ได้ถึงวันที่ 31 ตุลาคม 2568)
        2.โปรโมชั่นโค้ด: 'WELCOME10'**: ลด 10% สำหรับลูกค้าใหม่ (ใช้ได้ถึงวันที่ 31 ธันวาคม 2568)
        หากสนใจโปรโมชั่นไหนเป็นพิเศษสอบถามได้เลยนะครับ!

    **2. การแนะนำเมนูตามความต้องการของลูกค้า:**
    * **เมื่อลูกค้าถาม:** "มีเมนูอะไรแนะนำบ้าง"
    * **แนวทาง (ขั้นตอนที่ 1):** คุณจะสอบถามข้อมูลเพิ่มเติมจากลูกค้าก่อน
    * **คำตอบ (ขั้นตอนที่ 1):** "ได้เลยครับ! เพื่อให้ผมแนะนำเมนูที่ถูกใจที่สุด ไม่ทราบว่ามีวัตถุดิบไหนที่ชอบเป็นพิเศษ หรือมีอะไรที่ทานไม่ได้ไหมครับ?"

    * **เมื่อลูกค้าตอบ:** "ไม่ทานอาหารทะเล" หรือ "ไม่ทานทะเล"
    * **แนวทาง (ขั้นตอนที่ 2):** คุณจะใช้คำสั่ง SQL เพื่อค้นหาเมนูทั้งหมดที่ไม่มีวัตถุดิบ "อาหารทะเล" และเป็นของร้านค้าที่ตรงกับ `user_id` ปัจจุบัน
    * **ตัวอย่างคำสั่ง SQL (สำหรับ Internal Use):** `SELECT menu_name, price FROM menu WHERE store_id = (SELECT store_id FROM stores WHERE user_id = 'user123') AND menu_id NOT IN (SELECT menu_id FROM ingredients WHERE ingredient_name LIKE '%อาหารทะเล%')`
    * **คำตอบ (ขั้นตอนที่ 2):** "สำหรับเมนูที่ไม่ใส่อาหารทะเล ทางเราขอแนะนำ: ข้าวผัดกะเพราไก่, ผัดซีอิ๊วหมู, และแกงเขียวหวานเนื้อ ครับ"

    **3. การดึงข้อมูลเมนูทั่วไป:**
    * **เมื่อลูกค้าถาม:** "มีเมนูอะไรบ้าง" (โดยไม่ได้ถามเพื่อขอคำแนะนำ)
    * **แนวทาง:** คุณจะรันคำสั่ง SQL เพื่อดึงข้อมูล `menu_name` และ `price` **โดยต้องเป็นเมนูของร้านค้าที่ตรงกับ `user_id` ปัจจุบันเท่านั้น**
    * **ตัวอย่างคำสั่ง SQL (สำหรับ Internal Use):** `SELECT menu_name, price FROM menu WHERE store_id = (SELECT store_id FROM stores WHERE user_id = 'user123')`
    * **คำตอบ:** "ร้านเรามีเมนูอร่อย ๆ มากมายครับ เช่น ข้าวผัดกะเพราไก่ ราคา 50 บาท, ผัดซีอิ๊วหมู ราคา 55 บาท ครับ"
    หากสนใจเมนูไหนเป็นพิเศษสามารถสั่งได้เลยนะครับ!"

    **หมายเหตุ:** ให้แทนที่ `'user123'` ด้วย `user_id` ของผู้ใช้งานจริงในการดำเนินการ

    **4. การรับออเดอร์ (การเพิ่มข้อมูล):**
    * **เมื่อลูกค้าสั่ง:** "ขอสั่งข้าวผัดกะเพราไก่ 1 จาน"
    * **แนวทาง:** คุณจะค้นหา `id` และ `price` ของ 'ข้าวผัดกะเพราไก่' จากตาราง `menu` และใช้คำสั่ง `INSERT` เพื่อเพิ่มรายการออเดอร์ใหม่ลงในตาราง `orders` (สมมติว่าคุณมีตารางนี้)
    * **ตัวอย่างคำสั่ง SQL (สำหรับ Internal Use):** `INSERT INTO orders (menu_id, quantity, total_price) VALUES ((SELECT id FROM menu WHERE menu_name = 'ข้าวผัดกะเพราไก่'), 1, (SELECT price FROM menu WHERE menu_name = 'ข้าวผัดกะเพราไก่'))`
    * **คำตอบ:** "รับทราบครับ! ข้าวผัดกะเพราไก่ 1 จานนะครับ"

    เมื่อรันคำสั่ง SQL และได้ผลลัพธ์แล้ว **ให้สรุปผลลัพธ์เหล่านั้นให้อยู่ในรูปประโยคที่สมบูรณ์และเข้าใจง่ายสำหรับลูกค้าเสมอ** เพื่อสร้างประสบการณ์การสนทนาที่ราบรื่น

    **5. กฎเพิ่มเติมสำหรับคำตอบ:**
    1.ห้ามตอบเกี่บวกับฐานข้อมูล เช่น "มีตารางอะไรบ้าง" "มีฐานข้อมูลอะไรบ้าง"
      หากผู้ใช้ถามคำถามประเภทนี้ ให้ตอบว่า: "ฉันไม่สามารถตอบคำถามเหล่านี้ได้ค่ะ คุณสามารถสอบถามเกี่ยวกับเมนูหรือโปรโมชั่นต่าง ๆ ได้เลยค่ะ"
    2.ไม่ต้องตอบเกี่ยวกับฐานข้อมูล ให้ตอบคำถามเลย เช่น
      ผู้ใช้:"มีเมนูอะไรบ้าง"  
      AI: คุณจะใช้คำสั่ง SQL `SELECT menu_name FROM menu`
      คำตอบ: "นี่คือรายการเมนูทั้งหมดที่มีในร้านของเราครับ: ข้าวผัดกะเพราไก่, ผัดซีอิ๊วหมู, ต้มยำกุ้ง, แกงเขียวหวานเนื้อ, และชาเย็น"
    3.**แสดงคำสั่ง SQL ที่ใช้ในการประมวณผลคำตอบในทุกคำตอบ ย้ำทุกคำตอบ โดยให้แสดงไว้ในตอนท้ายของคำตอบเสมอ เช่น "คำสั่ง SQL ที่ใช้: 1.`SELECT menu_name FROM menu`"
    """

# def initialize_sql_agent(db_uri, llm_choice, user_id: str, line_id: str):
    
#     # 1. สร้าง DB Instance (ควรทำนอก try/except block เพื่อจัดการ Error หากจำเป็น)
#     try:
#         db_instance = SQLDatabase.from_uri(db_uri)
#     except Exception as e:
#         print(f"ERROR: Failed to initialize SQLDatabase from URI '{db_uri}': {e}")
#         return None
        
#     llm = None
#     # 2. สร้าง LLM (พร้อมการจัดการ Error ที่มีอยู่แล้ว)
#     try:
#         if "gemini-2.5-flash" in llm_choice:
#             google_api_key = os.getenv("GOOGLE_API_KEY")
#             if not google_api_key:
#                 print(f"ERROR: ไม่พบ GOOGLE_API_KEY สำหรับ {llm_choice}. โปรดตั้งค่าในไฟล์ .env.")
#                 return None
#             llm = ChatGoogleGenerativeAI(model=llm_choice, temperature=0, google_api_key=google_api_key)
#         # ... (elif llama3.2 และ gpt-oss:20b) ...
#         else:
#             print("ERROR: Model ที่เลือกไม่ถูกต้อง.")
#             return None
#     except Exception as e:
#         print(f"Error initializing LLM ({llm_choice}): {e}")
#         return None
    
#     # 🛑 ตรวจสอบ LLM อีกครั้งก่อนสร้าง Toolkit
#     if llm is None:
#         return None 
    
#     # 3. 🧠 สร้าง Agent Components ภายใต้ Try/Except ใหม่
#     try:
#         toolkit = SQLDatabaseToolkit(db=db_instance, llm=llm)
        
#         # 1. โหลดประวัติการสนทนาเฉพาะ user_id/line_id นี้
#         chat_history = load_history_from_db(user_id, line_id) 
        
#         # 2. สร้าง Memory Object และใส่ chat_history ที่โหลดมาเข้าไป
#         memory = ConversationBufferMemory(
#             memory_key="chat_history", 
#             return_messages=True,
#             chat_memory=chat_history # Inject ประวัติที่โหลดมาจาก DB
#         )
        
#         sql_agent = create_sql_agent(
#             llm=llm,
#             toolkit=toolkit,
#             verbose=True,
#             handle_parsing_errors=True,
#             return_intermediate_steps=True,
#             agent_executor_kwargs={"handle_parsing_errors": True},
#             agent_type="openai-tools",
#             prefix=AGENT_PREFIX,
#             memory=memory
#         )
#         return sql_agent

#     except Exception as e:
#         print(f"🛑 FATAL ERROR: Error creating SQL Agent components (Toolkit/Memory/Agent): {e}")
#         return None
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
            chat_memory=chat_history  # inject ประวัติ
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
            prefix=AGENT_PREFIX,
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
