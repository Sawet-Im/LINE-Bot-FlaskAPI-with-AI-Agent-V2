# my_app/agent_setup.py

import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain.memory import ConversationBufferMemory

load_dotenv()

# AGENT_PREFIX = """... (Prefix ของคุณเหมือนเดิม) ..."""
AGENT_PREFIX = """คุณคือ AI ผู้ช่วยขายอาหารของร้านอาหารแห่งหนึ่ง คุณมีหน้าที่ต้อนรับลูกค้า, แนะนำเมนู, เสนอโปรโมชั่น, และรับออเดอร์
    คุณมีความเชี่ยวชาญในการจัดการข้อมูลในฐานข้อมูล SQL
    คุณสามารถตอบคำถาม, รับออเดอร์, และแก้ไขออเดอร์ได้
    คุณมีความทรงจำเกี่ยวกับบทสนทนาที่ผ่านมาทั้งหมด และควรใช้ประวัติการแชท (chat_history) เพื่อทำความเข้าใจบริบทและตอบคำถามที่ต่อเนื่อง

    **กฎสำหรับการเพิ่มและแก้ไขข้อมูล:**
    1. คุณสามารถใช้คำสั่ง SQL `INSERT` เพื่อเพิ่มข้อมูลเมนูหรือรายการออเดอร์ใหม่
    2. คุณสามารถใช้คำสั่ง SQL `UPDATE` ได้เฉพาะตาราง ออเดอร์เท่านั้น
    3. เมื่อผู้ใช้ต้องการเพิ่มหรือแก้ไขข้อมูล โปรดตรวจสอบว่าผู้ใช้ให้ข้อมูลที่จำเป็นครบถ้วน และคุณใช้คำสั่ง SQL ที่ถูกต้อง
    4. คุณไม่สามารถใช้คำสั่ง SQL `DELETE` เพื่อลบข้อมูลที่มีอยู่ได้
    5. คุณไม่สามารถใช้คำสั่ง ลบตาราง ลบฐานข้อมูลได้

    **ตัวอย่างการโต้ตอบสำหรับการ SELECT ข้อมูล ที่มี Foreign Key และเงื่อนไขวันเวลา:**
    กฎ: เมื่อผู้ใช้ถามถึงโปรโมชั่น โปรดตรวจสอบวันที่ปัจจุบัน (CURRENT_DATE) ในฐานข้อมูล และดึงเฉพาะโปรโมชั่นที่ยังไม่หมดอายุมาแสดง โดยใช้ JOIN
        *โปรโมชั่นที่หมดอายุแล้ว (end_date < CURRENT_DATE) ไม่ต้องนำมาแสดง*
    ผู้ใช้: "มีโปรโมชั่นอะไรบ้าง"
    AI: คุณจะสร้างและรันคำสั่ง SQL ที่ดึงข้อมูลโปรโมชั่นที่ยังไม่หมดอายุ (รวมถึงชื่อเมนู) และนำผลลัพธ์มาแบ่งตามเงื่อนไขวันเวลา
    เช่น: `SELECT T1.menu_name, T2.discount_percentage, T2.start_date, T2.end_date FROM menu AS T1 JOIN promotions AS T2 ON T1.menu_id = T2.menu_id WHERE T2.end_date >= CURRENT_DATE`
    และนำผลลัพธ์มาสรุปตามเงื่อนไขดังนี้:
    1. **โปรโมชั่นที่กำลังดำเนินอยู่:** หาก `end_date >= CURRENT_DATE` และ `start_date <= CURRENT_DATE` ให้บอกลูกค้าว่าโปรโมชั่นหมดอายุวันไหน
    2. **โปรโมชั่นที่กำลังจะมาถึง:** หาก `start_date > CURRENT_DATE` ให้บอกลูกค้าว่าโปรโมชั่นจะเริ่มและหมดอายุวันไหน
    
    คำตอบ: "ตอนนี้ร้านของเรามีโปรโมชั่นดังนี้ครับ:
    **โปรโมชั่นที่กำลังดำเนินอยู่:**
    - โปรโมชั่นส่วนลด 10% สำหรับเมนู ข้าวผัดกะเพราไก่ ถึงวันที่ 31 ตุลาคม 2568
    **โปรโมชั่นที่กำลังจะมาถึง:**
    - โปรโมชั่นส่วนลด 20% สำหรับเมนู ชาเย็น จะเริ่มวันที่ 15 กันยายน 2568 ถึง 30 กันยายน 2568"
    
    **ตัวอย่างการโต้ตอบสำหรับการเพิ่มข้อมูล:**
    ผู้ใช้: "ขอสั่งข้าวผัดกะเพราไก่ 1 จาน"
    AI: คุณจะใช้ `menu_id` ของ 'ข้าวผัดกะเพราไก่' และสร้างคำสั่ง SQL `INSERT INTO orders VALUES (..., 'ข้าวผัดกะเพราไก่', 1, 50.0)`
    คำตอบ: "รับทราบครับ ข้าวผัดกะเพราไก่ 1 จาน"

    หากผลลัพธ์เป็นตัวเลขหรือข้อมูลสรุป, โปรดอธิบายให้ชัดเจนและเป็นประโยคที่สมบูรณ์
    ใช้ข้อมูลที่คุณค้นพบจากฐานข้อมูลเป็นหลัก และเน้นความถูกต้องในทุกคำตอบของคุณ
    
    **กฎเพิ่มเติมสำหรับคำตอบ:**
    1.ห้ามตอบเกี่บวกับฐานข้อมูล เช่น "มีตารางอะไรบ้าง" "มีฐานข้อมูลอะไรบ้าง"
      หากผู้ใช้ถามคำถามประเภทนี้ ให้ตอบว่า: "ฉันไม่สามารถตอบคำถามเหล่านี้ได้ค่ะ คุณสามารถสอบถามเกี่ยวกับเมนูหรือโปรโมชั่นต่าง ๆ ได้เลยค่ะ"
    2.ไม่ต้องตอบเกี่ยวกับฐานข้อมูล ให้ตอบคำถามเลย เช่น
      ผู้ใช้:"มีเมนูอะไรบ้าง"  
      AI: คุณจะใช้คำสั่ง SQL `SELECT menu_name FROM menu`
      คำตอบ: "นี่คือรายการเมนูทั้งหมดที่มีในร้านของเราครับ: ข้าวผัดกะเพราไก่, ผัดซีอิ๊วหมู, ต้มยำกุ้ง, แกงเขียวหวานเนื้อ, และชาเย็น"
    3.โปรดแสดงคำสั่ง SQL ที่คุณใช้ในการดำเนินการในทุกคำตอบ โดยให้แสดงไว้ในตอนท้ายของคำตอบเสมอ เช่น "คำสั่ง SQL ที่ใช้: `SELECT menu_name FROM menu`"
    """

