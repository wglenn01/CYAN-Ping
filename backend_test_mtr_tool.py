#!/usr/bin/env python3
"""
Backend API Test Suite for CyanPing - Ad-hoc MTR Tool Endpoints
Tests the NEW ad-hoc MTR Tool endpoints (/api/mtr/tool/...) that work with any host
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
    """Get a valid target ID from the tree endpoint for regression tests"""
    try:
        response = requests.get(
            f"{API_BASE}/tree",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            tree = response.json()
            for group in tree:
                targets = group.get("targets") or group.get("children") or []
                if len(targets) > 0:
                    return targets[0].get("id")
        return None
    except Exception:
        return None


def test_tool_live_before_start() -> bool:
    """Test 1: GET /api/mtr/tool/live?host=1.1.1.1 (before starting)"""
    print_test("Test 1: GET /api/mtr/tool/live?host=1.1.1.1 (before starting)")
    try:
        response = requests.get(
            f"{API_BASE}/mtr/tool/live?host=1.1.1.1",
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
        
        # Check available field (should be bool)
        if not isinstance(data["available"], bool):
            print_result(False, f"Expected available to be bool, got {type(data['available'])}", data)
            return False
        
        print_result(True, "Returns 200 with correct structure: {running:false, hops:[], cycles:0, elapsed:0, available:<bool>}", data)
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_tool_start_valid_host() -> bool:
    """Test 2: POST /api/mtr/tool/start with body {"host":"1.1.1.1"}"""
    print_test("Test 2: POST /api/mtr/tool/start with body {\"host\":\"1.1.1.1\"}")
    try:
        response = requests.post(
            f"{API_BASE}/mtr/tool/start",
            headers=get_headers(),
            json={"host": "1.1.1.1"},
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
                print_result(False, f"Returns 503 but detail doesn't mention privileges/raw sockets/NET_RAW: {detail}", data)
                return False
        
        # If it returns 200, that means NET_RAW is available (possible on some systems)
        elif response.status_code == 200:
            data = response.json()
            print_result(True, "⚠️  Returns 200 (NET_RAW appears to be available in this environment)", data)
            return True
        
        # 500 is NOT acceptable
        elif response.status_code == 500:
            print_result(False, f"❌ CRITICAL: Returns 500 (must NOT be 500, should be 503)", response.text)
            return False
        
        # Any other status code is a failure
        else:
            print_result(False, f"Expected 503 or 200, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_tool_start_empty_host() -> bool:
    """Test 3: POST /api/mtr/tool/start with body {"host":""} (empty)"""
    print_test("Test 3: POST /api/mtr/tool/start with body {\"host\":\"\"} (empty)")
    try:
        response = requests.post(
            f"{API_BASE}/mtr/tool/start",
            headers=get_headers(),
            json={"host": ""},
            timeout=10
        )
        
        # Should return 400 (host required)
        # Note: if availability check triggers 503 before validation, that's acceptable too
        if response.status_code == 400:
            data = response.json()
            detail = data.get("detail", "")
            print_result(True, f"Returns 400 with detail: {detail}", data)
            return True
        elif response.status_code == 503:
            data = response.json()
            print_result(True, "⚠️  Returns 503 (availability check before validation, acceptable)", data)
            return True
        elif response.status_code == 500:
            print_result(False, f"❌ CRITICAL: Returns 500 (must NOT be 500)", response.text)
            return False
        else:
            print_result(False, f"Expected 400 or 503, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_tool_stop() -> bool:
    """Test 4: POST /api/mtr/tool/stop with body {"host":"1.1.1.1"}"""
    print_test("Test 4: POST /api/mtr/tool/stop with body {\"host\":\"1.1.1.1\"}")
    try:
        response = requests.post(
            f"{API_BASE}/mtr/tool/stop",
            headers=get_headers(),
            json={"host": "1.1.1.1"},
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Expected 200, got {response.status_code}", response.text)
            return False
        
        data = response.json()
        
        # Should return {ok: true} (idempotent, safe when nothing running)
        if data.get("ok") == True:
            print_result(True, "Returns 200 {ok:true} (idempotent, safe when nothing running)", data)
            return True
        else:
            print_result(False, f"Returns 200 but unexpected response format", data)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_tool_live_after_stop() -> bool:
    """Test 5: GET /api/mtr/tool/live?host=1.1.1.1 after stop"""
    print_test("Test 5: GET /api/mtr/tool/live?host=1.1.1.1 after stop")
    try:
        response = requests.get(
            f"{API_BASE}/mtr/tool/live?host=1.1.1.1",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Expected 200, got {response.status_code}", response.text)
            return False
        
        data = response.json()
        
        # Should still return valid structure with running=false
        if data.get("running") == False:
            print_result(True, "Returns 200 with running:false (no error after stop)", data)
            return True
        else:
            print_result(False, f"Expected running=false, got {data.get('running')}", data)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_tool_live_no_auth() -> bool:
    """Test 6: GET /api/mtr/tool/live?host=1.1.1.1 WITHOUT Bearer token"""
    print_test("Test 6: GET /api/mtr/tool/live?host=1.1.1.1 WITHOUT Bearer token")
    try:
        response = requests.get(
            f"{API_BASE}/mtr/tool/live?host=1.1.1.1",
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


def test_tool_start_no_auth() -> bool:
    """Test 7: POST /api/mtr/tool/start without Bearer token"""
    print_test("Test 7: POST /api/mtr/tool/start without Bearer token")
    try:
        response = requests.post(
            f"{API_BASE}/mtr/tool/start",
            headers=get_headers(include_auth=False),
            json={"host": "1.1.1.1"},
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
    """Regression Test 1: POST /api/auth/login admin/admin"""
    print_test("Regression Test 1: POST /api/auth/login admin/admin")
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


def test_regression_tree() -> bool:
    """Regression Test 3: GET /api/tree"""
    print_test("Regression Test 3: GET /api/tree")
    try:
        response = requests.get(
            f"{API_BASE}/tree",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print_result(True, f"Tree endpoint still works, {len(data)} groups returned")
                return True
            else:
                print_result(False, "Tree returns 200 but not a list", data)
                return False
        else:
            print_result(False, f"Tree failed with status {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_regression_per_target_mtr_live() -> bool:
    """Regression Test 4: GET /api/targets/{id}/mtr/live (per-target endpoint)"""
    print_test("Regression Test 4: GET /api/targets/{id}/mtr/live (per-target endpoint)")
    
    target_id = get_valid_target_id()
    if not target_id:
        print_result(False, "Could not get valid target ID for regression test")
        return False
    
    try:
        response = requests.get(
            f"{API_BASE}/targets/{target_id}/mtr/live",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "running" in data and "available" in data:
                print_result(True, "Per-target MTR live endpoint still works", data)
                return True
            else:
                print_result(False, "Per-target MTR live returns 200 but missing expected fields", data)
                return False
        else:
            print_result(False, f"Per-target MTR live failed with status {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_regression_per_target_mtr_start() -> bool:
    """Regression Test 5: POST /api/targets/{id}/mtr/start (per-target endpoint)"""
    print_test("Regression Test 5: POST /api/targets/{id}/mtr/start (per-target endpoint)")
    
    target_id = get_valid_target_id()
    if not target_id:
        print_result(False, "Could not get valid target ID for regression test")
        return False
    
    try:
        response = requests.post(
            f"{API_BASE}/targets/{target_id}/mtr/start",
            headers=get_headers(),
            timeout=10
        )
        
        # Should return 503 in sandbox (graceful degradation)
        if response.status_code == 503:
            data = response.json()
            print_result(True, "Per-target MTR start returns 503 gracefully (correct for sandbox)", data)
            return True
        elif response.status_code == 200:
            data = response.json()
            print_result(True, "⚠️  Per-target MTR start returns 200 (NET_RAW available)", data)
            return True
        elif response.status_code == 500:
            print_result(False, f"❌ CRITICAL: Per-target MTR start returns 500 (must NOT be 500)", response.text)
            return False
        else:
            print_result(False, f"Expected 503 or 200, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*80)
    print("CyanPing Backend API Test Suite - Ad-hoc MTR Tool Endpoints")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print(f"Credentials: {ADMIN_USERNAME}/{ADMIN_PASSWORD}")
    print("\nCONTEXT: This sandbox has NO raw-socket capability, so real traceroute")
    print("can't run here — endpoints must degrade gracefully (503 on start, no 500s).")
    print("They work fully on the user's self-hosted server with NET_RAW.")
    
    # Login first
    if not login():
        print("\n❌ FATAL: Login failed, cannot proceed with tests")
        sys.exit(1)
    
    # Run all tests
    results = []
    
    # New ad-hoc MTR Tool endpoint tests
    print("\n" + "="*80)
    print("AD-HOC MTR TOOL ENDPOINT TESTS")
    print("="*80)
    results.append(("Test 1: GET /mtr/tool/live (before start)", test_tool_live_before_start()))
    results.append(("Test 2: POST /mtr/tool/start (valid host)", test_tool_start_valid_host()))
    results.append(("Test 3: POST /mtr/tool/start (empty host)", test_tool_start_empty_host()))
    results.append(("Test 4: POST /mtr/tool/stop", test_tool_stop()))
    results.append(("Test 5: GET /mtr/tool/live (after stop)", test_tool_live_after_stop()))
    results.append(("Test 6: GET /mtr/tool/live (no auth)", test_tool_live_no_auth()))
    results.append(("Test 7: POST /mtr/tool/start (no auth)", test_tool_start_no_auth()))
    
    # Regression tests
    print("\n" + "="*80)
    print("REGRESSION SANITY TESTS")
    print("="*80)
    results.append(("Regression 1: POST /auth/login", test_regression_login()))
    results.append(("Regression 2: GET /overview", test_regression_overview()))
    results.append(("Regression 3: GET /tree", test_regression_tree()))
    results.append(("Regression 4: GET /targets/{id}/mtr/live", test_regression_per_target_mtr_live()))
    results.append(("Regression 5: POST /targets/{id}/mtr/start", test_regression_per_target_mtr_start()))
    
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
        print("\nKey acceptance criteria met:")
        print("  ✅ No 500 errors")
        print("  ✅ tool/start returns clean 503 in this environment")
        print("  ✅ tool/stop + tool/live are safe")
        print("  ✅ Auth enforced")
        print("  ✅ Existing endpoints still work")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
