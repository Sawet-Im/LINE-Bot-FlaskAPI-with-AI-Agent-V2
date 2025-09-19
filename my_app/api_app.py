# my_app/api_app.py
import os
from flask import Flask, request, jsonify, render_template_string
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError, LineBotApiError
from linebot.models import TextMessage, MessageEvent, TextSendMessage
from dotenv import load_dotenv

# For updating webhook URL
import requests

# Import functions from our modular files
from database import initialize_database, add_new_task, get_credentials, add_credentials

# --- 1. Flask App and Database Setup ---
load_dotenv() # โหลดตัวแปรจากไฟล์ .env
app = Flask(__name__)
DB_FILE_NAME = "store_database.db"
initialize_database()

# --- Initialize WebhookHandler globally with a check ---
channel_secret = os.getenv('LINE_CHANNEL_SECRET')
if not channel_secret:
    raise ValueError("LINE_CHANNEL_SECRET environment variable not set.")
handler = WebhookHandler(channel_secret)

# --- 2. LINE Messaging API Webhook Update Function ---
def update_line_webhook(access_token, webhook_url):
    """
    Updates the webhook URL for a given LINE channel.
    """
    try:
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        # Corrected the key from 'webhookUrl' to 'endpoint'
        data = {
            "endpoint": webhook_url
        }
        
        api_url = "https://api.line.me/v2/bot/channel/webhook/endpoint"
        response = requests.put(api_url, headers=headers, json=data)
        response.raise_for_status()
        
        print(f"Webhook URL updated successfully to {webhook_url}")
        return True, "Webhook URL updated successfully."
    except requests.exceptions.HTTPError as err:
        error_details = err.response.json()
        print(f"LINE API Error: {error_details}")
        return False, f"LINE API Error: {error_details.get('message', 'Unknown error')}"
    except Exception as e:
        print(f"Error updating webhook URL: {e}")
        return False, "Error updating LINE webhook URL."

# --- 3. Flask Routes ---

@app.route('/')
def home():
    """
    Serves the main web page for entering LINE Channel credentials.
    """
    return render_template_string('''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ตั้งค่า LINE Bot Webhook</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f3f4f6;
        }
    </style>
</head>
<body class="bg-gray-100 flex items-center justify-center min-h-screen p-4">

<div class="bg-white rounded-xl shadow-lg p-8 w-full max-w-lg">
    <h1 class="text-3xl font-bold text-center text-gray-800 mb-2">ตั้งค่า LINE Bot Webhook</h1>
    <p class="text-center text-gray-500 mb-6">กรุณากรอกข้อมูล Channel API ของคุณ</p>

    <!-- Form for Channel Credentials -->
    <form id="credentials-form" class="space-y-4">
        <div>
            <label for="channel-secret" class="block text-sm font-medium text-gray-700">Channel Secret</label>
            <input type="password" id="channel-secret" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500" required>
        </div>
        <div>
            <label for="channel-access-token" class="block text-sm font-medium text-gray-700">Channel Access Token</label>
            <input type="password" id="channel-access-token" class="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500" required>
        </div>
        <div class="flex items-center justify-center">
            <button type="submit" class="w-full inline-flex items-center justify-center px-4 py-2 border border-transparent text-base font-medium rounded-md shadow-sm text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500">
                บันทึกและสร้าง Webhook
            </button>
        </div>
    </form>

    <!-- Message and Webhook URL Display Area -->
    <div id="status-message" class="mt-6 text-center text-sm font-medium hidden"></div>
    <div id="webhook-url-container" class="mt-6 hidden">
        <p class="text-sm font-medium text-gray-700">Webhook URL ของคุณ:</p>
        <div class="mt-2 flex rounded-md shadow-sm">
            <input type="text" id="webhook-url" readonly class="flex-1 block w-full rounded-l-md px-3 py-2 border border-gray-300 bg-gray-50 cursor-text">
            <button id="copy-button" class="inline-flex items-center px-3 py-2 border border-gray-300 rounded-r-md bg-gray-200 text-sm font-medium text-gray-700 hover:bg-gray-300">
                คัดลอก
            </button>
        </div>
        <p class="mt-2 text-xs text-gray-500">
            โปรดนำ URL นี้ไปใส่ในช่อง **Webhook URL** บน LINE Developers Console ของคุณ
        </p>
    </div>
</div>

<script>
    // Get a unique user ID and store it in localStorage
    let userId = localStorage.getItem('uniqueUserId');
    if (!userId) {
        userId = crypto.randomUUID();
        localStorage.setItem('uniqueUserId', userId);
    }
    
    // Get elements from the DOM
    const form = document.getElementById('credentials-form');
    const statusMessage = document.getElementById('status-message');
    const webhookUrlContainer = document.getElementById('webhook-url-container');
    const webhookUrlInput = document.getElementById('webhook-url');
    const copyButton = document.getElementById('copy-button');

    // Handle form submission
    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        // Get user input
        const channelSecret = document.getElementById('channel-secret').value;
        const channelAccessToken = document.getElementById('channel-access-token').value;

        // Show loading message
        statusMessage.textContent = 'กำลังบันทึกข้อมูลและอัปเดต Webhook...';
        statusMessage.classList.remove('hidden', 'text-green-500', 'text-red-500');
        statusMessage.classList.add('block', 'text-blue-500');

        try {
            // Send data to the Flask backend
            const response = await fetch(`/save_credentials/${userId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    channelSecret: channelSecret,
                    channelAccessToken: channelAccessToken
                })
            });

            const data = await response.json();
            
            // Display status message
            if (response.ok) {
                statusMessage.textContent = data.message;
                statusMessage.classList.remove('text-blue-500', 'text-red-500');
                statusMessage.classList.add('text-green-500');
                
                // Show the generated webhook URL
                webhookUrlInput.value = data.webhook_url;
                webhookUrlContainer.classList.remove('hidden');
            } else {
                statusMessage.textContent = `เกิดข้อผิดพลาด: ${data.message}`;
                statusMessage.classList.remove('text-blue-500', 'text-green-500');
                statusMessage.classList.add('text-red-500');
                webhookUrlContainer.classList.add('hidden');
            }
        } catch (error) {
            statusMessage.textContent = 'เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์';
            statusMessage.classList.remove('text-blue-500', 'text-green-500');
            statusMessage.classList.add('text-red-500');
            console.error('Fetch error:', error);
        }
    });

    // Handle copy button click
    copyButton.addEventListener('click', () => {
        const url = webhookUrlInput.value;
        if (url) {
            navigator.clipboard.writeText(url).then(() => {
                // Show a temporary success message instead of an alert
                const originalText = copyButton.textContent;
                copyButton.textContent = 'คัดลอกแล้ว!';
                setTimeout(() => {
                    copyButton.textContent = originalText;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy text: ', err);
            });
        }
    });
</script>

</body>
</html>
    ''')


