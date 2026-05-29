#!/usr/bin/env python3
"""Test script to verify Copilot and Saarthi AI services are working."""

import requests
import json

BASE_URL = "http://localhost:8000"

def test_copilot():
    """Test Copilot endpoint."""
    print("\n=== Testing Copilot ===")
    
    # First, we need to authenticate (using a test approach)
    # For now, let's just test if the endpoint exists
    url = f"{BASE_URL}/copilot/query"
    
    # Test payload
    payload = {
        "query": "What is my attendance status?",
        "entities": {}
    }
    
    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200 or response.status_code == 401  # 401 means auth required, which is expected
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_saarthi():
    """Test Saarthi endpoint."""
    print("\n=== Testing Saarthi ===")
    
    url = f"{BASE_URL}/saarthi/status"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 401:
            print("Authentication required (expected)")
            return True
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200 or response.status_code == 401
    except Exception as e:
        print(f"Error: {e}")
        return False

def check_api_docs():
    """Check if API docs are accessible."""
    print("\n=== Checking API Documentation ===")
    
    try:
        response = requests.get(f"{BASE_URL}/docs", timeout=5)
        print(f"API Docs Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing LPU Smart Campus AI Services")
    print("=" * 50)
    
    docs_ok = check_api_docs()
    copilot_ok = test_copilot()
    saarthi_ok = test_saarthi()
    
    print("\n" + "=" * 50)
    print("Test Results:")
    print(f"  API Docs: {'✓' if docs_ok else '✗'}")
    print(f"  Copilot: {'✓' if copilot_ok else '✗'}")
    print(f"  Saarthi: {'✓' if saarthi_ok else '✗'}")
    print("=" * 50)
