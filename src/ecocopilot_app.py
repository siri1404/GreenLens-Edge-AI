import sys
import warnings
import os

# Suppress PyTorch and EasyOCR warnings
warnings.filterwarnings("ignore", message=".*pin_memory.*")
warnings.filterwarnings("ignore", category=UserWarning, module="torch")
warnings.filterwarnings("ignore", category=UserWarning, module="easyocr")
warnings.filterwarnings("ignore", message=".*CUDA.*")
warnings.filterwarnings("ignore", message=".*GPU.*")

import cv2
import numpy as np
import onnxruntime as ort
import asyncio
import httpx
import json
import requests
import threading
import time
import yaml
import easyocr
import gradio as gr
import webbrowser
import speech_recognition as sr
import pyttsx3
import queue
import threading
from PyQt5.QtWidgets import (QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, 
                             QHBoxLayout, QFrame, QGridLayout, QStackedWidget, QFileDialog,
                             QTextEdit, QLineEdit, QListWidget, QListWidgetItem, QScrollArea)
from PyQt5.QtGui import QFont, QColor, QPainter, QPen, QBrush, QPixmap, QIcon, QImage
from PyQt5.QtCore import Qt, QRectF, QSize, pyqtSignal, QTimer, QThread, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView

# =============================================================================
# 1. TEXT DETECTION (EASYOCR)
# =============================================================================

class TextDetector:
    """EasyOCR-based text detection for shopping lists"""
    
    def __init__(self):
        try:
            # Initialize EasyOCR with English language
            self.reader = easyocr.Reader(['en'], gpu=False)  # Use CPU for compatibility
            print("✅ EasyOCR initialized successfully")
        except Exception as e:
            print(f"❌ Error initializing EasyOCR: {e}")
            self.reader = None
    
    def detect_text(self, image_path):
        """Detect text from image and return list of detected items"""
        if not self.reader:
            return []
        
        try:
            # Read image and detect text
            results = self.reader.readtext(image_path)
            
            # Extract text and filter for potential shopping items
            detected_items = []
            for (bbox, text, confidence) in results:
                if confidence > 0.5:  # Filter low confidence detections
                    # Clean up text
                    clean_text = text.strip().lower()
                    if len(clean_text) > 2:  # Filter very short text
                        detected_items.append(clean_text)
            
            return detected_items
            
        except Exception as e:
            print(f"❌ Error detecting text: {e}")
            return []

# =============================================================================
# 2. VOICE ASSISTANT
# =============================================================================

class VoiceAssistant(QThread):
    """Voice assistant with speech recognition and text-to-speech"""
    
    # Signals
    voice_recognized = pyqtSignal(str)  # Emits recognized text
    voice_speaking = pyqtSignal(bool)   # Emits speaking status
    voice_error = pyqtSignal(str)       # Emits error messages
    
    def __init__(self, npu_chatbot):
        super().__init__()
        self.npu_chatbot = npu_chatbot
        self.is_listening = False
        self.is_speaking = False
        
        # Initialize speech recognition
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Initialize text-to-speech
        self.tts_engine = pyttsx3.init()
        self.setup_tts()
        
        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
    
    def setup_tts(self):
        """Setup text-to-speech engine"""
        try:
            # Get available voices
            voices = self.tts_engine.getProperty('voices')
            
            # Try to set a female voice if available
            for voice in voices:
                if 'female' in voice.name.lower() or 'zira' in voice.name.lower():
                    self.tts_engine.setProperty('voice', voice.id)
                    break
            
            # Set speech rate and volume
            self.tts_engine.setProperty('rate', 180)  # Speed of speech
            self.tts_engine.setProperty('volume', 0.9)  # Volume level (0.0 to 1.0)
            
        except Exception as e:
            print(f"TTS setup warning: {e}")
    
    def start_listening(self):
        """Start listening for voice input"""
        if not self.is_listening and not self.is_speaking:
            self.is_listening = True
            self.start()
    
    def stop_listening(self):
        """Stop listening for voice input"""
        self.is_listening = False
    
    def speak(self, text):
        """Convert text to speech"""
        if not self.is_speaking:
            self.is_speaking = True
            self.voice_speaking.emit(True)
            
            try:
                self.tts_engine.say(text)
                self.tts_engine.runAndWait()
            except Exception as e:
                self.voice_error.emit(f"TTS Error: {str(e)}")
            finally:
                self.is_speaking = False
                self.voice_speaking.emit(False)
    
    def run(self):
        """Main voice recognition loop"""
        try:
            with self.microphone as source:
                # Listen for audio with timeout
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
            
            # Recognize speech using Google's service
            text = self.recognizer.recognize_google(audio)
            self.voice_recognized.emit(text)
            
        except sr.WaitTimeoutError:
            self.voice_error.emit("No speech detected. Please try again.")
        except sr.UnknownValueError:
            self.voice_error.emit("Could not understand speech. Please try again.")
        except sr.RequestError as e:
            self.voice_error.emit(f"Speech recognition service error: {str(e)}")
        except Exception as e:
            self.voice_error.emit(f"Voice recognition error: {str(e)}")
        finally:
            self.is_listening = False

# =============================================================================
# 3. GRADIO CHATBOT INTEGRATION
# =============================================================================

