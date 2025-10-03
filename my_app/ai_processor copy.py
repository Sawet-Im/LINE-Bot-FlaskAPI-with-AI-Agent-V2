# ai_processor.py
import time
import os
import sqlite3
from database import initialize_database, get_tasks_by_status, update_task_status, update_task_response, get_credentials, get_auto_reply_setting, update_auto_reply_setting
from agent_setup import initialize_sql_agent
from linebot import LineBotApi
from linebot.models import TextSendMessage
from linebot.exceptions import LineBotApiError

# Initialize database and AI Agent
db_uri_to_use = initialize_database()
sql_agent_executor = initialize_sql_agent(db_uri_to_use, "gemini-2.5-flash")

if not sql_agent_executor:
    print("Failed to initialize AI Agent. Exiting...")
    exit()

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
            
            response = sql_agent_executor.invoke({"input": user_message})
            ai_response = response.get("output", "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำตอบ")
            
            # อัปเดตฐานข้อมูลด้วยคำตอบของ AI, สถานะ, และเวลาในคำสั่งเดียว
            update_task_response(task_id, ai_response)
            
            if is_auto_reply_enabled:
                print(f"Auto-reply is enabled. Sending message for task {task_id}.")
                credentials_data = get_credentials(user_id)
                if credentials_data:
                    send_message_to_line(line_id, ai_response, credentials_data['channel_access_token'])
                    # ลบบรรทัดนี้ออก เพราะ update_task_response ได้เปลี่ยนสถานะให้แล้ว
                    # update_task_status(task_id, "Responded")
                else:
                    print(f"Credentials not found for user {user_id}. Cannot send message.")
                    update_task_status(task_id, "Error")
            else:
                print(f"Auto-reply is disabled. Updating status to Awaiting_Approval for task {task_id}.")
                # การเรียกใช้ update_task_response ได้เปลี่ยนสถานะเป็น Responded ไปแล้ว
                # หากต้องการให้เป็น Awaiting_Approval จริงๆ ต้องแก้ไข update_task_response
                # หรือเพิ่ม update_task_status กลับเข้ามาเฉพาะในส่วนนี้
                # แต่จากตรรกะเดิมของคุณคือต้องการให้เป็น Awaiting_Approval
                update_task_status(task_id, "Awaiting_Approval")
            
        except Exception as e:
            print(f"Error processing task {task_id}: {e}")
            update_task_status(task_id, "Error")

def process_new_tasks(user_id, line_id, user_message, task_id):
    """Processes a single, newly added task for the AI Agent."""
    print(f"Processing new task {task_id} for user {user_id}.")
    
    try:
        is_auto_reply_enabled = get_auto_reply_setting(user_id)      
        # Invoke the AI Agent with the user's message
        response = sql_agent_executor.invoke({"input": user_message})
        ai_response = response.get("output", "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำตอบ")     
        if is_auto_reply_enabled:
            print(f"Auto-reply is enabled. Sending message for task {task_id}.")
            credentials_data = get_credentials(user_id)
            if credentials_data:
                print(ai_response)
                response_message, delimiter, sql_command_raw = ai_response.partition("คำสั่ง SQL ที่ใช้:")
                sql_command = sql_command_raw.strip()
                if sql_command:
                    # กรณีที่ 1: มีคำสั่ง SQL (sql_command เป็น True)
                    # print(task_id, response_message, sql_command, "Responded", len(sql_command))
                    # อัปเดตด้วยคำสั่ง SQL จริง
                    update_task_response(task_id, response_message, sql_command) 
                else:
                    # กรณีที่ 2: ไม่มีคำสั่ง SQL (sql_command เป็น False/ว่างเปล่า)
                    # print(task_id, response_message, "None", "Responded", 0)
                    # อัปเดตด้วยค่า "None"
                    update_task_response(task_id, response_message, "None")
                
                # ส่งข้อความ Line (ส่ง 'response_message' ซึ่งเป็นข้อความตอบกลับของ AI)
                send_message_to_line(line_id, response_message, credentials_data['channel_access_token'])
            else:
                print(f"Credentials not found for user {user_id}. Cannot send message.")
                update_task_status(task_id, "Error")
        else:
            print(f"Auto-reply is disabled. Updating status to Awaiting_Approval for task {task_id}.")
            # ถ้าปิดการตอบอัตโนมัติ ให้เปลี่ยนสถานะเป็น 'Awaiting_Approval'
            update_task_status(task_id, "Awaiting_Approval")
            
    except Exception as e:
        print(f"Error processing task {task_id}: {e}")
        update_task_status(task_id, "Error")