import requests
import sys
import threading
import time
import yaml

# load config from yaml
with open("config.yaml", "r") as file:
    config = yaml.safe_load(file)

api_key = config["api_key"]
base_url = config["model_server_base_url"]
workspace_slug = config["workspace_slug"]

# workspace_slug = 'x-elite'
chat_url = f"{base_url}/workspace/{workspace_slug}/chat"

message_history = []

def loading_indicator():
    while not stop_loading:
        for _ in range(10):
            sys.stdout.write('.')
            sys.stdout.flush()
            time.sleep(0.5)
        sys.stdout.write('\r' + ' ' * 10 + '\r')
        sys.stdout.flush()
    print('')

def chat(message):
    global stop_loading
    stop_loading = False
    loading_thread = threading.Thread(target=loading_indicator)
    loading_thread.start()

    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key
    }

    message_history.append({
        "role": "user",
        "content": message
    })

    # create a short term memory bank with the last 20 messages
    short_term_memory = message_history[-20:]

    data = {
        "message": message,
        "mode": "chat",
        "sessionId": "example-session-id",
        "attachments": [],
        "history": short_term_memory
    }

    chat_response = requests.post(
        chat_url,
        headers=headers,
        json=data
    )

    stop_loading = True
    loading_thread.join()

    try:
        response_json = chat_response.json()
        message_history.append({
            "role": "assistant",
            "content": response_json['textResponse']
        })
        print("Agent: " + response_json['textResponse'])
    except ValueError:
        print("Response is not valid JSON")
    except Exception as e:
        print(f"Chat request failed. Error: {e}")

def main():
    while True:
        user_message = input("You: ")
        if user_message.lower() in ["exit", "quit"]:
            break
        chat(user_message)

if __name__ == '__main__':
    stop_loading = False
    main()