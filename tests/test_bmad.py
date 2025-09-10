#!/usr/bin/env python3
"""
Test script for BMAD functionality in the Fusion 360 MCP Server.
"""

import json
import os
import sys
import requests
from typing import Dict, Any, List

# Add the src directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Server URL
SERVER_URL = "http://127.0.0.1:8000"

def test_list_bmad_folders():
    """Test the list BMAD folders endpoint."""
    response = requests.get(f"{SERVER_URL}/bmad/folders")
    assert response.status_code == 200
    data = response.json()
    assert "folders" in data
    assert len(data["folders"]) > 0
    assert "basic" in data["folders"]
    assert "advanced" in data["folders"]
    print(f"✅ List BMAD folders test passed ({len(data['folders'])} folders found)")

def test_list_bmad_methods():
    """Test the list BMAD methods endpoint."""
    response = requests.get(f"{SERVER_URL}/bmad/methods")
    assert response.status_code == 200
    data = response.json()
    assert "methods" in data
    assert len(data["methods"]) > 0
    
    # Check that we have expected methods
    method_names = [method["name"] for method in data["methods"]]
    assert "SimpleBox" in method_names
    assert "Cylinder" in method_names
    assert "RoundedBox" in method_names
    assert "BasicEnclosure" in method_names
    print(f"✅ List BMAD methods test passed ({len(data['methods'])} methods found)")

def test_list_bmad_methods_by_category():
    """Test filtering BMAD methods by category."""
    # Test basic category
    response = requests.get(f"{SERVER_URL}/bmad/methods?category=basic")
    assert response.status_code == 200
    data = response.json()
    assert "methods" in data
    assert len(data["methods"]) >= 2  # SimpleBox and Cylinder
    
    # Check all returned methods are basic category
    for method in data["methods"]:
        assert method["category"] == "basic"
    
    print(f"✅ Filter BMAD methods by category test passed")

def test_call_bmad_method():
    """Test calling a BMAD method."""
    # Test SimpleBox method
    request_data = {
        "method_name": "SimpleBox",
        "parameters": {
            "width": 20,
            "depth": 30,
            "height": 10
        }
    }
    response = requests.post(f"{SERVER_URL}/bmad/call_method", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "script" in data
    assert "message" in data
    
    # Check that the script contains expected content
    script = data["script"]
    assert "sketch" in script.lower()
    assert "rectangle" in script.lower()  
    assert "extrude" in script.lower()
    assert "20" in script  # width parameter
    assert "30" in script  # depth parameter
    assert "10" in script  # height parameter
    print("✅ Call BMAD method (SimpleBox) test passed")

def test_call_bmad_method_with_defaults():
    """Test calling a BMAD method with default parameters."""
    # Test RoundedBox method without fillet_radius (should use default)
    request_data = {
        "method_name": "RoundedBox", 
        "parameters": {
            "width": 15,
            "depth": 25,
            "height": 8
        }
    }
    response = requests.post(f"{SERVER_URL}/bmad/call_method", json=request_data)
    assert response.status_code == 200
    data = response.json()
    assert "script" in data
    
    # Check that the script contains fillet with default radius
    script = data["script"]
    assert "fillet" in script.lower()
    assert "2" in script  # default fillet radius
    print("✅ Call BMAD method with defaults test passed")

def test_call_bmad_method_error_handling():
    """Test error handling for BMAD method calls."""
    # Test unknown method
    request_data = {
        "method_name": "NonExistentMethod",
        "parameters": {}
    }
    response = requests.post(f"{SERVER_URL}/bmad/call_method", json=request_data)
    assert response.status_code == 400
    data = response.json()
    assert "detail" in data
    assert "Unknown BMAD method" in data["detail"]
    print("✅ BMAD method error handling test passed")

def run_bmad_tests():
    """Run all BMAD tests."""
    print("🧪 Running BMAD tests for Fusion 360 MCP Server...")
    try:
        test_list_bmad_folders()
        test_list_bmad_methods()
        test_list_bmad_methods_by_category()
        test_call_bmad_method()
        test_call_bmad_method_with_defaults()
        test_call_bmad_method_error_handling()
        print("✅ All BMAD tests passed!")
    except requests.exceptions.ConnectionError:
        print("❌ Failed to connect to the server. Make sure the server is running.")
        print(f"   Server URL: {SERVER_URL}")
    except AssertionError as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run_bmad_tests()