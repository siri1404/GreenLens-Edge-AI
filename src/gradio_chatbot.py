import gradio as gr
import requests
import yaml
import asyncio
import httpx
import json

class Chatbot:
    def __init__(self):
        with open("config.yaml", "r") as file:
            config = yaml.safe_load(file)

        self.api_key = config["api_key"]
        self.base_url = config["model_server_base_url"]
        self.stream = config["stream"]
        self.stream_timeout = config["stream_timeout"]
        self.workspace_slug = config["workspace_slug"]

        if self.stream:
            self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/stream-chat"
        else:
            self.chat_url = f"{self.base_url}/workspace/{self.workspace_slug}/chat"

        self.headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + self.api_key
        }

    def chat(self, message: str) -> str:
        """
        Send a chat request in non-streaming mode.
        """
        data = {
            "message": message,
            "mode": "chat",
            "sessionId": "example-session-id",
            "attachments": []
        }
        chat_response = requests.post(
            self.chat_url,
            headers=self.headers,
            json=data
        )
        try:
            return chat_response.json()['textResponse']
        except ValueError:
            return "Response is not valid JSON"
        except Exception as e:
            return f"Chat request failed. Error: {e}"

    def streaming_chat(self, message: str):
        """
        Combined synchronous generator that wraps an asynchronous generator—
        it streams chat responses in chunks and yields the conversation history.
        """
        response_text = ""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        async def async_stream():
            data = {
                "message": message,
                "mode": "chat",
                "sessionId": "example-session-id",
                "attachments": []
            }
            buffer = ""
            try:
                async with httpx.AsyncClient(timeout=self.stream_timeout) as client:
                    async with client.stream("POST", self.chat_url, headers=self.headers, json=data) as response:
                        async for chunk in response.aiter_text():
                            if chunk:
                                buffer += chunk
                                # Process each complete line
                                while "\n" in buffer:
                                    line, buffer = buffer.split("\n", 1)
                                    if line.startswith("data: "):
                                        line = line[len("data: "):]
                                    try:
                                        parsed_chunk = json.loads(line.strip())
                                        yield parsed_chunk.get("textResponse", "")
                                    except json.JSONDecodeError:
                                        continue
                                    except Exception as e:
                                        yield f"Error processing chunk: {e}"
            except httpx.RequestError as e:
                yield f"Streaming chat request failed. Error: {e}"

        agen = async_stream()
        try:
            while True:
                chunk = loop.run_until_complete(agen.__anext__())
                response_text += chunk
                yield response_text
        except StopAsyncIteration:
            pass
        finally:
            loop.close()
        yield response_text