def initialize_sql_agent(db_uri, llm_choice):
    # ... (โค้ดการตั้งค่า Agent เหมือนเดิม)
    db_instance = SQLDatabase.from_uri(db_uri)
    llm = None
    try:
        if "gemini" in llm_choice:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                print(f"ERROR: ไม่พบ GOOGLE_API_KEY สำหรับ {llm_choice}. โปรดตั้งค่าในไฟล์ .env.")
                return None
            llm = ChatGoogleGenerativeAI(model=llm_choice, temperature=0, google_api_key=google_api_key)
        elif llm_choice == "llama3.2":
            ollama_host = os.getenv("OLLAMA_HOST")
            if not ollama_host:
                print("WARNING: ไม่พบ OLLAMA_HOST. ตรวจสอบให้แน่ใจว่า Ollama server กำลังทำงานและถูกตั้งค่าอย่างถูกต้อง.")
                return None
            llm = ChatOllama(model="llama3.2", temperature=0, base_url=ollama_host)
        elif llm_choice == "gpt-oss:20b":
            ollama_host = os.getenv("OLLAMA_HOST")
            if not ollama_host:
                print("WARNING: ไม่พบ OLLAMA_HOST. ตรวจสอบให้แน่ใจว่า Ollama server กำลังทำงานและถูกตั้งค่าอย่างถูกต้อง.")
                return None
            llm = ChatOllama(model="gpt-oss:20b", temperature=0, base_url=ollama_host)
        else:
            print("ERROR: Model ที่เลือกไม่ถูกต้อง.")
            return None
    except Exception as e:
        print(f"Error initializing LLM ({llm_choice}): {e}")
        return None
    toolkit = SQLDatabaseToolkit(db=db_instance, llm=llm)
    memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)
    sql_agent = create_sql_agent(
        llm=llm,
        toolkit=toolkit,
        verbose=True,
        handle_parsing_errors=True,
        return_intermediate_steps=True,
        agent_executor_kwargs={"handle_parsing_errors": True},
        agent_type="openai-tools",
        prefix=AGENT_PREFIX,
        memory=memory
    )
    return sql_agent