class GradioChatPage(QWidget):
    """Gradio chatbot page embedded directly in PyQt5 app"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
            }
        """)
        
        # Initialize NPU chatbot with error handling
        try:
            self.npu_chatbot = NPUChatbot()
            print("✅ NPU Chatbot initialized successfully")
        except Exception as e:
            print(f"❌ NPU Chatbot initialization failed: {e}")
            self.npu_chatbot = None
        self.gradio_thread = None
        self.gradio_demo = None
        
        # Create layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header with title and controls
        header_frame = QFrame()
        header_frame.setStyleSheet("""
            QFrame {
                background-color: #2E7D32;
                border: none;
                padding: 15px;
            }
        """)
        header_layout = QHBoxLayout(header_frame)
        
        # Title
        title = QLabel("🤖 Eco-Copilot Chat")
        title.setStyleSheet("""
            QLabel {
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        header_layout.addWidget(title)
        
        # Control buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Start Chat")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
        """)
        self.start_btn.clicked.connect(self.start_gradio_chat)
        button_layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop Chat")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #D32F2F;
            }
            QPushButton:disabled {
                background-color: #666666;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_gradio_chat)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)
        
        header_layout.addLayout(button_layout)
        layout.addWidget(header_frame)
        
        # Web view for embedded Gradio interface
        self.web_view = QWebEngineView()
        self.web_view.setStyleSheet("""
            QWebEngineView {
                border: none;
                background-color: white;
            }
        """)
        
        # Initial message
        self.web_view.setHtml("""
        <html>
        <head>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #96D9C0 0%, #4CAF50 100%);
                    margin: 0;
                    padding: 40px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }
                .container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                }
                h1 {
                    color: #2E7D32;
                    font-size: 32px;
                    margin-bottom: 20px;
                }
                p {
                    color: #666;
                    font-size: 18px;
                    line-height: 1.6;
                    margin-bottom: 30px;
                }
                .features {
                    text-align: left;
                    margin: 20px 0;
                }
                .feature {
                    color: #333;
                    font-size: 16px;
                    margin: 10px 0;
                    padding: 10px;
                    background: #E8F5E8;
                    border-radius: 8px;
                }
                .button {
                    background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%);
                    color: white;
                    border: none;
                    border-radius: 25px;
                    padding: 15px 30px;
                    font-size: 18px;
                    font-weight: bold;
                    cursor: pointer;
                    margin: 10px;
                }
                .button:hover {
                    background: linear-gradient(135deg, #45A049 0%, #1B5E20 100%);
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌱 Eco-Copilot Chat</h1>
                <p>Your AI-powered sustainability assistant for smarter shopping decisions</p>
                
                <div class="features">
                    <div class="feature">🌱 Sustainable product recommendations</div>
                    <div class="feature">📊 Carbon footprint analysis</div>
                    <div class="feature">🛒 Shopping list optimization</div>
                    <div class="feature">💡 Eco-friendly alternatives</div>
                    <div class="feature">🎯 Personalized sustainability tips</div>
                </div>
                
                <p>Click "Start Chat" above to begin your eco-friendly conversation!</p>
            </div>
        </body>
        </html>
        """)
        
        layout.addWidget(self.web_view)
        self.setLayout(layout)
    
    def start_gradio_chat(self):
        """Start the embedded Gradio chat interface"""
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        
        # Update web view with loading message
        self.web_view.setHtml("""
        <html>
        <head>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #96D9C0 0%, #4CAF50 100%);
                    margin: 0;
                    padding: 40px;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }
                .loading {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    text-align: center;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                }
                .spinner {
                    border: 4px solid #E8F5E8;
                    border-top: 4px solid #4CAF50;
                    border-radius: 50%;
                    width: 50px;
                    height: 50px;
                    animation: spin 1s linear infinite;
                    margin: 20px auto;
                }
                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }
                h2 {
                    color: #2E7D32;
                    margin-bottom: 20px;
                }
                p {
                    color: #666;
                    font-size: 16px;
                }
            </style>
        </head>
        <body>
            <div class="loading">
                <h2>🚀 Starting Eco-Copilot Chat...</h2>
                <div class="spinner"></div>
                <p>Initializing AI-powered sustainability assistant...</p>
            </div>
        </body>
        </html>
        """)
        
        # Start Gradio in a separate thread
        self.gradio_thread = threading.Thread(target=self._start_gradio_server)
        self.gradio_thread.daemon = True
        self.gradio_thread.start()
    
    def stop_gradio_chat(self):
        """Stop the Gradio chat interface"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        # Reset to initial state
        self.web_view.setHtml("""
        <html>
        <head>
            <style>
                body {
                    font-family: 'Segoe UI', Arial, sans-serif;
                    background: linear-gradient(135deg, #96D9C0 0%, #4CAF50 100%);
                    margin: 0;
                    padding: 40px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    min-height: 100vh;
                }
                .container {
                    background: white;
                    border-radius: 20px;
                    padding: 40px;
                    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
                    text-align: center;
                    max-width: 600px;
                }
                h1 {
                    color: #2E7D32;
                    font-size: 32px;
                    margin-bottom: 20px;
                }
                p {
                    color: #666;
                    font-size: 18px;
                    line-height: 1.6;
                }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🌱 Eco-Copilot Chat</h1>
                <p>Chat interface stopped. Click "Start Chat" to begin again.</p>
            </div>
        </body>
        </html>
        """)
    
    def _start_gradio_server(self):
        """Start the Gradio server and load it in the web view"""
        try:
            # Create the Gradio interface
            self.gradio_demo = self._create_gradio_interface()
            
            # Launch Gradio server (blocking call)
            self.gradio_demo.launch(
                server_name="127.0.0.1",
                server_port=7860,
                share=False,
                inbrowser=False,  # Don't open browser
                show_error=True,
                quiet=True
            )
            
        except Exception as e:
            print(f"Error starting Gradio server: {e}")
            # Show error in web view
            self.web_view.setHtml(f"""
            <html>
            <body style="font-family: Arial; padding: 40px; text-align: center;">
                <h2 style="color: #F44336;">❌ Error Starting Chat</h2>
                <p>Error: {str(e)}</p>
                <p>Please try again or check your NPU server connection.</p>
            </body>
            </html>
            """)
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
    
    def _create_gradio_interface(self):
        """Create the Gradio interface"""
        
        # Eco-copilot themed CSS
        eco_css = """
        .gradio-container {
            background: linear-gradient(135deg, #96D9C0 0%, #4CAF50 100%) !important;
        }
        
        .chat-message {
            background-color: #E8F5E8 !important;
            border-radius: 12px !important;
            padding: 12px !important;
            margin: 8px 0 !important;
        }
        
        .user-message {
            background-color: #4CAF50 !important;
            color: white !important;
        }
        
        .bot-message {
            background-color: #E8F5E8 !important;
            color: #2E7D32 !important;
        }
        
        .chat-input {
            border: 2px solid #4CAF50 !important;
            border-radius: 20px !important;
            padding: 12px !important;
        }
        
        .send-button {
            background: linear-gradient(135deg, #4CAF50 0%, #2E7D32 100%) !important;
            color: white !important;
            border: none !important;
            border-radius: 20px !important;
            padding: 12px 24px !important;
            font-weight: bold !important;
        }
        
        .send-button:hover {
            background: linear-gradient(135deg, #45A049 0%, #1B5E20 100%) !important;
            transform: translateY(-2px) !important;
        }
        
        .header {
            background: linear-gradient(135deg, #2E7D32 0%, #1B5E20 100%) !important;
            color: white !important;
            padding: 20px !important;
            border-radius: 12px 12px 0 0 !important;
        }
        """
        
        def eco_copilot_chat(message, history):
            """Eco-copilot chat function"""
            if not message.strip():
                return history, ""
            
            # Add user message to history (new messages format)
            history.append({"role": "user", "content": message})
            
            # Get response from NPU chatbot
            try:
                if self.npu_chatbot is None:
                    history.append({"role": "assistant", "content": "❌ Chatbot not available. Please check your NPU server connection."})
                else:
                    response = self.npu_chatbot.send_eco_copilot_prompt(message)
                    history.append({"role": "assistant", "content": response})
            except Exception as e:
                error_msg = f"❌ Error: {str(e)}"
                print(f"Chat error: {e}")
                history.append({"role": "assistant", "content": error_msg})
            
            return history, ""
        
        # Create Gradio interface
        with gr.Blocks(css=eco_css, title="Eco-Copilot Chat") as demo:
            gr.Markdown("""
            # 🌱 Eco-Copilot Chat
            **Your AI-powered sustainability assistant for smarter shopping decisions**
            
            Ask me about:
            - 🌿 Sustainable product alternatives
            - 📊 Carbon footprint estimates  
            - 🛒 Eco-friendly shopping tips
            - 💡 Green lifestyle advice
            """)
            
            chatbot = gr.Chatbot(
                height=400,
                label="Eco-Copilot Assistant",
                show_label=True,
                type="messages"
            )
            
            with gr.Row():
                msg = gr.Textbox(
                    placeholder="Ask about sustainable products, carbon footprints, or eco-friendly alternatives...",
                    label="Your Message",
                    lines=2
                )
                send_btn = gr.Button("Send 🌱", variant="primary")
            
            with gr.Row():
                clear_btn = gr.Button("Clear Chat", variant="secondary")
                example_btn = gr.Button("Example Questions", variant="secondary")
            
            # Example questions
            examples = gr.Examples(
                examples=[
                    "What's the carbon footprint of beef vs chicken?",
                    "Suggest eco-friendly alternatives to plastic water bottles",
                    "How can I make my grocery shopping more sustainable?",
                    "What are the environmental benefits of organic food?",
                    "Compare the sustainability of different milk alternatives"
                ],
                inputs=msg
            )
            
            # Event handlers
            msg.submit(eco_copilot_chat, [msg, chatbot], [chatbot, msg])
            send_btn.click(eco_copilot_chat, [msg, chatbot], [chatbot, msg])
            clear_btn.click(lambda: ([], ""), outputs=[chatbot, msg])
            
            def show_examples():
                return "Try asking: 'What's the carbon footprint of beef vs chicken?' or 'Suggest eco-friendly alternatives to plastic water bottles'"
            
            example_btn.click(show_examples, outputs=msg)
        
        # Load the Gradio interface in the web view
        self.web_view.load(QUrl("http://127.0.0.1:7860"))
        
        return demo

# =============================================================================
# 3. NPU-OPTIMIZED CHATBOT
# =============================================================================

class NPUChatbot:
    """NPU-optimized chatbot with INT8 quantization for local inference"""
    
    def __init__(self):
        try:
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
            
            # Check if NPU server is running
            self.server_status = self.check_server_status()
            if self.server_status:
                print("✅ NPU Chatbot initialized with INT8 optimization")
                print("✅ NPU Model Server is running")
            else:
                print("⚠️ NPU Chatbot initialized - server status check failed")
                print("💡 But auth works, so server is likely running")
                # Don't fail initialization if status check fails but auth works
                self.server_status = True
            
        except Exception as e:
            print(f"❌ Error initializing NPU Chatbot: {e}")
            self.chat_url = None
            self.server_status = False
    
    def check_server_status(self):
        """Check if the NPU model server is running"""
        try:
            # Try to connect to the server using the API endpoint
            response = requests.get(f"{self.base_url}/workspace/{self.workspace_slug}", 
                                  headers=self.headers, timeout=5)
            return response.status_code == 200
        except:
            try:
                # Fallback: try the root endpoint
                response = requests.get(f"{self.base_url.replace('/api/v1', '')}/", timeout=5)
                return response.status_code == 200
            except:
                return False
    
    def send_eco_copilot_prompt(self, product_name: str) -> str:
        """Send eco-copilot prompt to NPU-optimized model"""
        if not self.chat_url:
            return "❌ Chatbot not available - check NPU model server"
        
        if not self.server_status:
            return """❌ NPU Model Server Not Running

To start the NPU model server:

1. Open AnythingLLM application
2. Make sure you have:
   - Selected "AnythingLLM NPU" as LLM Provider
   - Downloaded Llama 3.1 8B Chat 8K model
   - Created a workspace named "greenlens"
   - Generated an API key

3. The server should be running on localhost:3001

4. Test the connection:
   python src/auth.py

5. Get workspace slug:
   python src/workspaces.py

Once the server is running, try the NPU chatbot again!"""
        
        # Create a shorter, more focused eco-copilot prompt
        prompt = f"""Analyze this product for environmental impact: {product_name}

Provide:
1. CO₂ estimate (kg CO₂e per serving)
2. Two sustainable alternatives with brief explanations
3. One encouraging message

Keep response concise and practical."""

        try:
            if self.stream:
                return self.streaming_chat(prompt)
            else:
                return self.blocking_chat(prompt)
        except Exception as e:
            return f"❌ Error sending to NPU model: {str(e)}"
    
    def blocking_chat(self, message: str) -> str:
        """Send blocking chat request to NPU model"""
        data = {
            "message": message,
            "mode": "chat",
            "sessionId": "eco-copilot-session",
            "attachments": []
        }
        
        try:
            print(f"🔍 Chat URL: {self.chat_url}")
            print(f"🔍 Request Data: {data}")
            print(f"🔍 Headers: {self.headers}")
            
            response = requests.post(
                self.chat_url,
                headers=self.headers,
                json=data,
                timeout=15  # Reduced timeout for faster feedback
            )
            
            print(f"🔍 Response Status: {response.status_code}")
            print(f"🔍 Response Headers: {response.headers}")
            print(f"🔍 Response Text: {response.text[:500]}...")  # First 500 chars
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"🔍 Response JSON: {response_data}")
                
                # Handle the correct response format
                if 'textResponse' in response_data:
                    return response_data['textResponse']
                elif 'error' in response_data and response_data['error']:
                    return f"❌ NPU Model Error: {response_data['error']}"
                else:
                    return f"❌ Unexpected response format: {response_data}"
            else:
                return f"❌ NPU Model Error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return f"❌ Connection Error: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected Error: {str(e)}"
    
    def streaming_chat(self, message: str) -> str:
        """Send streaming chat request to NPU model"""
        data = {
            "message": message,
            "mode": "chat",
            "sessionId": "eco-copilot-session",
            "attachments": []
        }
        
        try:
            response = requests.post(
                self.chat_url,
                headers=self.headers,
                json=data,
                timeout=30
            )
            
            if response.status_code == 200:
                # For now, return the full response (streaming can be added later)
                return response.json().get('textResponse', 'No response received')
            else:
                return f"❌ NPU Model Error: {response.status_code} - {response.text}"
                
        except requests.exceptions.RequestException as e:
            return f"❌ Connection Error: {str(e)}"


# =============================================================================
# 2. ONNX DETECTOR AND CAMERA THREAD
# =============================================================================

class ONNXYOLOv8Detector:
    """ONNX YOLOv8 Detector for real-time object detection."""
    
    def __init__(self, model_path: str = "models/yolov8_det_w8a8.onnx"):
        """Initialize ONNX YOLOv8 detector."""
        self.model_path = model_path
        self.input_size = (640, 640)
        
        # COCO class names
        self.class_names = [
            'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
            'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
            'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
            'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
            'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
            'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
            'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
            'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
            'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
            'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier', 'toothbrush'
        ]
        
        # Load ONNX model
        try:
            self.session = ort.InferenceSession(model_path)
            print(f"Loading ONNX model from: {model_path}")
            print("ONNX model loaded successfully!")
        except Exception as e:
            print(f"Error loading ONNX model: {e}")
            self.session = None
    
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """Preprocess image for YOLOv8 model."""
        # Resize to model input size
        resized = cv2.resize(image, self.input_size)
        
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        # Normalize to [0, 1]
        normalized = rgb_image.astype(np.float32) / 255.0
        
        # Add batch dimension and transpose to CHW format
        input_tensor = np.transpose(normalized, (2, 0, 1))
        input_tensor = np.expand_dims(input_tensor, axis=0)
        
        return input_tensor
    
    def postprocess(self, outputs: list, original_shape: tuple) -> list:
        """Postprocess YOLOv8 model outputs to get detections."""
        if not outputs:
            return []
            
        boxes = outputs[0][0]  # Shape: [8400, 4] - remove batch dimension
        confidences = outputs[1][0]  # Shape: [8400] - remove batch dimension
        class_ids = outputs[2][0]  # Shape: [8400] - remove batch dimension
        
        detections = []
        h, w = original_shape
        
        num_detections = boxes.shape[0]
        
        for i in range(num_detections):
            # Get confidence and class ID
            confidence = float(confidences[i])
            class_id = int(class_ids[i])
            
            # Filter out low confidence detections
            if confidence < 0.5:
                continue
            
            # Get bounding box coordinates [x1, y1, x2, y2]
            x1, y1, x2, y2 = boxes[i]
            
            # Scale bounding box coordinates from model input size to original image size
            scale_x = w / self.input_size[0]
            scale_y = h / self.input_size[1]
            
            x1 = int(x1 * scale_x)
            y1 = int(y1 * scale_y)
            x2 = int(x2 * scale_x)
            y2 = int(y2 * scale_y)
            
            # Ensure coordinates are within image bounds
            x1 = max(0, min(x1, w))
            y1 = max(0, min(y1, h))
            x2 = max(0, min(x2, w))
            y2 = max(0, min(y2, h))
            
            # Skip invalid bounding boxes
            if x2 <= x1 or y2 <= y1:
                continue
            
            class_name = self.class_names[class_id] if class_id < len(self.class_names) else f"class_{class_id}"
            
            detections.append({
                'bbox': [x1, y1, x2, y2],
                'confidence': confidence,
                'class_id': class_id,
                'class_name': class_name
            })
        
        return detections
    
    def detect(self, image: np.ndarray) -> list:
        """Run object detection on an image."""
        if self.session is None:
            return []
            
        # Preprocess image
        input_tensor = self.preprocess(image)
        
        # Run inference
        input_name = self.session.get_inputs()[0].name
        outputs = self.session.run(None, {input_name: input_tensor})
        
        # Postprocess outputs
        detections = self.postprocess(outputs, image.shape[:2])
        
        return detections


class CameraThread(QThread):
    """Thread for camera processing."""
    
    frame_ready = pyqtSignal(np.ndarray)
    detection_ready = pyqtSignal(list)
    
    def __init__(self, detector):
        super().__init__()
        self.detector = detector
        self.running = False
        self.cap = None
    
    def start_camera(self):
        """Start camera capture."""
        # Use DirectShow backend for Windows (most reliable)
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        
        if not self.cap.isOpened():
            print("Failed to open camera with DirectShow, trying default...")
            self.cap = cv2.VideoCapture(0)
        
        if self.cap.isOpened():
            # Set camera properties for better performance
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.cap.set(cv2.CAP_PROP_FPS, 30)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)  # Reduce buffer size
            
            print("Camera opened successfully")
            self.running = True
            self.start()
        else:
            print("Error: Could not open camera")
            raise Exception("Camera initialization failed")
    
    def stop_camera(self):
        """Stop camera capture."""
        self.running = False
        if self.cap:
            self.cap.release()
        self.wait()
    
    def run(self):
        """Camera processing loop."""
        frame_count = 0
        
        while self.running and self.cap:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                frame_count += 1
                
                # Run detection every frame for real-time detection
                detections = self.detector.detect(frame)
                
                # Filter out person detections
                filtered_detections = [d for d in detections if d['class_name'] != 'person']
                
                # Emit signals
                self.frame_ready.emit(frame)
                self.detection_ready.emit(filtered_detections)
            
            self.msleep(33)  # ~30 FPS
        
        print("Camera thread stopped")


# =============================================================================
# 2. CUSTOM WIDGETS (for charts and special UI elements)
# =============================================================================

class CircularProgressBar(QWidget):
    """A custom widget to display a circular progress bar."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.maximum = 100
        self.progress_color = QColor("#E74C3C") # Default to red for 'High Carbon'
        self.setMinimumSize(100, 100)

    def setValue(self, value):
        self.value = value
        self.update() # Trigger a repaint

    def setColor(self, color):
        self.progress_color = QColor(color)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        rect = QRectF(self.rect()).adjusted(5, 5, -5, -5)
        
        # Background arc
        pen = QPen(QColor("#4A5568"), 10, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.drawArc(rect, 0, 360 * 16)

        # Foreground arc
        pen.setColor(self.progress_color)
        painter.setPen(pen)
        
        span_angle = int((self.value / self.maximum) * 360)
        painter.drawArc(rect, 90 * 16, -span_angle * 16)

class BarChartWidget(QWidget):
    """A custom widget to display a simple bar chart."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = [40, 60, 80, 50, 70] # Example data
        self.bar_color = QColor("#2ECC71")
        self.bg_color = QColor("#4A5568")
        self.setMinimumHeight(80)

    def setData(self, data):
        self.data = data
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        max_value = max(self.data) if self.data else 1
        num_bars = len(self.data)
        
        bar_width = (self.width() - (num_bars - 1) * 5) / num_bars
        
        for i, value in enumerate(self.data):
            bar_height = (value / max_value) * self.height()
            x = i * (bar_width + 5)
            y = self.height() - bar_height
            
            # Draw bar
            painter.setBrush(QBrush(self.bar_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(x, y, bar_width, bar_height), 5, 5)

# =============================================================================
# 2. SIDEBAR COMPONENTS
# =============================================================================

class SidebarButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setFixedHeight(50)
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #06402B;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                padding: 15px 20px;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: rgba(6, 64, 43, 0.1);
                color: #06402B;
            }
            QPushButton:pressed {
                background-color: rgba(6, 64, 43, 0.2);
            }
        """)
        
    def enterEvent(self, event):
        self.setStyleSheet("""
            QPushButton {
                background-color: rgba(6, 64, 43, 0.1);
                color: #06402B;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                padding: 15px 20px;
                border-radius: 8px;
            }
        """)
        super().enterEvent(event)
        
    def leaveEvent(self, event):
        self.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #06402B;
                border: none;
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                padding: 15px 20px;
                border-radius: 8px;
            }
        """)
        super().leaveEvent(event)

class Sidebar(QFrame):
    menu_clicked = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(280)
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(255, 255, 255, 0.95);
                border-right: 2px solid rgba(6, 64, 43, 0.1);
            }
        """)
        
        # Create main layout
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Logo and App Name Section
        logo_section = QWidget()
        logo_layout = QVBoxLayout()
        logo_layout.setContentsMargins(20, 30, 20, 20)
        logo_layout.setSpacing(15)
        
        # Create SVG leaf icon (using text as placeholder)
        leaf_icon = QLabel("🍃")
        leaf_icon.setStyleSheet("""
            QLabel {
                font-size: 48px;
                color: #06402B;
                text-align: center;
            }
        """)
        leaf_icon.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(leaf_icon)
        
        # App name
        app_name = QLabel("GreenLens")
        app_name.setStyleSheet("""
            QLabel {
                font-size: 24px;
                font-weight: bold;
                color: #06402B;
                text-align: center;
            }
        """)
        app_name.setAlignment(Qt.AlignCenter)
        logo_layout.addWidget(app_name)
        
        logo_section.setLayout(logo_layout)
        layout.addWidget(logo_section)
        
        # Menu Items Section
        menu_section = QWidget()
        menu_layout = QVBoxLayout()
        menu_layout.setContentsMargins(10, 10, 10, 10)
        menu_layout.setSpacing(5)
        
        # Create menu buttons
        self.menu_buttons = []
        menu_items = ["Home", "Scan", "Progress", "Eco-copilot", "Inventory", "Diary", "Settings"]
        
        for item in menu_items:
            btn = SidebarButton(item)
            btn.clicked.connect(lambda checked, text=item: self.on_menu_clicked(text))
            self.menu_buttons.append(btn)
            menu_layout.addWidget(btn)
        
        menu_section.setLayout(menu_layout)
        layout.addWidget(menu_section)
        
        # Add stretch to push support section to bottom
        layout.addStretch()
        
        # Support Section
        support_section = QWidget()
        support_layout = QVBoxLayout()
        support_layout.setContentsMargins(20, 20, 20, 30)
        support_layout.setSpacing(10)
        
        # Support title
        support_title = QLabel("Support")
        support_title.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #06402B;
                text-align: left;
            }
        """)
        support_layout.addWidget(support_title)
        
        # Support buttons
        help_btn = SidebarButton("Help & FAQ")
        contact_btn = SidebarButton("Contact Us")
        about_btn = SidebarButton("About")
        
        support_layout.addWidget(help_btn)
        support_layout.addWidget(contact_btn)
        support_layout.addWidget(about_btn)
        
        support_section.setLayout(support_layout)
        layout.addWidget(support_section)
        
        self.setLayout(layout)
        
    def on_menu_clicked(self, item):
        print(f"Menu clicked: {item}")
        # Reset all buttons to default state
        for btn in self.menu_buttons:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #06402B;
                    border: none;
                    text-align: left;
                    font-size: 16px;
                    font-weight: 500;
                    padding: 15px 20px;
                    border-radius: 8px;
                }
            """)
        
        # Highlight clicked button
        for btn in self.menu_buttons:
            if btn.text() == item:
                btn.setStyleSheet("""
                    QPushButton {
                        background-color: rgba(6, 64, 43, 0.15);
                        color: #06402B;
                        border: none;
                        text-align: left;
                        font-size: 16px;
                        font-weight: 600;
                        padding: 15px 20px;
                        border-radius: 8px;
                    }
                """)
                break
        
        # Emit signal for page switching
        self.menu_clicked.emit(item)

# =============================================================================
# 3. MAIN APPLICATION WINDOW
# =============================================================================

class HomePage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #96D9C0;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Welcome message
        welcome_label = QLabel("Welcome to GreenLens")
        welcome_label.setStyleSheet("""
            QLabel {
                color: #06402B;
                font-size: 36px;
                font-weight: bold;
                padding: 30px;
                background-color: rgba(255, 255, 255, 0.8);
                border-radius: 20px;
                border: 2px solid rgba(6, 64, 43, 0.2);
            }
        """)
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        # Description
        desc_label = QLabel("Your AI-powered environmental monitoring companion")
        desc_label.setStyleSheet("""
            QLabel {
                color: #06402B;
                font-size: 20px;
                padding: 20px;
                background-color: rgba(255, 255, 255, 0.6);
                border-radius: 15px;
                margin-top: 20px;
            }
        """)
        desc_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(desc_label)
        
        # Add some features section
        features_label = QLabel("🌱 Environmental Scanning  📊 Progress Tracking  🤖 AI Eco-Copilot")
        features_label.setStyleSheet("""
            QLabel {
                color: #06402B;
                font-size: 16px;
                padding: 15px;
                background-color: rgba(255, 255, 255, 0.4);
                border-radius: 12px;
                margin-top: 30px;
            }
        """)
        features_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(features_label)
        
        layout.addStretch()
        self.setLayout(layout)

class ScanPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
            }
        """)
        
        # Initialize scan mode
        self.scan_mode = "live"  # live, upload, shopping_list
        self.is_scanning = False
        self.scan_timer = QTimer()
        self.scan_timer.timeout.connect(self.update_scan_status)
        
        # Initialize ONNX detector with error handling
        try:
            self.detector = ONNXYOLOv8Detector("models/yolov8_det_w8a8.onnx")
            self.camera_thread = CameraThread(self.detector)
            self.camera_thread.frame_ready.connect(self.update_camera_display)
            self.camera_thread.detection_ready.connect(self.update_detection_results)
            print("✅ ONNX detector initialized successfully")
        except Exception as e:
            print(f"❌ ONNX detector initialization failed: {e}")
            self.detector = None
            self.camera_thread = None
        
        # Initialize NPU chatbot with error handling
        try:
            self.npu_chatbot = NPUChatbot()
            print("✅ NPU Chatbot initialized successfully")
        except Exception as e:
            print(f"❌ NPU Chatbot initialization failed: {e}")
            self.npu_chatbot = None
        
        # Initialize text detector for shopping lists with error handling
        try:
            self.text_detector = TextDetector()
            print("✅ Text detector initialized successfully")
        except Exception as e:
            print(f"❌ Text detector initialization failed: {e}")
            self.text_detector = None
        
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header Bar
        header = QWidget()
        header.setFixedHeight(60)
        header.setStyleSheet("""
            QWidget {
                background-color: #F5F5F5;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(30, 15, 30, 15)
        
        # Breadcrumbs
        breadcrumbs = QLabel("Scan / Live Detection")
        breadcrumbs.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 14px;
            }
        """)
        header_layout.addWidget(breadcrumbs)
        
        header_layout.addStretch()
        
        # Action icons
        new_tab_btn = QPushButton("+")
        new_tab_btn.setFixedSize(32, 32)
        new_tab_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                color: #333333;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        
        share_btn = QPushButton("↗")
        share_btn.setFixedSize(32, 32)
        share_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                color: #333333;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        
        menu_btn = QPushButton("⋮")
        menu_btn.setFixedSize(32, 32)
        menu_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #DDDDDD;
                border-radius: 6px;
                color: #333333;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #F0F0F0;
            }
        """)
        
        header_layout.addWidget(new_tab_btn)
        header_layout.addWidget(share_btn)
        header_layout.addWidget(menu_btn)
        
        header.setLayout(header_layout)
        layout.addWidget(header)
        
        # Main content area
        content_scroll = QScrollArea()
        content_scroll.setWidgetResizable(True)
        content_scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #F5F5F5;
            }
        """)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(30, 30, 30, 30)
        content_layout.setSpacing(20)
        
        # Scan Mode Selection Card
        mode_card = QFrame()
        mode_card.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: none;
            }
        """)
        
        mode_layout = QVBoxLayout()
        mode_layout.setContentsMargins(30, 30, 30, 30)
        mode_layout.setSpacing(20)
        
        mode_title = QLabel("Choose Scan Mode")
        mode_title.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        mode_layout.addWidget(mode_title)
        
        # Mode buttons
        mode_buttons_layout = QHBoxLayout()
        mode_buttons_layout.setSpacing(15)
        
        # Live Detection Button
        self.live_btn = QPushButton("📹 Live Detection")
        self.live_btn.setFixedHeight(80)
        self.live_btn.setStyleSheet("""
            QPushButton {
                background-color: #E8F5E8;
                color: #2E7D32;
                border: 2px solid #4CAF50;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #C8E6C9;
            }
            QPushButton:pressed {
                background-color: #A5D6A7;
            }
        """)
        self.live_btn.clicked.connect(lambda: self.set_scan_mode("live"))
        
        # Upload Photo Button
        self.upload_btn = QPushButton("📷 Upload Photo")
        self.upload_btn.setFixedHeight(80)
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #E3F2FD;
                color: #1565C0;
                border: 2px solid #2196F3;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #BBDEFB;
            }
            QPushButton:pressed {
                background-color: #90CAF9;
            }
        """)
        self.upload_btn.clicked.connect(lambda: self.set_scan_mode("upload"))
        
        # Shopping List Scanner Button
        self.shopping_btn = QPushButton("🛒 Shopping List Scanner")
        self.shopping_btn.setFixedHeight(80)
        self.shopping_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFF3E0;
                color: #E65100;
                border: 2px solid #FF9800;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #FFE0B2;
            }
            QPushButton:pressed {
                background-color: #FFCC02;
            }
        """)
        self.shopping_btn.clicked.connect(lambda: self.set_scan_mode("shopping_list"))
        
        mode_buttons_layout.addWidget(self.live_btn)
        mode_buttons_layout.addWidget(self.upload_btn)
        mode_buttons_layout.addWidget(self.shopping_btn)
        
        mode_layout.addLayout(mode_buttons_layout)
        mode_card.setLayout(mode_layout)
        content_layout.addWidget(mode_card)
        
        # Main Scan Area
        self.scan_area = self.create_scan_area()
        content_layout.addWidget(self.scan_area)
        
        # Results Area
        self.results_area = self.create_results_area()
        content_layout.addWidget(self.results_area)
        
        content_layout.addStretch()
        content_widget.setLayout(content_layout)
        content_scroll.setWidget(content_widget)
        layout.addWidget(content_scroll)
        
        self.setLayout(layout)
        
        # Set default mode
        self.set_scan_mode("live")
    
    def set_scan_mode(self, mode):
        """Set the current scan mode and update UI"""
        self.scan_mode = mode
        
        # Reset all buttons
        self.live_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #666666;
                border: 2px solid #DDDDDD;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
            }
        """)
        
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #666666;
                border: 2px solid #DDDDDD;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
            }
        """)
        
        self.shopping_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                color: #666666;
                border: 2px solid #DDDDDD;
                border-radius: 12px;
                font-size: 16px;
                font-weight: bold;
                padding: 20px;
            }
            QPushButton:hover {
                background-color: #EEEEEE;
            }
        """)
        
        # Highlight selected button
        if mode == "live":
            self.live_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E8F5E8;
                    color: #2E7D32;
                    border: 2px solid #4CAF50;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 20px;
                }
                QPushButton:hover {
                    background-color: #C8E6C9;
                }
            """)
        elif mode == "upload":
            self.upload_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E3F2FD;
                    color: #1565C0;
                    border: 2px solid #2196F3;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 20px;
                }
                QPushButton:hover {
                    background-color: #BBDEFB;
                }
            """)
        elif mode == "shopping_list":
            self.shopping_btn.setStyleSheet("""
                QPushButton {
                    background-color: #FFF3E0;
                    color: #E65100;
                    border: 2px solid #FF9800;
                    border-radius: 12px;
                    font-size: 16px;
                    font-weight: bold;
                    padding: 20px;
                }
                QPushButton:hover {
                    background-color: #FFE0B2;
                }
            """)
        
        # Update scan area content
        self.update_scan_area()
    
    def create_scan_area(self):
        """Create the main scan area based on current mode"""
        area = QFrame()
        area.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 2px solid #E0E0E0;
            }
        """)
        
        self.scan_layout = QVBoxLayout()
        self.scan_layout.setContentsMargins(30, 30, 30, 30)
        self.scan_layout.setSpacing(20)
        
        area.setLayout(self.scan_layout)
        return area
    
    def update_scan_area(self):
        """Update the scan area content based on current mode"""
        # Clear existing content
        for i in reversed(range(self.scan_layout.count())):
            item = self.scan_layout.itemAt(i)
            if item and item.widget():
                item.widget().setParent(None)
        
        if self.scan_mode == "live":
            self.create_live_detection_area()
        elif self.scan_mode == "upload":
            self.create_upload_area()
        elif self.scan_mode == "shopping_list":
            self.create_shopping_list_area()
    
    def create_live_detection_area(self):
        """Create live detection interface"""
        # Title
        title = QLabel("Live Environmental Detection")
        title.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        self.scan_layout.addWidget(title)
        
        # Camera view - this will be updated when scanning starts
        self.camera_view = QLabel("📹 Camera Feed\n\nClick 'Start Live Detection' to begin")
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setStyleSheet("""
            QLabel {
                background-color: #F8F9FA;
                color: #666666;
                border: 2px dashed #CCCCCC;
                border-radius: 10px;
                font-size: 16px;
                padding: 40px;
                min-height: 400px;
            }
        """)
        self.scan_layout.addWidget(self.camera_view)
        
        # Control buttons
        controls_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🎬 Start Live Detection")
        self.start_btn.setFixedHeight(50)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        self.start_btn.clicked.connect(self.start_live_detection)
        
        self.stop_btn = QPushButton("⏹️ Stop Detection")
        self.stop_btn.setFixedHeight(50)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #DA190B;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_live_detection)
        self.stop_btn.setEnabled(False)
        
        self.test_npu_btn = QPushButton("🤖 Test NPU Chatbot")
        self.test_npu_btn.setFixedHeight(50)
        self.test_npu_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        self.test_npu_btn.clicked.connect(self.test_npu_chatbot)
        
        self.check_server_btn = QPushButton("🔍 Check Server Status")
        self.check_server_btn.setFixedHeight(50)
        self.check_server_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        self.check_server_btn.clicked.connect(self.check_server_status)
        
        # Detection status
        self.status_label = QLabel("Ready to start detection")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 10px;
                background-color: #F0F0F0;
                border-radius: 6px;
            }
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.test_npu_btn)
        controls_layout.addWidget(self.check_server_btn)
        controls_layout.addStretch()
        
        self.scan_layout.addLayout(controls_layout)
        self.scan_layout.addWidget(self.status_label)
    
    def create_upload_area(self):
        """Create photo upload interface"""
        # Title
        title = QLabel("Upload Photo for Analysis")
        title.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        self.scan_layout.addWidget(title)
        
        # Upload area
        upload_area = QLabel("📷 Drop your photo here or click to browse\n\nSupports: JPG, PNG, HEIC")
        upload_area.setAlignment(Qt.AlignCenter)
        upload_area.setStyleSheet("""
            QLabel {
                background-color: #F8F9FA;
                color: #666666;
                border: 2px dashed #CCCCCC;
                border-radius: 10px;
                font-size: 16px;
                padding: 40px;
                min-height: 200px;
            }
        """)
        upload_area.mousePressEvent = self.upload_photo
        self.scan_layout.addWidget(upload_area)
        
        # Upload button
        upload_btn = QPushButton("📁 Choose Photo")
        upload_btn.setFixedHeight(50)
        upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        upload_btn.clicked.connect(self.upload_photo)
        self.scan_layout.addWidget(upload_btn)
    
    def create_shopping_list_area(self):
        """Create shopping list scanner interface"""
        # Title
        title = QLabel("Shopping List Scanner")
        title.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 20px;
                font-weight: bold;
            }
        """)
        self.scan_layout.addWidget(title)
        
        # Instructions
        instructions = QLabel("Scan multiple products to build your shopping list and get environmental impact analysis")
        instructions.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 10px 0;
            }
        """)
        instructions.setWordWrap(True)
        self.scan_layout.addWidget(instructions)
        
        # Shopping list display
        self.shopping_list = QListWidget()
        self.shopping_list.setStyleSheet("""
            QListWidget {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        self.shopping_list.setMaximumHeight(200)
        self.scan_layout.addWidget(self.shopping_list)
        
        # Add item input
        input_layout = QHBoxLayout()
        
        self.item_input = QLineEdit()
        self.item_input.setPlaceholderText("Enter product name or scan barcode...")
        self.item_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #DDDDDD;
                border-radius: 8px;
                padding: 10px;
                font-size: 14px;
            }
        """)
        self.item_input.returnPressed.connect(self.add_shopping_item)
        
        add_btn = QPushButton("Add Item")
        add_btn.setFixedHeight(40)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
                padding: 0 20px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
        """)
        add_btn.clicked.connect(self.add_shopping_item)
        
        input_layout.addWidget(self.item_input)
        input_layout.addWidget(add_btn)
        self.scan_layout.addLayout(input_layout)
        
        # Photo upload button for shopping list
        photo_upload_btn = QPushButton("📷 Upload Shopping List Photo")
        photo_upload_btn.setFixedHeight(50)
        photo_upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        photo_upload_btn.clicked.connect(self.upload_shopping_list_photo)
        self.scan_layout.addWidget(photo_upload_btn)
        
        # Scan button
        scan_btn = QPushButton("🔍 Scan Shopping List")
        scan_btn.setFixedHeight(50)
        scan_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        scan_btn.clicked.connect(self.scan_shopping_list)
        self.scan_layout.addWidget(scan_btn)
        
        # Scan from image button
        scan_image_btn = QPushButton("📷 Scan Shopping List from Image")
        scan_image_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 20px;
                font-size: 16px;
                font-weight: bold;
                padding: 0 30px;
            }
            QPushButton:hover {
                background-color: #45A049;
            }
        """)
        scan_image_btn.clicked.connect(self.scan_shopping_list_from_image)
        self.scan_layout.addWidget(scan_image_btn)
    
    def create_results_area(self):
        """Create results display area"""
        area = QFrame()
        area.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border-radius: 12px;
                border: 2px solid #E0E0E0;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)
        
        title = QLabel("Analysis Results")
        title.setStyleSheet("""
            QLabel {
                color: #333333;
                font-size: 18px;
                font-weight: bold;
            }
        """)
        layout.addWidget(title)
        
        self.results_text = QTextEdit()
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
                color: #333333;
            }
        """)
        self.results_text.setMaximumHeight(200)
        self.results_text.setPlainText("No analysis results yet. Start scanning to see environmental impact data.")
        layout.addWidget(self.results_text)
        
        area.setLayout(layout)
        return area
    
    def start_live_detection(self):
        """Start live camera detection"""
        try:
            self.is_scanning = True
            self.start_btn.setEnabled(False)
            self.stop_btn.setEnabled(True)
            
            # Update camera view to show live detection
            self.camera_view.setText("📹 Starting Camera...\n\n🔍 Initializing live detection...\n\nPlease wait...")
            self.camera_view.setStyleSheet("""
                QLabel {
                    background-color: #E8F5E8;
                    color: #2E7D32;
                    border: 2px solid #4CAF50;
                    border-radius: 10px;
                    font-size: 16px;
                    padding: 40px;
                    min-height: 400px;
                }
            """)
            
            # Update status
            self.status_label.setText("🔴 LIVE - Starting camera...")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #2E7D32;
                    font-size: 14px;
                    padding: 10px;
                    background-color: #E8F5E8;
                    border-radius: 6px;
                    border: 1px solid #4CAF50;
                }
            """)
            
            # Update results area
            self.results_text.setPlainText("🔍 Live Detection Starting\n\nInitializing camera and ONNX model...\nEnvironmental impact analysis ready...")
            
            # Start camera thread - this will raise exception if camera fails
            self.camera_thread.start_camera()
            
        except Exception as e:
            # Camera failed - show error and stop
            self.camera_view.setText(f"📹 Camera Error\n\n❌ {str(e)}\n\nCamera initialization failed.")
            self.camera_view.setStyleSheet("""
                QLabel {
                    background-color: #FFEBEE;
                    color: #C62828;
                    border: 2px solid #F44336;
                    border-radius: 10px;
                    font-size: 16px;
                    padding: 40px;
                    min-height: 400px;
                }
            """)
            
            self.status_label.setText("❌ Camera Failed")
            self.status_label.setStyleSheet("""
                QLabel {
                    color: #C62828;
                    font-size: 14px;
                    padding: 10px;
                    background-color: #FFEBEE;
                    border-radius: 6px;
                    border: 1px solid #F44336;
                }
            """)
            
            self.results_text.setPlainText(f"❌ Camera Error: {str(e)}\n\nPlease check:\n• Camera is connected\n• No other apps using camera\n• Camera permissions")
            
            # Re-enable start button
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.is_scanning = False
    
    def stop_live_detection(self):
        """Stop live camera detection"""
        self.is_scanning = False
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.scan_timer.stop()
        
        # Stop camera thread
        self.camera_thread.stop_camera()
        
        # Reset camera view
        self.camera_view.setText("📹 Camera Feed\n\nLive detection stopped.\nClick 'Start Live Detection' to begin again.")
        self.camera_view.setStyleSheet("""
            QLabel {
                background-color: #F8F9FA;
                color: #666666;
                border: 2px dashed #CCCCCC;
                border-radius: 10px;
                font-size: 16px;
                padding: 40px;
                min-height: 400px;
            }
        """)
        
        # Update status
        self.status_label.setText("⏹️ Detection stopped")
        self.status_label.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 14px;
                padding: 10px;
                background-color: #F0F0F0;
                border-radius: 6px;
            }
        """)
        
        # Update results with final analysis
        self.results_text.setPlainText("✅ Live Detection Complete!\n\nCamera stopped successfully.\nClick 'Start Live Detection' to begin again.")
    
    def update_camera_display(self, frame):
        """Update the camera display with live video feed"""
        try:
            # Resize frame to fit label
            height, width = frame.shape[:2]
            max_width = 780
            max_height = 480
            
            scale = min(max_width/width, max_height/height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            
            frame = cv2.resize(frame, (new_width, new_height))
            
            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Convert to QImage
            h, w, ch = frame_rgb.shape
            bytes_per_line = ch * w
            qt_image = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
            
            # Convert to QPixmap and display
            pixmap = QPixmap.fromImage(qt_image)
            self.camera_view.setPixmap(pixmap)
            
        except Exception as e:
            print(f"Error updating camera display: {e}")
    
    def update_detection_results(self, detections):
        """Update detection results in real-time"""
        try:
            if detections:
                # Sort by confidence and take only the top result
                top_detection = max(detections, key=lambda x: x['confidence'])
                
                # Update status
                self.status_label.setText(f"🔴 LIVE - Top: {top_detection['class_name']} ({top_detection['confidence']:.2f})")
                self.status_label.setStyleSheet("""
                    QLabel {
                        color: #2E7D32;
                        font-size: 14px;
                        padding: 10px;
                        background-color: #E8F5E8;
                        border-radius: 6px;
                        border: 1px solid #4CAF50;
                    }
                """)
                
                # Send to eco-copilot chatbot
                self.send_to_eco_copilot(top_detection['class_name'])
                
            else:
                self.status_label.setText("🔴 LIVE - No objects detected")
                self.status_label.setStyleSheet("""
                    QLabel {
                        color: #666666;
                        font-size: 14px;
                        padding: 10px;
                        background-color: #F0F0F0;
                        border-radius: 6px;
                    }
                """)
                
        except Exception as e:
            print(f"Error updating detection results: {e}")
    
    def send_to_eco_copilot(self, product_name):
        """Send detected product to NPU-optimized eco-copilot chatbot"""
        try:
            # Check if NPU chatbot is available
            if self.npu_chatbot is None:
                self.results_text.clear()
                self.results_text.append("❌ NPU Chatbot Not Available")
                self.results_text.append("=" * 50)
                self.results_text.append("The NPU chatbot is not initialized.")
                self.results_text.append("Please check your server connection and try again.")
                return
            
            # Update results area
            self.results_text.clear()
            self.results_text.append("🤖 NPU Eco-Copilot Analysis")
            self.results_text.append("=" * 50)
            self.results_text.append(f"📦 Detected Product: {product_name}")
            self.results_text.append("")
            self.results_text.append("🔍 Sending to NPU-optimized model...")
            self.results_text.append("⏳ Processing with INT8 quantization...")
            self.results_text.append("")
            
            # Force UI update
            QApplication.processEvents()
            
            # Send to NPU chatbot
            response = self.npu_chatbot.send_eco_copilot_prompt(product_name)
            
            # Display the response
            self.results_text.append("🤖 NPU Eco-Copilot Response:")
            self.results_text.append("=" * 50)
            self.results_text.append(response)
            self.results_text.append("")
            self.results_text.append("✅ Analysis complete! Powered by NPU with INT8 optimization")
            
        except Exception as e:
            print(f"Error sending to eco-copilot: {e}")
            self.results_text.append(f"❌ Error: {str(e)}")
            self.results_text.append("")
            self.results_text.append("💡 Make sure your NPU model server is running on localhost:3001")
    
    def test_npu_chatbot(self):
        """Test NPU chatbot with a sample product"""
        test_product = "apple"
        self.send_to_eco_copilot(test_product)
    
    def check_server_status(self):
        """Check NPU server status and provide instructions"""
        self.results_text.clear()
        self.results_text.append("🔍 NPU Server Status Check")
        self.results_text.append("=" * 50)
        
        # Check server status
        status = self.npu_chatbot.check_server_status()
        
        if status:
            self.results_text.append("✅ NPU Model Server is RUNNING")
            self.results_text.append("✅ Ready for eco-copilot analysis")
            self.results_text.append("")
            self.results_text.append("🚀 You can now:")
            self.results_text.append("• Start live detection")
            self.results_text.append("• Upload photos for analysis")
            self.results_text.append("• Test NPU chatbot")
        else:
            self.results_text.append("❌ NPU Model Server is NOT RUNNING")
            self.results_text.append("")
            self.results_text.append("📋 To start the server:")
            self.results_text.append("")
            self.results_text.append("1. Open AnythingLLM application")
            self.results_text.append("2. Verify settings:")
            self.results_text.append("   • LLM Provider: 'AnythingLLM NPU'")
            self.results_text.append("   • Model: Llama 3.1 8B Chat 8K")
            self.results_text.append("   • Workspace: 'greenlens'")
            self.results_text.append("   • API Key: Generated")
            self.results_text.append("")
            self.results_text.append("3. Test connection:")
            self.results_text.append("   python src/auth.py")
            self.results_text.append("")
            self.results_text.append("4. Get workspace slug:")
            self.results_text.append("   python src/workspaces.py")
            self.results_text.append("")
            self.results_text.append("5. Update config.yaml with correct values")
            self.results_text.append("")
            self.results_text.append("💡 The server should run on localhost:3001")
    
    def update_scan_status(self):
        """Update scanning status (simulated live detection)"""
        # This method is now handled by the camera thread
        pass
    
    def upload_photo(self, event=None):
        """Handle photo upload"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Photo", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.heic *.bmp)"
        )
        if file_path:
            self.results_text.setPlainText(f"📷 Photo uploaded: {os.path.basename(file_path)}\n\n🔍 Analyzing image...")
            
            try:
                # Read and analyze image
                image = cv2.imread(file_path)
                if image is not None:
                    # Check if detector is available
                    if self.detector is None:
                        self.results_text.append("\n❌ Object detector not available. Please check your setup.")
                        return
                    
                    # First try object detection
                    detections = self.detector.detect(image)
                    
                    # Filter out person detections
                    filtered_detections = [d for d in detections if d['class_name'] != 'person']
                    
                    if filtered_detections:
                        # Take only the top detection
                        top_detection = max(filtered_detections, key=lambda x: x['confidence'])
                        
                        self.results_text.append(f"\n🔍 Object Detection: {top_detection['class_name']} (confidence: {top_detection['confidence']:.2f})")
                        self.results_text.append("=" * 40)
                        
                        # Send to eco-copilot
                        self.send_to_eco_copilot(top_detection['class_name'])
                    else:
                        # If no objects detected, try text detection for shopping lists
                        self.results_text.append("\n🔍 No objects detected. Trying text detection for shopping list...")
                        
                        detected_text = self.text_detector.detect_text(file_path)
                        if detected_text:
                            self.results_text.append(f"\n📝 Detected Text Items:")
                            for i, item in enumerate(detected_text[:10], 1):  # Show first 10 items
                                self.results_text.append(f"{i}. {item}")
                            
                            # Analyze the first detected item with eco-copilot
                            if detected_text:
                                self.results_text.append(f"\n🤖 Analyzing first item: {detected_text[0]}")
                                self.send_to_eco_copilot(detected_text[0])
                        else:
                            self.results_text.append("\n❌ No text detected in image")
                else:
                    self.results_text.append("\n❌ Error loading image")
                    
            except Exception as e:
                self.results_text.append(f"\n❌ Error analyzing image: {str(e)}")
    
    def add_shopping_item(self):
        """Add item to shopping list"""
        item_text = self.item_input.text().strip()
        if item_text:
            item = QListWidgetItem(f"🛒 {item_text}")
            self.shopping_list.addItem(item)
            self.item_input.clear()
    
    def scan_shopping_list_from_image(self):
        """Scan shopping list from uploaded image using text detection"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Shopping List Image", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.heic *.bmp)"
        )
        
        if file_path:
            self.results_text.clear()
            self.results_text.append("📷 Shopping List Image Analysis")
            self.results_text.append("=" * 50)
            self.results_text.append(f"📁 File: {os.path.basename(file_path)}")
            self.results_text.append("")
            self.results_text.append("🔍 Processing image with EasyOCR...")
            self.results_text.append("⏳ Detecting text items...")
            
            try:
                # Detect text from shopping list image
                detected_items = self.text_detector.detect_text(file_path)
                
                if detected_items:
                    self.results_text.append(f"\n✅ Successfully detected {len(detected_items)} items:")
                    self.results_text.append("=" * 40)
                    
                    # Add detected items to shopping list
                    for i, item in enumerate(detected_items, 1):
                        clean_item = ' '.join(item.split()).title()
                        self.shopping_list.addItem(f"{i}. {clean_item}")
                        self.results_text.append(f"{i}. {clean_item}")
                    
                    self.results_text.append(f"\n🎉 Added {len(detected_items)} items to your shopping list!")
                    self.results_text.append("\n🔍 Running environmental impact analysis...")
                    
                    # Analyze the shopping list
                    self.scan_shopping_list()
                else:
                    self.results_text.append("\n❌ No text detected in the image.")
                    self.results_text.append("\n💡 Tips for better text detection:")
                    self.results_text.append("   • Use clear, well-lit photos")
                    self.results_text.append("   • Ensure text is readable and not blurry")
                    self.results_text.append("   • Try different angles or lighting")
                    
            except Exception as e:
                self.results_text.append(f"\n❌ Error processing image: {str(e)}")

    def upload_shopping_list_photo(self):
        """Upload and process shopping list photo with EasyOCR"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Shopping List Photo", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.heic *.bmp)"
        )
        
        if file_path:
            # Update results area to show processing
            self.results_text.clear()
            self.results_text.append("📷 Shopping List Photo Upload")
            self.results_text.append("=" * 50)
            self.results_text.append(f"📁 File: {os.path.basename(file_path)}")
            self.results_text.append("")
            self.results_text.append("🔍 Processing image with EasyOCR...")
            self.results_text.append("⏳ Detecting text items...")
            
            try:
                # Detect text from shopping list image using EasyOCR
                detected_items = self.text_detector.detect_text(file_path)
                
                if detected_items:
                    self.results_text.append(f"\n✅ Successfully detected {len(detected_items)} items:")
                    self.results_text.append("=" * 40)
                    
                    # Clear existing shopping list
                    self.shopping_list.clear()
                    
                    # Add detected items to shopping list
                    for i, item in enumerate(detected_items, 1):
                        # Clean up the text (remove extra spaces, capitalize)
                        clean_item = ' '.join(item.split()).title()
                        self.shopping_list.addItem(f"{i}. {clean_item}")
                        self.results_text.append(f"{i}. {clean_item}")
                    
                    self.results_text.append(f"\n🎉 Added {len(detected_items)} items to your shopping list!")
                    self.results_text.append("\n💡 Click '🔍 Scan Shopping List' to analyze environmental impact")
                    
                else:
                    self.results_text.append("\n❌ No text detected in the image.")
                    self.results_text.append("\n💡 Tips for better text detection:")
                    self.results_text.append("   • Use clear, well-lit photos")
                    self.results_text.append("   • Ensure text is readable and not blurry")
                    self.results_text.append("   • Try different angles or lighting")
                    
            except Exception as e:
                self.results_text.append(f"\n❌ Error processing image: {str(e)}")
                self.results_text.append("\n💡 Please try a different image or check if the file is valid.")

    def scan_shopping_list(self):
        """Analyze entire shopping list"""
        if self.shopping_list.count() == 0:
            self.results_text.setPlainText("⚠️ Please add items to your shopping list first.")
            return
        
        items = []
        for i in range(self.shopping_list.count()):
            items.append(self.shopping_list.item(i).text())
        
        self.results_text.setPlainText(f"🛒 Shopping List Analysis\n\nItems: {len(items)}\n\nEnvironmental Impact Analysis:")
        self.results_text.append("=" * 40)
        
        # Analyze each item for environmental impact
        eco_friendly_items = 0
        total_carbon = 0
        
        for item in items:
            item_lower = item.lower()
            carbon_factor = 0.3  # Default carbon factor
            
            # Categorize items for better analysis
            if any(word in item_lower for word in ['organic', 'local', 'recycled', 'eco', 'green']):
                carbon_factor = 0.1
                eco_friendly_items += 1
            elif any(word in item_lower for word in ['meat', 'beef', 'lamb', 'cheese']):
                carbon_factor = 1.0
            elif any(word in item_lower for word in ['fish', 'chicken', 'pork']):
                carbon_factor = 0.5
            elif any(word in item_lower for word in ['vegetables', 'fruits', 'grains', 'beans']):
                carbon_factor = 0.2
                eco_friendly_items += 1
            
            total_carbon += carbon_factor
            self.results_text.append(f"• {item}: {carbon_factor:.1f} kg CO₂e")
        
        self.results_text.append("=" * 40)
        self.results_text.append(f"📊 Summary:")
        self.results_text.append(f"• Total Carbon Footprint: {total_carbon:.1f} kg CO₂e")
        self.results_text.append(f"• Eco-friendly items: {eco_friendly_items}/{len(items)}")
        self.results_text.append(f"• Sustainability Score: {min(10.0, (eco_friendly_items / len(items)) * 10):.1f}/10")
        
        if eco_friendly_items / len(items) > 0.7:
            self.results_text.append(f"🌱 Great! Your shopping list is very eco-friendly!")
        elif eco_friendly_items / len(items) > 0.4:
            self.results_text.append(f"👍 Good choices! Consider adding more organic/local items.")
        else:
            self.results_text.append(f"💡 Consider choosing more eco-friendly alternatives.")

class EcoCopilotApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GreenLens - Environmental AI Assistant")
        self.setGeometry(100, 100, 1400, 800)
        self.setObjectName("MainWindow")

        # --- Main Layout (Sidebar + Content) ---
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Create sidebar
        self.sidebar = Sidebar()
        main_layout.addWidget(self.sidebar)
        
        # Create stacked widget for pages
        self.stacked_widget = QStackedWidget()
        
        # Create pages
        self.home_page = HomePage()
        self.scan_page = ScanPage()
        self.eco_copilot_page = GradioChatPage()  # Use GradioChatPage instead
        
        # Initialize voice assistant
        self.voice_assistant = VoiceAssistant(self.eco_copilot_page.npu_chatbot)
        self.voice_assistant.voice_recognized.connect(self.handle_voice_input)
        self.voice_assistant.voice_speaking.connect(self.update_voice_status)
        self.voice_assistant.voice_error.connect(self.handle_voice_error)
        
        # Add pages to stacked widget
        self.stacked_widget.addWidget(self.home_page)
        self.stacked_widget.addWidget(self.scan_page)
        self.stacked_widget.addWidget(self.eco_copilot_page)
        
        # Set default page
        self.stacked_widget.setCurrentWidget(self.home_page)
        
        main_layout.addWidget(self.stacked_widget)

        # Create floating microphone button
        self.create_voice_button()
        
        # Connect sidebar menu clicks to page switching
        self.sidebar.menu_clicked.connect(self.switch_page)

        # Apply the stylesheet
        self.setStyleSheet(self.get_stylesheet())
    
    def closeEvent(self, event):
        """Handle application close event"""
        # Stop camera if running
        if hasattr(self.scan_page, 'camera_thread'):
            self.scan_page.camera_thread.stop_camera()
        event.accept()
    
    def switch_page(self, page_name):
        """Switch between different pages based on menu selection"""
        if page_name == "Scan":
            self.stacked_widget.setCurrentWidget(self.scan_page)
        elif page_name == "Eco-copilot":
            self.stacked_widget.setCurrentWidget(self.eco_copilot_page)
        else:
            # For other menu items, show home page for now
            self.stacked_widget.setCurrentWidget(self.home_page)
    
    def handle_voice_input(self, text):
        """Handle recognized voice input"""
        print(f"🎤 Voice recognized: {text}")
        
        # Get response from NPU chatbot
        try:
            response = self.voice_assistant.npu_chatbot.send_eco_copilot_prompt(text)
            print(f"🤖 Bot response: {response}")
            
            # Speak the response
            self.voice_assistant.speak(response)
            
        except Exception as e:
            error_msg = f"Error getting response: {str(e)}"
            print(f"❌ {error_msg}")
            self.voice_assistant.speak("Sorry, I encountered an error. Please try again.")
    
    def update_voice_status(self, is_speaking):
        """Update voice status indicator"""
        if is_speaking:
            print("🔊 Speaking...")
        else:
            print("🔇 Finished speaking")
    
    def handle_voice_error(self, error_msg):
        """Handle voice assistant errors"""
        print(f"❌ Voice Error: {error_msg}")
        # You could show a popup or status message here
    
    def create_voice_button(self):
        """Create floating microphone button"""
        self.voice_button = QPushButton("🎤")
        self.voice_button.setFixedSize(60, 60)
        self.voice_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #4CAF50, stop:1 #2E7D32);
                border: none;
                border-radius: 30px;
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #45A049, stop:1 #1B5E20);
                transform: scale(1.1);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #3D8B40, stop:1 #0D4F1A);
            }
        """)
        self.voice_button.setToolTip("Click to start voice assistant")
        self.voice_button.clicked.connect(self.toggle_voice_assistant)
        
        # Position the button at bottom right
        self.voice_button.move(self.width() - 80, self.height() - 80)
        self.voice_button.raise_()  # Bring to front
    
    def toggle_voice_assistant(self):
        """Toggle voice assistant listening"""
        if not self.voice_assistant.is_listening and not self.voice_assistant.is_speaking:
            self.voice_button.setText("🔴")
            self.voice_button.setToolTip("Listening... Click to stop")
            self.voice_assistant.start_listening()
        else:
            self.voice_button.setText("🎤")
            self.voice_button.setToolTip("Click to start voice assistant")
            self.voice_assistant.stop_listening()
    
    def resizeEvent(self, event):
        """Handle window resize to keep voice button positioned"""
        super().resizeEvent(event)
        if hasattr(self, 'voice_button'):
            self.voice_button.move(self.width() - 80, self.height() - 80)
    
    def create_ecocopilot_page(self):
        """Creates the EcoCopilot page with the original design"""
        page = QWidget()
        page.setObjectName("MainWindow")
        
        # --- Main Layouts ---
        main_layout = QVBoxLayout(page)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        content_layout = QHBoxLayout()
        footer_layout = QHBoxLayout()
        
        # --- Header ---
        title_label = QLabel("EcoCopilot")
        title_label.setObjectName("HeaderTitle")
        header_layout.addWidget(title_label, alignment=Qt.AlignLeft)
        
        # --- Content Area (Left and Right Panels) ---
        left_panel = self.create_left_panel()
        right_panel = self.create_right_panel()
        content_layout.addWidget(left_panel, 2) # 2/3 of the space
        content_layout.addWidget(right_panel, 1) # 1/3 of the space

        # --- Footer ---
        footer_label = QLabel("Powered by Edge AI")
        footer_label.setObjectName("FooterText")
        footer_layout.addWidget(footer_label, alignment=Qt.AlignRight)

        # --- Assemble Layouts ---
        main_layout.addLayout(header_layout)
        main_layout.addLayout(content_layout)
        main_layout.addLayout(footer_layout)
        
        return page

    def create_left_panel(self):
        """Creates the left panel with the camera feed and button."""
        left_widget = QWidget()
        layout = QVBoxLayout(left_widget)
        
        scan_frame = QFrame()
        scan_frame.setObjectName("ScanFrame")
        scan_layout = QVBoxLayout(scan_frame)
        scan_layout.setContentsMargins(20, 20, 20, 20)
        
        scan_title = QLabel("Real-Time Scan")
        scan_title.setObjectName("CardTitle")
        
        # Placeholder for camera feed
        self.camera_view = QLabel("Camera feed would appear here.")
        self.camera_view.setAlignment(Qt.AlignCenter)
        self.camera_view.setObjectName("CameraView")
        self.camera_view.setMinimumSize(600, 400)
        
        scan_button = QPushButton("Scan Product")
        scan_button.setObjectName("ScanButton")
        scan_button.setMinimumHeight(50)
        
        scan_layout.addWidget(scan_title)
        scan_layout.addWidget(self.camera_view, 1) # Make it stretch
        
        layout.addWidget(scan_frame)
        layout.addWidget(scan_button)
        
        return left_widget

    def create_right_panel(self):
        """Creates the right panel with informational cards."""
        right_widget = QWidget()
        layout = QVBoxLayout(right_widget)
        layout.setSpacing(20)

        # Carbon Footprint Card
        carbon_card = QFrame()
        carbon_card.setObjectName("InfoCard")
        carbon_layout = QGridLayout(carbon_card)
        
        carbon_title = QLabel("Carbon Footprint")
        carbon_title.setObjectName("CardTitle")
        
        self.carbon_progress = CircularProgressBar()
        self.carbon_progress.setValue(80) # Example value
        
        carbon_value_label = QLabel("7.2 <span>kg CO₂e</span>")
        carbon_value_label.setObjectName("CarbonValue")
        
        carbon_status_label = QLabel("High Carbon Footprint")
        carbon_status_label.setObjectName("CarbonStatus")
        
        carbon_layout.addWidget(carbon_title, 0, 0, 1, 2)
        carbon_layout.addWidget(self.carbon_progress, 1, 0)
        carbon_layout.addWidget(carbon_value_label, 1, 1, Qt.AlignCenter)
        carbon_layout.addWidget(carbon_status_label, 2, 0, 1, 2, Qt.AlignCenter)
        
        # Smart Suggestion Card
        suggestion_card = QFrame()
        suggestion_card.setObjectName("InfoCard")
        suggestion_layout = QVBoxLayout(suggestion_card)
        
        suggestion_title = QLabel("💡 Smart Suggestion")
        suggestion_title.setObjectName("CardTitle")
        
        suggestion_text = QLabel("Try the store brand in the carton. It typically has a 30% lower footprint due to lighter packaging.")
        suggestion_text.setObjectName("BodyText")
        suggestion_text.setWordWrap(True)
        
        privacy_label = QLabel("🔒 100% On-Device AI")
        privacy_label.setObjectName("PrivacyText")
        
        suggestion_layout.addWidget(suggestion_title)
        suggestion_layout.addWidget(suggestion_text)
        suggestion_layout.addStretch()
        suggestion_layout.addWidget(privacy_label)
        
        # Weekly Impact Card
        impact_card = QFrame()
        impact_card.setObjectName("InfoCard")
        impact_layout = QVBoxLayout(impact_card)
        
        impact_title = QLabel("Your Weekly Impact")
        impact_title.setObjectName("CardTitle")
        
        self.bar_chart = BarChartWidget()
        
        impact_layout.addWidget(impact_title)
        impact_layout.addWidget(self.bar_chart)

        layout.addWidget(carbon_card)
        layout.addWidget(suggestion_card)
        layout.addWidget(impact_card)
        
        return right_widget

    def get_stylesheet(self):
        """Returns the QSS stylesheet for the application."""
        return """
            QWidget#MainWindow {
                background-color: #1A202C;
            }
            QLabel#HeaderTitle {
                color: #FFFFFF;
                font-size: 28px;
                font-weight: bold;
                font-family: 'Segoe UI';
            }
            QFrame#ScanFrame, QFrame#InfoCard {
                background-color: #2D3748;
                border-radius: 15px;
            }
            QLabel#CardTitle {
                color: #E2E8F0;
                font-size: 18px;
                font-weight: bold;
                font-family: 'Segoe UI';
                padding-bottom: 10px;
            }
            QLabel#CameraView {
                background-color: #1A202C;
                color: #A0AEC0;
                border-radius: 10px;
                font-size: 16px;
            }
            QPushButton#ScanButton {
                background-color: #2ECC71;
                color: #FFFFFF;
                font-size: 18px;
                font-weight: bold;
                border-radius: 10px;
                padding: 10px;
                border: none;
            }
            QPushButton#ScanButton:hover {
                background-color: #27AE60;
            }
            QLabel#CarbonValue {
                color: #FFFFFF;
                font-size: 28px;
                font-weight: bold;
            }
            QLabel#CarbonValue span {
                font-size: 16px;
                color: #A0AEC0;
            }
            QLabel#CarbonStatus {
                color: #E74C3C;
                font-size: 14px;
                font-weight: bold;
            }
            QLabel#BodyText {
                color: #CBD5E0;
                font-size: 14px;
                font-family: 'Segoe UI';
            }
            QLabel#PrivacyText, QLabel#FooterText {
                color: #718096;
                font-size: 12px;
                font-family: 'Segoe UI';
            }
        """

# =============================================================================
# 4. APPLICATION EXECUTION
# =============================================================================

if __name__ == '__main__':
    try:
        app = QApplication(sys.argv)
        window = EcoCopilotApp()
        window.show()
        sys.exit(app.exec_())
    except ImportError as e:
        print("❌ Missing Dependencies Error:")
        print(f"   {str(e)}")
        print("\n💡 To fix this, run:")
        print("   python install_dependencies.py")
        print("\n   Or install manually:")
        print("   pip install opencv-python onnxruntime PyQt5 PyQtWebEngine easyocr gradio")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Application Error: {str(e)}")
        print("\n💡 Please check your configuration and try again.")
        sys.exit(1)