@app.route('/save_credentials/<user_id>', methods=['POST'])
def save_credentials(user_id):
    """
    Receives user credentials, saves them to SQLite, and updates the webhook.
    """
    print(f"--- Received POST request for user: {user_id} ---") # DEBUG
    try:
        data = request.json
        channel_secret = data.get('channelSecret')
        channel_access_token = data.get('channelAccessToken')

        print(f"Received data: Channel Secret: {channel_secret}, Channel Access Token: {channel_access_token}") # DEBUG

        if not channel_secret or not channel_access_token:
            print("Missing Channel Secret or Access Token.") # DEBUG
            return jsonify({'message': 'Missing Channel Secret or Access Token.'}), 400

        # Save credentials to SQLite
        if not add_credentials(user_id, channel_secret, channel_access_token):
            print("Failed to save credentials to database.") # DEBUG
            return jsonify({'message': 'Failed to save credentials to database.'}), 500

        # Dynamically create webhook URL
        #
        #
        # V V V V V V V V V V V V V V V V V V V V V V V V V V V V V V
        #
        # ขั้นตอนสำคัญ: URL นี้ถูกตั้งค่าให้แล้วโดยอัตโนมัติ
        #
        # ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^ ^
        #
        base_url = "https://4097df1bbb47.ngrok-free.app"
        webhook_url = f"{base_url}/webhook/{user_id}"
        print(f"Generated webhook_url: {webhook_url}") # DEBUG

        # Try to update LINE webhook automatically
        success, message = update_line_webhook(channel_access_token, webhook_url)
        
        response = {
            'message': message,
            'webhook_url': webhook_url
        }
        
        if success:
            return jsonify(response), 200
        else:
            return jsonify(response), 500

    except Exception as e:
        print(f"Error saving credentials: {e}")
        return jsonify({'message': f'Internal Server Error: {e}'}), 500

@app.route('/webhook/<user_id>', methods=['POST'])
def callback(user_id):
    """
    Handles LINE webhook events for a specific user ID.
    """
    print(f"--- LINE Webhook Request for user: {user_id} ---")

    # Get credentials from SQLite based on user_id
    credentials_data = get_credentials(user_id)

    if not credentials_data:
        print(f"Credentials not found for user ID: {user_id}")
        return 'Not Found', 404

    # The global handler is used for the decorator, but the dynamic handler is what we will use to handle the request.
    channel_secret_dynamic = credentials_data['channel_secret']
    line_bot_api_dynamic = LineBotApi(credentials_data['channel_access_token'])
    handler_dynamic = WebhookHandler(channel_secret_dynamic)

    # Get request body and signature
    body = request.get_data(as_text=True)
    signature = request.headers.get('X-Line-Signature')
    
    # Try to handle the webhook event
    try:
        # We need to tell the handler what to do with messages.
        # So we have to define a message handler for our dynamic handler.
        @handler_dynamic.add(MessageEvent, message=TextMessage)
        def handle_message(event):
            user_id_event = event.source.user_id
            user_message = event.message.text
            reply_token = event.reply_token

            # Add the user's message to the tasks queue
            add_new_task(user_id_event, reply_token, user_message)

            # Immediately send a "received" message back to the user
            try:
                line_bot_api_dynamic.reply_message(
                    reply_token,
                    TextSendMessage(text="ได้รับข้อความของคุณแล้วค่ะ กรุณารอสักครู่ กำลังดำเนินการค่ะ")
                )
            except Exception as e:
                print(f"Error replying to user: {e}")

        handler_dynamic.handle(body, signature)

    except InvalidSignatureError:
        print("Invalid signature. Please check your channel secret.")
        return 'Invalid signature', 400
    except LineBotApiError as e:
        print(f"LINE API Error: {e}")
        return 'LINE API Error', 500
    except Exception as e:
        print(f"Error handling webhook: {e}")
        return 'Internal Server Error', 500
    
    return 'OK', 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 9000))
    app.run(host='0.0.0.0', port=port)