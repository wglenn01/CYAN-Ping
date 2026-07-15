#!/usr/bin/env python3
"""
Backend API Test Suite for CyanPing - Live/Continuous MTR Endpoints
Tests the NEW live/continuous MTR endpoints added to CyanPing
"""

import requests
import json
import sys
import time
from typing import Dict, Any, Optional

# Load base URL from frontend/.env
BASE_URL = "https://uptime-tracker-41.preview.emergentagent.com"
API_BASE = f"{BASE_URL}/api"

# Test credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Global token storage
auth_token: Optional[str] = None


def print_test(test_name: str):
    """Print test header"""
    print(f"\n{'='*80}")
    print(f"TEST: {test_name}")
    print('='*80)


def print_result(success: bool, message: str, details: Any = None):
    """Print test result"""
    status = "✅ PASS" if success else "❌ FAIL"
    print(f"{status}: {message}")
    if details:
        print(f"Details: {json.dumps(details, indent=2)}")


def login() -> bool:
    """Login and get JWT token"""
    print_test("Authentication - Login")
    try:
        response = requests.post(
            f"{API_BASE}/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            global auth_token
            auth_token = data.get("access_token")
            print_result(True, f"Login successful, token length: {len(auth_token)}", 
                        {"username": data.get("user", {}).get("username")})
            return True
        else:
            print_result(False, f"Login failed with status {response.status_code}", 
                        response.text)
            return False
    except Exception as e:
        print_result(False, f"Login exception: {str(e)}")
        return False


def get_headers(include_auth: bool = True) -> Dict[str, str]:
    """Get request headers"""
    headers = {"Content-Type": "application/json"}
    if include_auth and auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


def get_valid_target_id() -> Optional[str]:
    """Get a valid target ID from the tree endpoint"""
    print_test("Get Valid Target ID from Tree")
    try:
        response = requests.get(
            f"{API_BASE}/tree",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            tree = response.json()
            # Find the 8.8.8.8 target or any target
            for group in tree:
                # Handle both "targets" and "children" keys for backward compatibility
                targets = group.get("targets") or group.get("children") or []
                if len(targets) > 0:
                    target = targets[0]
                    target_id = target.get("id")
                    target_name = target.get("name", "unknown")
                    target_host = target.get("host", "unknown")
                    print_result(True, f"Found target: {target_name} ({target_host})", 
                                {"id": target_id})
                    return target_id
            
            print_result(False, "No targets found in tree")
            return None
        else:
            print_result(False, f"Failed to get tree: {response.status_code}", response.text)
            return None
    except Exception as e:
        print_result(False, f"Exception getting target ID: {str(e)}")
        return None


def test_mtr_live_before_start(target_id: str) -> bool:
    """Test 1: GET /api/targets/{id}/mtr/live before starting"""
    print_test("Test 1: GET /api/targets/{id}/mtr/live (before starting)")
    try:
        response = requests.get(
            f"{API_BASE}/targets/{target_id}/mtr/live",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Expected 200, got {response.status_code}", response.text)
            return False
        
        data = response.json()
        
        # Check required fields
        required_fields = ["running", "hops", "cycles", "elapsed", "available"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result(False, f"Missing required fields: {missing_fields}", data)
            return False
        
        # Verify values
        if data["running"] != False:
            print_result(False, f"Expected running=false, got {data['running']}", data)
            return False
        
        if not isinstance(data["hops"], list):
            print_result(False, f"Expected hops to be list, got {type(data['hops'])}", data)
            return False
        
        if data["cycles"] != 0:
            print_result(False, f"Expected cycles=0, got {data['cycles']}", data)
            return False
        
        if data["elapsed"] != 0:
            print_result(False, f"Expected elapsed=0, got {data['elapsed']}", data)
            return False
        
        # In sandbox, available should be false
        if data["available"] != False:
            print_result(True, f"⚠️  available={data['available']} (expected false in sandbox, but true means NET_RAW is available)", data)
        else:
            print_result(True, "Returns 200 with correct structure: running=false, hops=[], cycles=0, elapsed=0, available=false", data)
        
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_mtr_start(target_id: str) -> bool:
    """Test 2: POST /api/targets/{id}/mtr/start"""
    print_test("Test 2: POST /api/targets/{id}/mtr/start")
    try:
        response = requests.post(
            f"{API_BASE}/targets/{target_id}/mtr/start",
            headers=get_headers(),
            timeout=10
        )
        
        # In sandbox without NET_RAW, should return 503
        if response.status_code == 503:
            data = response.json()
            detail = data.get("detail", "")
            
            # Check that detail mentions privileges/raw sockets/NET_RAW
            keywords = ["privilege", "raw socket", "NET_RAW"]
            has_keyword = any(keyword.lower() in detail.lower() for keyword in keywords)
            
            if has_keyword:
                print_result(True, "Returns 503 with detail about elevated privileges/raw sockets/NET_RAW (correct for sandbox)", data)
                return True
            else:
                print_result(False, f"Returns 503 but detail doesn't mention privileges/raw sockets: {detail}", data)
                return False
        
        # If it returns 200, that means NET_RAW is available (possible on some systems)
        elif response.status_code == 200:
            data = response.json()
            print_result(True, "⚠️  Returns 200 (NET_RAW appears to be available in this environment)", data)
            return True
        
        # Any other status code is a failure
        else:
            print_result(False, f"Expected 503 or 200, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_mtr_stop(target_id: str) -> bool:
    """Test 3: POST /api/targets/{id}/mtr/stop"""
    print_test("Test 3: POST /api/targets/{id}/mtr/stop")
    try:
        response = requests.post(
            f"{API_BASE}/targets/{target_id}/mtr/stop",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Expected 200, got {response.status_code}", response.text)
            return False
        
        data = response.json()
        
        # Should return {ok: true} or similar success indicator
        if data.get("ok") == True or "ok" in data or "success" in str(data).lower():
            print_result(True, "Returns 200 with success indicator (idempotent stop)", data)
            return True
        else:
            print_result(False, f"Returns 200 but unexpected response format", data)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_mtr_live_after_stop(target_id: str) -> bool:
    """Test 4: GET /api/targets/{id}/mtr/live after stop"""
    print_test("Test 4: GET /api/targets/{id}/mtr/live (after stop)")
    try:
        response = requests.get(
            f"{API_BASE}/targets/{target_id}/mtr/live",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Expected 200, got {response.status_code}", response.text)
            return False
        
        data = response.json()
        
        # Should still return valid structure with running=false
        if data.get("running") == False:
            print_result(True, "Returns 200 with running=false (no error after stop)", data)
            return True
        else:
            print_result(False, f"Expected running=false, got {data.get('running')}", data)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_mtr_invalid_target_start() -> bool:
    """Test 5: POST /api/targets/BADID/mtr/start with invalid target ID"""
    print_test("Test 5: POST /api/targets/BADID/mtr/start (invalid target)")
    try:
        response = requests.post(
            f"{API_BASE}/targets/BADID/mtr/start",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 404:
            print_result(True, "Returns 404 for invalid target ID", response.json())
            return True
        else:
            print_result(False, f"Expected 404, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_mtr_invalid_target_live() -> bool:
    """Test 6: GET /api/targets/BADID/mtr/live with invalid target ID"""
    print_test("Test 6: GET /api/targets/BADID/mtr/live (invalid target)")
    try:
        response = requests.get(
            f"{API_BASE}/targets/BADID/mtr/live",
            headers=get_headers(),
            timeout=10
        )
        
        # Acceptable responses: 404 OR 200 with running=false (session doesn't exist)
        if response.status_code == 404:
            print_result(True, "Returns 404 for invalid target ID", response.json())
            return True
        elif response.status_code == 200:
            data = response.json()
            if data.get("running") == False:
                print_result(True, "Returns 200 with running=false (session doesn't exist, acceptable)", data)
                return True
            else:
                print_result(False, f"Returns 200 but unexpected data", data)
                return False
        else:
            print_result(False, f"Expected 404 or 200, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_mtr_live_no_auth(target_id: str) -> bool:
    """Test 7: GET /api/targets/{id}/mtr/live without Bearer token"""
    print_test("Test 7: GET /api/targets/{id}/mtr/live (no auth)")
    try:
        response = requests.get(
            f"{API_BASE}/targets/{target_id}/mtr/live",
            headers=get_headers(include_auth=False),
            timeout=10
        )
        
        if response.status_code == 401:
            print_result(True, "Returns 401 without Bearer token (auth required)", response.json())
            return True
        else:
            print_result(False, f"Expected 401, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_regression_login() -> bool:
    """Regression Test 1: POST /api/auth/login"""
    print_test("Regression Test 1: POST /api/auth/login")
    try:
        response = requests.post(
            f"{API_BASE}/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                print_result(True, "Login still works correctly", {"token_length": len(data["access_token"])})
                return True
            else:
                print_result(False, "Login returns 200 but no access_token", data)
                return False
        else:
            print_result(False, f"Login failed with status {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_regression_overview() -> bool:
    """Regression Test 2: GET /api/overview"""
    print_test("Regression Test 2: GET /api/overview")
    try:
        response = requests.get(
            f"{API_BASE}/overview",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "total" in data and "avg_latency" in data:
                print_result(True, "Overview endpoint still works", data)
                return True
            else:
                print_result(False, "Overview returns 200 but missing expected fields", data)
                return False
        else:
            print_result(False, f"Overview failed with status {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_regression_series(target_id: str) -> bool:
    """Regression Test 3: GET /api/targets/{id}/series?range=30h"""
    print_test("Regression Test 3: GET /api/targets/{id}/series?range=30h")
    try:
        response = requests.get(
            f"{API_BASE}/targets/{target_id}/series?range=30h",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "points" in data and isinstance(data["points"], list):
                print_result(True, f"Series endpoint still works, {len(data['points'])} points returned", 
                           {"stats": data.get("stats")})
                return True
            else:
                print_result(False, "Series returns 200 but missing points array", data)
                return False
        else:
            print_result(False, f"Series failed with status {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_regression_mtr_old(target_id: str) -> bool:
    """Regression Test 4: GET /api/targets/{id}/mtr (old endpoint)"""
    print_test("Regression Test 4: GET /api/targets/{id}/mtr (old endpoint)")
    try:
        response = requests.get(
            f"{API_BASE}/targets/{target_id}/mtr",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "available" in data:
                print_result(True, "Old MTR endpoint still works", data)
                return True
            else:
                print_result(False, "Old MTR endpoint returns 200 but missing 'available' field", data)
                return False
        else:
            print_result(False, f"Old MTR endpoint failed with status {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CyanPing Backend API Test Suite - Live/Continuous MTR Endpoints")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print(f"Credentials: {ADMIN_USERNAME}/{ADMIN_PASSWORD}")
    
    # Login first
    if not login():
        print("\n❌ FATAL: Login failed, cannot proceed with tests")
        sys.exit(1)
    
    # Get valid target ID
    target_id = get_valid_target_id()
    if not target_id:
        print("\n❌ FATAL: Could not get valid target ID, cannot proceed with tests")
        sys.exit(1)
    
    # Run all tests
    results = []
    
    # New MTR live/continuous endpoint tests
    results.append(("Test 1: GET /mtr/live (before start)", test_mtr_live_before_start(target_id)))
    results.append(("Test 2: POST /mtr/start", test_mtr_start(target_id)))
    results.append(("Test 3: POST /mtr/stop", test_mtr_stop(target_id)))
    results.append(("Test 4: GET /mtr/live (after stop)", test_mtr_live_after_stop(target_id)))
    results.append(("Test 5: POST /mtr/start (invalid target)", test_mtr_invalid_target_start()))
    results.append(("Test 6: GET /mtr/live (invalid target)", test_mtr_invalid_target_live()))
    results.append(("Test 7: GET /mtr/live (no auth)", test_mtr_live_no_auth(target_id)))
    
    # Regression tests
    results.append(("Regression 1: POST /auth/login", test_regression_login()))
    results.append(("Regression 2: GET /overview", test_regression_overview()))
    results.append(("Regression 3: GET /series", test_regression_series(target_id)))
    results.append(("Regression 4: GET /mtr (old)", test_regression_mtr_old(target_id)))
    
    # Summary
    print("\n" + "="*80)
    print("TEST SUMMARY")
    print("="*80)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*80)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*80)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
