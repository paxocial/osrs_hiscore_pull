#!/usr/bin/env python3
"""Simple test script for OSRS Analytics API."""

import requests
import json
from datetime import datetime

# API base URL (adjust if running on different port)
BASE_URL = "http://localhost:8000"

def test_health_endpoint():
    """Test the health check endpoint."""
    print("Testing health endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_root_endpoint():
    """Test the root endpoint."""
    print("\nTesting root endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_accounts_endpoint():
    """Test the accounts endpoint."""
    print("\nTesting accounts endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/accounts/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {data['total']} accounts")
            for account in data['accounts'][:3]:  # Show first 3 accounts
                print(f"  - {account['name']} (ID: {account['id']})")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_snapshots_endpoint():
    """Test the snapshots endpoint."""
    print("\nTesting snapshots endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/snapshots/", params={"page_size": 5})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Found {data['total']} snapshots")
            for snapshot in data['snapshots'][:3]:  # Show first 3 snapshots
                print(f"  - {snapshot['snapshot_id']} ({snapshot['account_name']})")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_docs_endpoint():
    """Test the API documentation endpoint."""
    print("\nTesting API docs endpoint...")
    try:
        response = requests.get(f"{BASE_URL}/docs")
        print(f"Status: {response.status_code}")
        print(f"Docs available at: {BASE_URL}/docs")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    """Run all API tests."""
    print("=" * 50)
    print("OSRS Analytics API Test Suite")
    print("=" * 50)
    print(f"Testing API at: {BASE_URL}")
    print(f"Timestamp: {datetime.now()}")
    print()

    tests = [
        ("Health Check", test_health_endpoint),
        ("Root Endpoint", test_root_endpoint),
        ("Accounts List", test_accounts_endpoint),
        ("Snapshots List", test_snapshots_endpoint),
        ("API Documentation", test_docs_endpoint),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"Running: {test_name}")
        success = test_func()
        results.append((test_name, success))
        print(f"Result: {'✅ PASS' if success else '❌ FAIL'}")
        print("-" * 30)

    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    passed = sum(1 for _, success in results if success)
    total = len(results)

    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{test_name:.<30} {status}")

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! API is working correctly.")
        print(f"\nYou can access the interactive API docs at: {BASE_URL}/docs")
    else:
        print("⚠️  Some tests failed. Check the API server logs.")

    print("=" * 50)

if __name__ == "__main__":
    main()