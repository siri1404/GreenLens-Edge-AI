#!/usr/bin/env python3
"""
Debug script to test individual components
"""
import sys
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

def test_imports():
    """Test all required imports"""
    print("🔍 Testing imports...")
    
    try:
        import cv2
        print("✅ OpenCV imported successfully")
    except ImportError as e:
        print(f"❌ OpenCV import failed: {e}")
        return False
    
    try:
        import numpy as np
        print("✅ NumPy imported successfully")
    except ImportError as e:
        print(f"❌ NumPy import failed: {e}")
        return False
    
    try:
        import onnxruntime as ort
        print("✅ ONNX Runtime imported successfully")
    except ImportError as e:
        print(f"❌ ONNX Runtime import failed: {e}")
        return False
    
    try:
        from PyQt5.QtWidgets import QApplication
        print("✅ PyQt5 imported successfully")
    except ImportError as e:
        print(f"❌ PyQt5 import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests imported successfully")
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False
    
    try:
        import yaml
        print("✅ YAML imported successfully")
    except ImportError as e:
        print(f"❌ YAML import failed: {e}")
        return False
    
    return True

def test_config():
    """Test configuration file"""
    print("\n🔍 Testing configuration...")
    
    try:
        import yaml
        with open("config.yaml", "r") as f:
            config = yaml.safe_load(f)
        
        print("✅ Config file loaded successfully")
        print(f"   API Key: {config.get('api_key', 'NOT SET')[:10]}...")
        print(f"   Base URL: {config.get('model_server_base_url', 'NOT SET')}")
        print(f"   Workspace: {config.get('workspace_slug', 'NOT SET')}")
        
        return config
    except Exception as e:
        print(f"❌ Config error: {e}")
        return None

def test_server_connection(config):
    """Test server connection"""
    print("\n🔍 Testing server connection...")
    
    if not config:
        print("❌ No config available")
        return False
    
    try:
        import requests
        
        # Test basic connection
        base_url = config["model_server_base_url"]
        test_url = base_url.replace("/api/v1", "")
        
        print(f"   Testing: {test_url}")
        response = requests.get(test_url, timeout=5)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Server is reachable")
        else:
            print(f"⚠️ Server returned status {response.status_code}")
        
        # Test API endpoint
        api_url = f"{base_url}/workspace/{config['workspace_slug']}"
        print(f"   Testing API: {api_url}")
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config["api_key"]
        }
        
        response = requests.get(api_url, headers=headers, timeout=5)
        print(f"   API Status: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ API endpoint is working")
            return True
        else:
            print(f"❌ API endpoint failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server - is AnythingLLM running?")
        return False
    except Exception as e:
        print(f"❌ Server test error: {e}")
        return False

def test_chat_request(config):
    """Test a simple chat request"""
    print("\n🔍 Testing chat request...")
    
    if not config:
        print("❌ No config available")
        return False
    
    try:
        import requests
        
        chat_url = f"{config['model_server_base_url']}/workspace/{config['workspace_slug']}/chat"
        
        data = {
            "message": "Hello, test message",
            "mode": "chat",
            "sessionId": "test-session",
            "attachments": []
        }
        
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": "Bearer " + config["api_key"]
        }
        
        print(f"   Sending to: {chat_url}")
        response = requests.post(chat_url, headers=headers, json=data, timeout=15)
        
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.text[:300]}...")
        
        if response.status_code == 200:
            response_data = response.json()
            if 'textResponse' in response_data:
                print("✅ Chat request successful!")
                print(f"   Response: {response_data['textResponse'][:100]}...")
                return True
            else:
                print("❌ No textResponse in response")
                return False
        else:
            print(f"❌ Chat request failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Chat test error: {e}")
        return False

def main():
    """Main debug function"""
    print("🔧 EcoCopilot App Debug Tool")
    print("=" * 50)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import test failed - install dependencies first:")
        print("   python install_dependencies.py")
        return
    
    # Test config
    config = test_config()
    if not config:
        print("\n❌ Config test failed - check config.yaml")
        return
    
    # Test server
    if not test_server_connection(config):
        print("\n❌ Server test failed - check AnythingLLM")
        return
    
    # Test chat
    if test_chat_request(config):
        print("\n🎉 All tests passed! The app should work.")
    else:
        print("\n❌ Chat test failed - check NPU model setup")

if __name__ == "__main__":
    main()

