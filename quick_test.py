#!/usr/bin/env python3
"""
Quick test with a very short message
"""
import requests
import yaml

def quick_test():
    """Test with a very short message"""
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    api_key = config["api_key"]
    base_url = config["model_server_base_url"]
    workspace_slug = config["workspace_slug"]
    
    # Construct URL
    chat_url = f"{base_url}/workspace/{workspace_slug}/chat"
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key
    }
    
    # Very short test message
    data = {
        "message": "Hello",
        "mode": "chat",
        "sessionId": "test-session",
        "attachments": []
    }
    
    print("🔍 Quick Test - Very Short Message...")
    print(f"🔍 Chat URL: {chat_url}")
    print(f"🔍 Message: {data['message']}")
    
    try:
        response = requests.post(
            chat_url,
            headers=headers,
            json=data,
            timeout=10  # Short timeout
        )
        
        print(f"🔍 Response Status: {response.status_code}")
        print(f"🔍 Response Text: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"✅ Success! Response: {response_data.get('textResponse', 'No textResponse field')}")
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            
    except requests.exceptions.Timeout:
        print("❌ Request timed out - server is too slow")
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")

if __name__ == "__main__":
    quick_test()

