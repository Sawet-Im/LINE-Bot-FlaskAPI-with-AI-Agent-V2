# ai_processor.py
import time
import os
import sqlite3
# นำเข้าทุกฟังก์ชันที่จำเป็น
from database import initialize_database, get_tasks_by_status, update_task_status, update_task_response, get_credentials, get_auto_reply_setting, update_auto_reply_setting
from agent_setup import initialize_sql_agent
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError
# from utils.memory_checker import MemoryCheckerCallback # ต้อง import คลาส
# from google.generativeai.errors import APIError

# ----------------------------------------------------------------------
# ❌ การเปลี่ยนแปลงที่ 1: ลบการสร้าง Agent ใน Global Scope ออก
#    Agent ต้องถูกสร้างในฟังก์ชันที่รู้ user_id และ line_id เท่านั้น
# ----------------------------------------------------------------------
# Initialize database URI (ยังคงต้องทำครั้งเดียว)
db_uri_to_use = initialize_database()
AGENT_MODEL_CHOICE = "gemini-2.5-flash"

# ลบโค้ดนี้ออก:
# sql_agent_executor = initialize_sql_agent(db_uri_to_use, "gemini-2.5-flash")
# if not sql_agent_executor:
#     print("Failed to initialize AI Agent. Exiting...")
#     exit()
# ----------------------------------------------------------------------

def send_message_to_line(line_id, message, channel_access_token):
    """Sends a message to the LINE user via push message."""
    try:
        line_bot_api = LineBotApi(channel_access_token)
        line_bot_api.push_message(
            line_id,
            TextSendMessage(text=message)
        )
        print(f"Successfully sent message to LINE user {line_id}.")
        return True
    except LineBotApiError as e:
        print(f"LINE API Error when sending message to {line_id}: {e}")
        return False
    except Exception as e:
        print(f"General error when sending message to {line_id}: {e}")
        return False

def process_pending_tasks():
    user_id = "d65e044b-1136-4020-9b72-e3b7e5092d30"
    
    print("Looking for pending tasks...")
    pending_tasks = get_tasks_by_status(user_id, "Pending")
    
    if not pending_tasks:
        print("No pending tasks found.")
        return

    print(f"Found {len(pending_tasks)} pending tasks. Processing...")
    
    for task in pending_tasks:
        task_id = task['task_id']
        user_message = task['user_message']
        line_id = task['line_id']
        
        print(f"Processing task_id: {task_id} for user {user_id}.")
        
        try:
            is_auto_reply_enabled = get_auto_reply_setting(user_id)
            
            # ------------------------------------------------------------------
            # 🔄 การเปลี่ยนแปลงที่ 2: สร้าง Agent ภายใน Loop เพื่อโหลด Memory
            # ------------------------------------------------------------------
            sql_agent_executor = initialize_sql_agent(db_uri_to_use, AGENT_MODEL_CHOICE, user_id, line_id)
            if not sql_agent_executor:
                raise Exception("Failed to initialize AI Agent for task.")
            # ------------------------------------------------------------------
            
            response = sql_agent_executor.invoke({"input": user_message})
            
            # ------------------------------------------------------------------
            # 🔄 การเปลี่ยนแปลงที่ 3: แยกคำตอบและคำสั่ง SQL ก่อนอัปเดต DB
            # ------------------------------------------------------------------
            ai_response_raw = response.get("output", "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำตอบ")
            response_message, delimiter, sql_command_raw = ai_response_raw.partition("คำสั่ง SQL ที่ใช้:")
            sql_command = sql_command_raw.strip()
            
            # อัปเดตฐานข้อมูลด้วยคำตอบของ AI และคำสั่ง SQL
            update_task_response(task_id, response_message.strip(), sql_command if sql_command else "None")
            # ------------------------------------------------------------------
            
            if is_auto_reply_enabled:
                print(f"Auto-reply is enabled. Sending message for task {task_id}.")
                credentials_data = get_credentials(user_id)
                if credentials_data:
                    # ใช้ response_message ที่ถูกแยกแล้ว
                    send_message_to_line(line_id, response_message.strip(), credentials_data['channel_access_token'])
                else:
                    print(f"Credentials not found for user {user_id}. Cannot send message.")
                    update_task_status(task_id, "Error")
            else:
                print(f"Auto-reply is disabled. Updating status to Awaiting_Approval for task {task_id}.")
                # เปลี่ยนเป็น Awaiting_Approval หากปิดการตอบอัตโนมัติ
                update_task_status(task_id, "Awaiting_Approval")
            
        except Exception as e:
            print(f"Error processing task {task_id}: {e}")
            update_task_status(task_id, "Error")

# def process_new_tasks(user_id, line_id, user_message, task_id):
#     """Processes a single, newly added task for the AI Agent."""
#     print(f"Processing new task {task_id} for user {user_id} and line_id {line_id}.")
    
#     try:
#         is_auto_reply_enabled = get_auto_reply_setting(user_id)      
        
