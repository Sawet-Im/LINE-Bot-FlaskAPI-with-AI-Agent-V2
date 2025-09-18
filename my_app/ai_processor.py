# my_app/ai_processor.py

import time
import os
from database import initialize_database, get_tasks_by_status, update_task_status, update_task_response, DB_FILE_NAME
from agent_setup import initialize_sql_agent

# Initialize database and AI Agent
db_uri_to_use = initialize_database()
sql_agent_executor = initialize_sql_agent(db_uri_to_use, "gemini-2.5-flash")

if not sql_agent_executor:
    print("Failed to initialize AI Agent. Exiting...")
    exit()

def process_pending_tasks():
    print("Looking for pending tasks...")
    pending_tasks = get_tasks_by_status("Pending")
    
    if not pending_tasks:
        print("No pending tasks found.")
        return
    
    print(f"Found {len(pending_tasks)} pending tasks. Processing...")
    
    for task in pending_tasks:
        task_id = task['task_id']
        user_message = task['user_message']

        print(f"Processing task_id: {task_id}")
        
        # Change status to Processing to prevent other workers from picking it up
        update_task_status(task_id, "Processing")
        
        try:
            response = sql_agent_executor.invoke({"input": user_message})
            ai_response = response.get("output", "ขออภัยครับ เกิดข้อผิดพลาดในการประมวลผลคำตอบ")
            
            # Update the task with the AI's response and change status
            update_task_response(task_id, ai_response)
            update_task_status(task_id, "Awaiting_Approval")
            print(f"Task {task_id} processed. Status updated to 'Awaiting_Approval'.")
            
        except Exception as e:
            print(f"Error processing task {task_id}: {e}")
            update_task_status(task_id, "Error")

if __name__ == "__main__":
    # This loop simulates a background worker
    while True:
        process_pending_tasks()
        time.sleep(5) # Wait 5 seconds before checking for new tasks