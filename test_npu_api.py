#!/usr/bin/env python3
"""
Test script to debug NPU API calls
"""
import requests
import yaml

def test_npu_api():
    """Test the NPU API directly"""
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    api_key = config["api_key"]
    base_url = config["model_server_base_url"]
    workspace_slug = config["workspace_slug"]
    
    # Construct URL (use non-streaming for testing)
    chat_url = f"{base_url}/workspace/{workspace_slug}/chat"
    
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key
    }
    
    data = {
        "message": "Hello, test message",
        "mode": "chat",
        "sessionId": "test-session",
        "attachments": []
    }
    
    print("🔍 Testing NPU API...")
    print(f"🔍 Chat URL: {chat_url}")
    print(f"🔍 Request Data: {data}")
    print(f"🔍 Headers: {headers}")
    
    try:
        response = requests.post(
            chat_url,
            headers=headers,
            json=data,
            timeout=30
        )
        
        print(f"🔍 Response Status: {response.status_code}")
        print(f"🔍 Response Headers: {response.headers}")
        print(f"🔍 Response Text: {response.text}")
        
        if response.status_code == 200:
            response_data = response.json()
            print(f"🔍 Response JSON: {response_data}")
            
            if 'textResponse' in response_data:
                print(f"✅ Success! Response: {response_data['textResponse']}")
            elif 'error' in response_data and response_data['error']:
                print(f"❌ NPU Model Error: {response_data['error']}")
            else:
                print(f"❌ Unexpected response format: {response_data}")
        else:
            print(f"❌ HTTP Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection Error: {str(e)}")
    except Exception as e:
        print(f"❌ Unexpected Error: {str(e)}")

if __name__ == "__main__":
    test_npu_api()
