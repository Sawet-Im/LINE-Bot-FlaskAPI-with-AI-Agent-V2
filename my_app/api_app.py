# my_app/api_app.py

import os
from flask import Flask, request, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError # แก้ไขบรรทัดนี้: เพิ่ม InvalidSignatureError
from linebot.models import TextMessage, MessageEvent, TextSendMessage
from dotenv import load_dotenv

load_dotenv()

# Import functions from our modular files
from database import initialize_database, add_new_task, DB_FILE_NAME


# --- 1. Flask App and LINE API Setup ---
app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# ... (โค้ด initialize_database และ import อื่นๆ เหมือนเดิม) ...

@app.route('/webhook', methods=['POST'])
def callback():
    # Get request body and signature
    print("--- LINE Webhook Request ---")
    print(request.get_data(as_text=True))
    print("----------------------------")
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature') # NEW: Get the signature
    
    # Try to handle the webhook event
    try:
        handler.handle(body, signature)
    except InvalidSignatureError: # NEW: Catch the specific error
        print("Invalid signature. Please check your channel secret.")
        return 'Invalid signature', 400
    except Exception as e:
        print(f"Error handling webhook: {e}")
        return 'Internal Server Error', 500
    
    return 'OK', 200

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text
    reply_token = event.reply_token

    # Add the user's message to the tasks queue
    add_new_task(user_id, reply_token, user_message)

    # Immediately send a "received" message back to the user
    line_bot_api.reply_message(
        reply_token,
        TextSendMessage(text="ได้รับข้อความของคุณแล้วค่ะ กรุณารอสักครู่ กำลังดำเนินการค่ะ")
    )

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000)) # พอร์ต 8000 และ ngrok ต้องตรงกัน
    app.run(host='0.0.0.0', port=port)