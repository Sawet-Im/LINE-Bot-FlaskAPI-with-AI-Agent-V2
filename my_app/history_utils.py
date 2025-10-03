# history_utils.py

from langchain_core.messages import HumanMessage, AIMessage
# from langchain.memory import ChatMessageHistory
from database import get_chat_history_for_memory
from langchain_community.chat_message_histories import ChatMessageHistory

def load_history_from_db(user_id: str, line_id: str) -> ChatMessageHistory:
    """
    Loads chat history from the database and converts it into a LangChain ChatMessageHistory object.
    
    The history will only contain (HumanMessage, AIMessage) pairs.
    """
    db_history = get_chat_history_for_memory(user_id, line_id, limit=10) # จำกัดแค่ 10 คู่ล่าสุด
    
    history = ChatMessageHistory()
    
    for task in db_history:
        # ข้อความจากลูกค้า (Human)
        user_msg = task.get('user_message')
        # ข้อความตอบกลับจาก AI (AI)
        ai_resp = task.get('ai_response')
        
        # เพิ่มข้อความจากลูกค้าเสมอ
        if user_msg:
            history.add_message(HumanMessage(content=user_msg))
            
        # เพิ่มข้อความจาก AI เฉพาะเมื่อมีการตอบกลับแล้วเท่านั้น
        # (ป้องกันการใส่ข้อความที่ยัง 'Pending' เข้าไปใน history)
        if ai_resp and ai_resp.strip():
            history.add_message(AIMessage(content=ai_resp))
            
    return history