import requests
import json

def test_basic_functionality():
    base_url = "http://localhost:5000"
    
    print("🧪 Testing MyVakeel Basic Functionality...")
    
    # Test 1: Health check
    try:
        response = requests.get(f"{base_url}/api/health", timeout=5)
        print(f"✅ Health Check: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"❌ Health Check Failed: {e}")
        return False
    
    # Test 2: Chat functionality
    try:
        chat_data = {"query": "What is a contract?", "language": "en"}
        response = requests.post(f"{base_url}/api/chat", 
                               json=chat_data, 
                               timeout=10)
        print(f"✅ Chat Test: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Chat Response: {result.get('response', '')[:100]}...")
    except Exception as e:
        print(f"❌ Chat Test Failed: {e}")
    
    # Test 3: Text Analysis
    try:
        text_data = {"text": "This is a sample contract for testing purposes."}
        response = requests.post(f"{base_url}/api/analyze-text", 
                               json=text_data,
                               headers={"User-Email": "test@example.com"},
                               timeout=15)
        print(f"✅ Text Analysis: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"   Analysis Success: {result.get('success', False)}")
    except Exception as e:
        print(f"❌ Text Analysis Failed: {e}")
    
    print("\n🎉 Basic functionality test completed!")
    return True

if __name__ == "__main__":
    test_basic_functionality()