def main():
    chatbot = Chatbot()

    # Custom CSS for the floating chat icon and collapsible interface
    custom_css = """
    .floating-chat-icon {
        position: fixed;
        bottom: 20px;
        right: 20px;
        width: 60px;
        height: 60px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        cursor: pointer;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        transition: all 0.3s ease;
        z-index: 1000;
        border: none;
        color: white;
        font-size: 24px;
    }
    
    .floating-chat-icon:hover {
        transform: scale(1.1);
        box-shadow: 0 6px 20px rgba(0, 0, 0, 0.25);
    }
    
    #chat-container {
        position: fixed;
        bottom: 90px;
        right: 20px;
        width: 400px;
        height: 500px;
        background: white;
        border-radius: 12px;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
        display: none;
        flex-direction: column;
        z-index: 999;
        border: 1px solid #e0e0e0;
    }
    
    #chat-container.visible {
        display: flex !important;
        animation: slideUp 0.3s ease-out;
    }
    
    @keyframes slideUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .chat-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 15px;
        border-radius: 12px 12px 0 0;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    
    .chat-title {
        font-weight: 600;
        font-size: 16px;
    }
    
    .close-btn {
        background: none;
        border: none;
        color: white;
        font-size: 20px;
        cursor: pointer;
        padding: 0;
        width: 24px;
        height: 24px;
        display: flex;
        align-items: center;
        justify-content: center;
    }
    
    .close-btn:hover {
        background: rgba(255, 255, 255, 0.2);
        border-radius: 50%;
    }
    
    .chat-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        padding: 0;
    }
    
    .chat-messages {
        flex: 1;
        overflow-y: auto;
        padding: 15px;
    }
    
    .chat-input-area {
        padding: 15px;
        border-top: 1px solid #e0e0e0;
        background: #f8f9fa;
        border-radius: 0 0 12px 12px;
    }
    
    .chat-input {
        width: 100%;
        padding: 10px 12px;
        border: 1px solid #ddd;
        border-radius: 20px;
        outline: none;
        font-size: 14px;
    }
    
    .chat-input:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.2);
    }
    
    .send-btn {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 14px;
        margin-left: 8px;
        transition: all 0.2s ease;
    }
    
    .send-btn:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }
    
    .clear-btn {
        background: #6c757d;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 20px;
        cursor: pointer;
        font-size: 14px;
        margin-left: 8px;
        transition: all 0.2s ease;
    }
    
    .clear-btn:hover {
        background: #5a6268;
        transform: translateY(-1px);
    }
    """

    with gr.Blocks(css=custom_css) as app:
        # Floating chat icon
        chat_icon = gr.Button(
            "💬", 
            elem_classes=["floating-chat-icon"],
            visible=True
        )
        
        # Chat container (initially hidden)
        chat_container = gr.Column(
            elem_classes=["chat-container"], 
            visible=True,
            elem_id="chat-container"
        )
        
        with chat_container:
            # Chat header
            with gr.Row(elem_classes=["chat-header"]):
                gr.Markdown("### Chat Assistant", elem_classes=["chat-title"])
                close_btn = gr.Button("✕", elem_classes=["close-btn"])
            
            # Chat content
            with gr.Column(elem_classes=["chat-content"]):
                chatbot_widget = gr.Chatbot(
                    type="messages", 
                    height=350,
                    elem_classes=["chat-messages"]
                )
                
                # Input area
                with gr.Row(elem_classes=["chat-input-area"]):
                    msg = gr.Textbox(
                        placeholder="Type your message...", 
                        elem_classes=["chat-input"],
                        scale=4
                    )
                    send_btn = gr.Button("Send", elem_classes=["send-btn"], scale=1)
                    clear_btn = gr.Button("Clear", elem_classes=["clear-btn"], scale=1)

        def user_message(message, history):
            history.append({"role": "user", "content": message})
            return "", history

        def bot_response(history):
            user_msg = history[-1]["content"]
            if chatbot.stream:
                history.append({"role": "assistant", "content": ""})
                for updated in chatbot.streaming_chat(user_msg):
                    history[-1]["content"] = updated
                    yield history
            else:
                response = chatbot.chat(user_msg)
                history.append({"role": "assistant", "content": response})
                yield history

        # JavaScript to handle show/hide functionality
        app.load(
            None,
            None,
            None,
            js="""
            function() {
                // Hide chat container initially
                const chatContainer = document.getElementById('chat-container');
                if (chatContainer) {
                    chatContainer.style.display = 'none';
                }
                
                // Add click event to chat icon
                const chatIcon = document.querySelector('.floating-chat-icon');
                if (chatIcon) {
                    chatIcon.addEventListener('click', function() {
                        const chatContainer = document.getElementById('chat-container');
                        if (chatContainer) {
                            if (chatContainer.style.display === 'none') {
                                chatContainer.style.display = 'flex';
                                chatContainer.classList.add('visible');
                            } else {
                                chatContainer.style.display = 'none';
                                chatContainer.classList.remove('visible');
                            }
                        }
                    });
                }
                
                // Add click event to close button
                const closeBtn = document.querySelector('.close-btn');
                if (closeBtn) {
                    closeBtn.addEventListener('click', function() {
                        const chatContainer = document.getElementById('chat-container');
                        if (chatContainer) {
                            chatContainer.style.display = 'none';
                            chatContainer.classList.remove('visible');
                        }
                    });
                }
            }
            """
        )
        
        msg.submit(
            user_message, 
            [msg, chatbot_widget], 
            [msg, chatbot_widget], 
            queue=False
        ).then(
            bot_response, 
            chatbot_widget, 
            chatbot_widget
        )
        
        send_btn.click(
            user_message, 
            [msg, chatbot_widget], 
            [msg, chatbot_widget], 
            queue=False
        ).then(
            bot_response, 
            chatbot_widget, 
            chatbot_widget
        )
        
        clear_btn.click(
            lambda: None, 
            None, 
            chatbot_widget, 
            queue=False
        )

    app.launch()

if __name__ == "__main__":
    main()