#         # 1. สร้าง Agent (อาจคืนค่า None)
#         sql_agent_executor = initialize_sql_agent(db_uri_to_use, AGENT_MODEL_CHOICE, user_id, line_id)
        
#         # 2. 🛑 ตรวจสอบความสำเร็จของการสร้าง Agent
#         if not sql_agent_executor:
#             # นี่คือการจัดการเมื่อ Agent สร้างไม่สำเร็จ (เช่น API Key ผิด)
#             print(f"🛑 FATAL ERROR: initialize_sql_agent returned None for task {task_id}. Check API Key/LLM setup.")
#             update_task_status(task_id, "FatalError") 
#             return # ออกจากฟังก์ชันทันที (ป้องกันไม่ให้ไปถึงโค้ด Memory)
        
#         # ----------------------------------------------------
#         # 🛑 โค้ดสำหรับ DEBUG (ถูกเรียกเมื่อ Agent สร้างสำเร็จเท่านั้น) 🛑
#         # ----------------------------------------------------
#         # ⚠️ บรรทัด Debug ถูกย้ายมาอยู่หลังการตรวจสอบ 'if not sql_agent_executor:'
#         print("\n--- DEBUG: AGENT SUCCESSFUL. LOADING HISTORY NOW ---")
        
#         # ⚠️ ตั้งค่าตัวแปรสำหรับเก็บ Memory (เผื่อว่าเข้าถึงไม่ได้)
#         memory_loaded = None 
        
#         try:
#             # ⚠️ การเข้าถึง Memory ที่ถูกต้อง
#             memory_loaded = sql_agent_executor.memory 
#         except AttributeError:
#             # ถ้าเข้าถึง .memory ไม่ได้
#             print("WARNING: Could not access .memory attribute on AgentExecutor. Skipping history display.")
#             # 🛑 ลบ 'return' ออก! 🛑
#             pass 
        
#         if memory_loaded:
#             # ดึงค่า history เป็น list ของ Messages
#             current_history = memory_loaded.load_memory_variables({})['chat_history'] 
#             print("*********")
#             for message in current_history:
#                 # พิมพ์แต่ละข้อความในรูปแบบที่ชัดเจน
#                 print(f"[{message.type.upper()}]: {message.content}") 
            
#             print("-------------------------------------------\n")
        
#         # ----------------------------------------------------
        
#         # 3. Invoke the AI Agent with the user's message
#         # response = sql_agent_executor.invoke({"input": user_message})

#         response = sql_agent_executor.invoke(
#             {"input": user_message},
#             config={"callbacks": [MemoryCheckerCallback()]} # ⬅️ ใส่ Callback เข้าไป
#         )

        
#         ai_response_raw = response.get("output", "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำตอบ")     
        
#         # 4. แยกคำตอบและ SQL เพียงครั้งเดียว (ถูกต้อง)
#         response_message, delimiter, sql_command_raw = ai_response_raw.partition("คำสั่ง SQL ที่ใช้:")
#         sql_command = sql_command_raw.strip()
#         final_response_message = response_message.strip() # ข้อความตอบลูกค้า
        
#         if is_auto_reply_enabled:
#             print(f"Auto-reply is enabled. Sending message for task {task_id}.")
#             credentials_data = get_credentials(user_id)
#             if credentials_data:
                
#                 # ❌ ลบโค้ดซ้ำซ้อนใน if block ออกทั้งหมด
                
#                 # 5. อัปเดต DB และส่ง LINE ด้วยค่าที่แยกไว้แล้ว
#                 if sql_command:
#                     update_task_response(task_id, final_response_message, sql_command) 
#                 else:
#                     update_task_response(task_id, final_response_message, "None")
                
#                 # ส่งข้อความ Line (ใช้ final_response_message)
#                 send_message_to_line(line_id, final_response_message, credentials_data['channel_access_token'])
#             else:
#                 print(f"Credentials not found for user {user_id}. Cannot send message.")
#                 update_task_status(task_id, "Error")
#         else:
#             print(f"Auto-reply is disabled. Updating status to Awaiting_Approval for task {task_id}.")
#             update_task_status(task_id, "Awaiting_Approval")
            
#     except Exception as e:
#         # หากเกิด Exception อื่น ๆ (เช่น การเรียก DB, การรัน invoke)
#         print(f"Error processing task {task_id}: {e}")
#         update_task_status(task_id, "Error")


