import requests
import os
import django

# Setup Django environment to access models directly if needed, 
# but here we want to test the HTTP endpoint.

# We need a token first. Let's try to login as admin.
# Assuming there is a superuser '074000000' (from previous context or common patterns)
# If not, I might need to create one or use an existing token if I could find one.
# Actually, I can use the `requests` library to hit the endpoint.

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_endpoint():
    print(f"Testing {BASE_URL}/delivery/agents/...")
    
    # 1. Login to get token
    # I'll try a known admin credential if available, or just check if the endpoint exists (401 vs 404)
    
    try:
        response = requests.get(f"{BASE_URL}/delivery/agents/")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text[:200]}")
        
        if response.status_code == 404:
            print("❌ Endpoint not found. The server might not have reloaded the URL configuration.")
        elif response.status_code == 401:
            print("✅ Endpoint exists (Auth required). URL routing is working.")
        elif response.status_code == 200:
            print("✅ Success!")
        else:
            print(f"⚠️ Unexpected status: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Is it running on port 8000?")

if __name__ == "__main__":
    test_endpoint()
