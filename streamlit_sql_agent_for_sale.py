import streamlit as st
import os
import sqlite3
from datetime import date, datetime
import re
from dotenv import load_dotenv
import csv 

# Load environment variables from .env file
load_dotenv()

# LangChain Imports for SQL Agent
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ollama import ChatOllama
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain_community.agent_toolkits.sql.base import create_sql_agent
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.agents import AgentFinish, AgentAction
from langchain.memory import ConversationBufferMemory

# --- Page Setup ---
st.set_page_config(page_title="AI ผู้ช่วยจัดการฐานข้อมูล", layout="wide")
st.title("🤖 AI ผู้ช่วยจัดการฐานข้อมูล (SQL Agent)")
st.write("สวัสดีครับ! ผมคือ AIผู้ช่วย ที่สามารถ **ค้นหา, เพิ่ม, และแก้ไข** ข้อมูลในฐานข้อมูลของเราได้แล้วนะครับ ถามมาได้เลย!")

# --- 1. Database Setup: Create or connect to the database ---
DB_FILE_NAME = "store_database.db"

@st.cache_resource
def initialize_database(db_file):
    """Initializes SQLite database and populates with sample data if it doesn't exist."""
    if os.path.exists(db_file):
        os.remove(db_file)  # ลบไฟล์เก่าทิ้ง เพื่อให้สร้างตารางใหม่
        
    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE menu (
            menu_id INTEGER PRIMARY KEY,
            menu_name TEXT,
            price REAL,
            category TEXT,
            stock INTEGER,
            store_id INTEGER,
            FOREIGN KEY(store_id) REFERENCES stores(store_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE promotions (
            promo_id INTEGER PRIMARY KEY,
            menu_id INTEGER,
            discount_percentage INTEGER,
            start_date TEXT,
            end_date TEXT,
            FOREIGN KEY(menu_id) REFERENCES menu(menu_id)
        )
    """)
    cursor.execute("""
        CREATE TABLE stores (
            store_id INTEGER PRIMARY KEY,
            store_name TEXT,
            address TEXT,
            opening_hours TEXT
        )
    """)

    # Insert sample data for a food business with store_id
    cursor.execute("INSERT INTO menu VALUES (1, 'ข้าวผัดกะเพราไก่', 50.0, 'จานเดียว', 100, 1)")
    cursor.execute("INSERT INTO menu VALUES (2, 'ผัดซีอิ๊วหมู', 55.0, 'จานเดียว', 80, 1)")
    cursor.execute("INSERT INTO menu VALUES (3, 'ต้มยำกุ้ง', 120.0, 'กับข้าว', 50, 1)")
    cursor.execute("INSERT INTO menu VALUES (4, 'แกงเขียวหวานเนื้อ', 150.0, 'กับข้าว', 40, 2)")
    cursor.execute("INSERT INTO menu VALUES (5, 'ชาเย็น', 35.0, 'เครื่องดื่ม', 150, 2)")

    # Insert promotion data, linked to the new menu
    cursor.execute("INSERT INTO promotions VALUES (1, 1, 10, '2025-09-10', '2025-10-31')") # ข้าวผัดกะเพราไก่ ลด 10%
    cursor.execute("INSERT INTO promotions VALUES (2, 5, 20, '2025-09-15', '2025-09-30')") # ชาเย็น ลด 20%
    
    # Store information remains the same
    cursor.execute("INSERT INTO stores VALUES (1, 'Central Plaza Branch', 'Bangkok', '10:00 - 21:00')")
    cursor.execute("INSERT INTO stores VALUES (2, 'The Mall Branch', 'Chiang Mai', '10:30 - 20:30')")

    conn.commit()
    conn.close()
    
    return f"sqlite:///{db_file}"

db_uri_to_use = initialize_database(DB_FILE_NAME)

# --- 2. LLM and Agent Creation ---

st.sidebar.header("การตั้งค่า AI Model")
selected_llm_model = st.sidebar.radio(
    "เลือก AI Model ที่ต้องการ:",
    ("gemini-2.5-pro","gemini-2.5-flash", "llama3.2","gpt-oss:20b")
)

@st.cache_resource(hash_funcs={ChatGoogleGenerativeAI: id, ChatOllama: id})
def initialize_sql_agent(db_uri, llm_choice):
    """Initializes and returns the LangChain SQL Agent with data modification capabilities."""
    db_instance = SQLDatabase.from_uri(db_uri)

    llm = None
    try:
        if "gemini" in llm_choice:
            google_api_key = os.getenv("GOOGLE_API_KEY")
            if not google_api_key:
                st.error(f"ไม่พบ GOOGLE_API_KEY สำหรับ {llm_choice}. โปรดตั้งค่าในไฟล์ .env.")
                return None
            llm = ChatGoogleGenerativeAI(model=llm_choice, temperature=0, google_api_key=google_api_key)
        elif llm_choice == "llama3.2":
            ollama_host = os.getenv("OLLAMA_HOST")
            if not ollama_host:
                st.warning("ไม่พบ OLLAMA_HOST. ตรวจสอบให้แน่ใจว่า Ollama server กำลังทำงานและถูกตั้งค่าอย่างถูกต้อง.")
                return None
            llm = ChatOllama(model="llama3.2", temperature=0, base_url=ollama_host)
        elif llm_choice == "gpt-oss:20b":
            ollama_host = os.getenv("OLLAMA_HOST")
            if not ollama_host:
                st.warning("ไม่พบ OLLAMA_HOST. ตรวจสอบให้แน่ใจว่า Ollama server กำลังทำงานและถูกตั้งค่าอย่างถูกต้อง.")
                return None
            llm = ChatOllama(model="gpt-oss:20b", temperature=0, base_url=ollama_host)
        else:
            st.error("Model ที่เลือกไม่ถูกต้อง.")
            return None
    except Exception as e:
        st.error(f"Error initializing LLM ({llm_choice}): {e}")
        return None

    toolkit = SQLDatabaseToolkit(db=db_instance, llm=llm)

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
    ผู้ใช้: "ตอนนี้มีโปรโมชั่นอะไรบ้าง"
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

sql_agent_executor = initialize_sql_agent(db_uri_to_use, selected_llm_model)

# --- NEW FUNCTION: Check which stores are open ---
def get_open_stores():
    """Checks the current time and returns a list of stores that are currently open."""
    conn = sqlite3.connect(DB_FILE_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT store_name, opening_hours FROM stores")
    stores = cursor.fetchall()
    conn.close()

    now = datetime.now().time()
    open_stores = []
    
    for store_name, opening_hours_str in stores:
        try:
            open_time_str, close_time_str = opening_hours_str.split(' - ')
            open_time = datetime.strptime(open_time_str, '%H:%M').time()
            close_time = datetime.strptime(close_time_str, '%H:%M').time()
            
            # Check if current time is within opening hours
            if open_time <= now <= close_time:
                open_stores.append(store_name)
        except ValueError:
            # Handle cases where the opening hours format is incorrect
            continue
            
    return open_stores

# --- 3. Chat Interface ---

if "messages" not in st.session_state:
    st.session_state.messages = [
        AIMessage(content="สวัสดีครับ! ผมคือ AI ผู้ช่วยขายอาหาร มีอะไรให้ช่วยไหมครับ?")
    ]

for message in st.session_state.messages:
    with st.chat_message(message.type):
        st.markdown(message.content)

prompt_input = st.chat_input("พิมพ์คำถามหรือคำสั่งของคุณที่นี่...")

def write_to_csv(query, response, sql_command):
    """
    Writes a summary of the query and response to a CSV file.
    """
    csv_file = 'agent_summary.csv'
    is_new_file = not os.path.exists(csv_file)
    
    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        if is_new_file:
            writer.writerow(["DateTime", "User Query", "Finished Chain", "Final AI Response", "SQL Command"])
        
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([current_datetime, query, "Finished", response, sql_command])

if prompt_input:
    st.session_state.messages.append(HumanMessage(content=prompt_input))
    with st.chat_message("user"):
        st.markdown(prompt_input)

    # NEW: Check for the specific question before invoking the agent
    if "ตอนนี้ร้านไหนเปิดบ้าง" in prompt_input or "ร้านไหนเปิดอยู่" in prompt_input or "ร้านเปิดไหม" in prompt_input:
        open_stores = get_open_stores()
        
        if open_stores:
            response_text = f"ตอนนี้ร้านสาขาที่เปิดอยู่ได้แก่: {', '.join(open_stores)} ครับ"
        else:
            response_text = "ขออภัยครับ ตอนนี้ไม่มีร้านสาขาไหนเปิดให้บริการเลย"
            
        write_to_csv(prompt_input, response_text, "N/A")
        st.session_state.messages.append(AIMessage(content=response_text))
        with st.chat_message("ai"):
            st.markdown(response_text)
    else:
        # ORIGINAL LOGIC: Invoke the SQL agent for other queries
        with st.spinner("AI กำลังคิด..."):
            try:
                response = sql_agent_executor.invoke({"input": prompt_input})
                ai_response = response.get("output", "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำตอบ")
                sql_command = "N/A"
                
                if response.get("intermediate_steps"):
                    for step in response["intermediate_steps"]:
                        action, _ = step
                        if isinstance(action, AgentAction) and action.tool == "sql_db_query":
                            sql_command = action.tool_input
                            break
                
                if sql_command != "N/A":
                    ai_response += f"\n\nคำสั่ง SQL ที่ใช้: `{sql_command}`"

                write_to_csv(prompt_input, ai_response, sql_command)
                
                st.session_state.messages.append(AIMessage(content=ai_response))

                with st.chat_message("ai"):
                    st.markdown(ai_response)

                if response.get("intermediate_steps"):
                    with st.expander("ดูขั้นตอนการทำงานของ AI"):
                        for i, step in enumerate(response["intermediate_steps"]):
                            action, observation = step

                            col1, col2 = st.columns([0.5, 0.5])
                            
                            with col1:
                                st.markdown(f"**ขั้นตอนที่ {i+1}**")
                                if isinstance(action, AgentAction):
                                    thought_match = re.search(r'Thought:\s*(.*?)(?=\nAction:|$)', action.log, re.DOTALL)
                                    thought = thought_match.group(1).strip() if thought_match else "AI กำลังคิด..."

                                    st.markdown(f"**🧠 ความคิดของ AI:** {thought}")
                                    st.markdown(f"**⚙️ การดำเนินการ:** `{action.tool}`")
                                    st.markdown(f"**🔧 ข้อมูลนำเข้า (SQL Query):** ```\n{action.tool_input}\n```")
                                elif isinstance(action, AgentFinish):
                                    st.markdown(f"**🧠 ความคิดของ AI:** AI ได้ข้อมูลครบถ้วนและพร้อมให้คำตอบสุดท้ายแล้วครับ")
                                    st.markdown(f"**⚙️ การดำเนินการ:** `สรุปคำตอบ`")
                                else:
                                    st.markdown(f"**💡 ความคิดของ AI:** ไม่ใช่ AgentAction หรือ AgentFinish ที่รู้จัก")
                                    st.markdown(f"**⚙️ การดำเนินการ:** `{type(action)}`")
                                    st.markdown(f"**🔧 ข้อมูลนำเข้า:** `ไม่มี`")

                            with col2:
                                st.markdown("**📋 ผลลัพธ์**")
                                if isinstance(action, AgentAction):
                                    st.markdown(f"```\n{str(observation)}\n```")
                                elif isinstance(action, AgentFinish):
                                    st.markdown(f"```\n{action.return_values.get('output', 'N/A')}\n```")
                            
                            st.markdown("---")

            except Exception as e:
                st.error("เกิดข้อผิดพลาดในการทำงานของ AI", icon="🚨")
                st.markdown("กรุณาลองใหม่อีกครั้ง หรือพิมพ์คำถามให้ชัดเจนขึ้น")
                st.exception(e)
                st.session_state.messages.append(AIMessage(content="ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่"))
                with st.chat_message("ai"):
                    st.markdown("ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผล กรุณาลองใหม่")