def process_new_tasks(user_id, line_id, user_message, task_id):
    """Processes a single, newly added task for the AI Agent with Retry Logic."""
    print(f"Processing new task {task_id} for user {user_id} and line_id {line_id}.")
    
    # 🟢 กำหนดค่า Retry
    MAX_RETRIES = 5 
    BASE_WAIT_TIME = 5 # วินาที เริ่มต้นรอ 5, 10, 20, ...

    for attempt in range(MAX_RETRIES):
        try:
            is_auto_reply_enabled = get_auto_reply_setting(user_id)      
            
            # 1. สร้าง Agent (อาจคืนค่า None)
            sql_agent_executor = initialize_sql_agent(db_uri_to_use, AGENT_MODEL_CHOICE, user_id, line_id)
            
            # 2. 🛑 ตรวจสอบความสำเร็จของการสร้าง Agent
            if not sql_agent_executor:
                # Fatal Error ที่ไม่เกี่ยวกับ 503 (เช่น API Key ผิด)
                print(f"🛑 FATAL ERROR: initialize_sql_agent returned None for task {task_id}. Check API Key/LLM setup.")
                update_task_status(task_id, "FatalError") 
                return 
            
            # ----------------------------------------------------
            # 🛑 โค้ดสำหรับ DEBUG (ถูกเรียกเมื่อ Agent สร้างสำเร็จเท่านั้น) 🛑
            # ----------------------------------------------------
            print("\n--- DEBUG: AGENT SUCCESSFUL. LOADING HISTORY NOW ---")
            
            memory_loaded = None 
            
            try:
                memory_loaded = sql_agent_executor.memory 
            except AttributeError:
                print("WARNING: Could not access .memory attribute on AgentExecutor. Skipping history display.")
                pass 
            
            if memory_loaded:
                current_history = memory_loaded.load_memory_variables({})['chat_history'] 
                print("*********")
                for message in current_history:
                    print(f"[{message.type.upper()}]: {message.content}") 
                
                print("-------------------------------------------\n")
            
            # ----------------------------------------------------
            
            # 3. Invoke the AI Agent with the user's message
            # ลบคืนค่า Callback ที่ไม่ได้ประกาศออกไป
            response = sql_agent_executor.invoke({"input": user_message})

            
            ai_response_raw = response.get("output", "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำตอบ")     
            
            # 4. แยกคำตอบและ SQL เพียงครั้งเดียว (ถูกต้อง)
            response_message, delimiter, sql_command_raw = ai_response_raw.partition("คำสั่ง SQL ที่ใช้:")
            sql_command = sql_command_raw.strip()
            final_response_message = response_message.strip() # ข้อความตอบลูกค้า
            
            # 5. อัปเดต DB และส่ง LINE
            if sql_agent_executor:
                print(f"Auto-reply is enabled. Sending message for task {task_id}.")
                credentials_data = get_credentials(user_id)
                if credentials_data:
                    
                    if sql_command:
                        update_task_response(task_id, final_response_message, sql_command) 
                    else:
                        update_task_response(task_id, final_response_message, "None")
                    
                    # ส่งข้อความ Line (ใช้ final_response_message)
                    send_message_to_line(line_id, final_response_message, credentials_data['channel_access_token'])
                    update_task_status(task_id, "Responded") # 🟢 เพิ่มการอัปเดตสถานะสำเร็จ
                else:
                    print(f"Credentials not found for user {user_id}. Cannot send message.")
                    update_task_status(task_id, "Error")
            else:
                print(f"Auto-reply is disabled. Updating status to Awaiting_Approval for task {task_id}.")
                update_task_status(task_id, "Awaiting_Approval")
            
            # 🟢 สำเร็จแล้ว: ออกจาก Loop และฟังก์ชัน
            return 
        
        # 🟢 ดักจับ Error ที่เป็น Rate Limit หรือ Server Overload
        except Exception as e:
            error_message = str(e).lower()
            
            # ตรวจสอบ Error 429 (Rate Limit) หรือ 503 (Overloaded) หรือ 500
            is_retryable = ("429" in error_message or 
                            "503" in error_message or 
                            "500" in error_message)

            if is_retryable and attempt < MAX_RETRIES - 1:
                # 🟢 คำนวณเวลาหน่วงแบบทวีคูณ (Exponential Backoff)
                wait_time = BASE_WAIT_TIME * (2 ** attempt) + (attempt * 2)
                
                print(f"Attempt {attempt + 1} failed (Error: {e}). Retrying in {wait_time} seconds...")
                time.sleep(wait_time) 
            else:
                # 🟢 ถ้าลองครบ 5 ครั้ง หรือเป็น Error อื่นที่แก้ไม่ได้
                print(f"Max retries reached or unrecoverable error for Task {task_id}: {e}")
                
                # 1. อัปเดตสถานะเป็น Error
                update_task_status(task_id, "Error")
                
                # 2. ตอบกลับลูกค้าว่าระบบไม่ว่าง
                credentials_data = get_credentials(user_id)
                if credentials_data:
                    line_bot_api_dynamic = LineBotApi(credentials_data['channel_access_token'])
                    # ใช้ push_message เพื่อให้ตอบกลับได้แม้ว่า reply_token จะหมดอายุไปแล้ว
                    line_bot_api_dynamic.push_message(
                        line_id,
                        TextSendMessage(text="ขออภัยค่ะ ระบบกำลังประมวลผลเยอะ รบกวนลองใหม่อีกครั้งค่ะ")
                    )
                # 3. จบการทำงาน (ไม่ raise e เพื่อไม่ให้ Webhook พัง)
                return 