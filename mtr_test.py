#!/usr/bin/env python3
"""
MTR (traceroute) endpoint tests for CyanPing
Tests the new MTR endpoints added to the backend
"""
import requests
import sys
from typing import Optional

# Backend URL from frontend/.env
BASE_URL = "https://uptime-tracker-41.preview.emergentagent.com/api"

# Test credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Global token storage
auth_token: Optional[str] = None
test_failures = []


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   Details: {details}")
    if not passed:
        test_failures.append(f"{name}: {details}")


def get_headers(with_auth: bool = True) -> dict:
    """Get request headers with optional auth token"""
    headers = {"Content-Type": "application/json"}
    if with_auth and auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


# ============================================================================
# SETUP: Login to get auth token
# ============================================================================
def setup_auth():
    """Login to get auth token"""
    print("\n" + "="*80)
    print("SETUP: Authenticating as admin/admin")
    print("="*80)
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data:
                global auth_token
                auth_token = data["access_token"]
                print(f"✅ Authentication successful")
                return True
            else:
                print(f"❌ Authentication failed: No access_token in response")
        else:
            print(f"❌ Authentication failed: Status {response.status_code}")
    except Exception as e:
        print(f"❌ Authentication failed: {str(e)}")
    
    return False


# ============================================================================
# HELPER: Get a valid target ID (preferably 8.8.8.8)
# ============================================================================
def get_valid_target_id():
    """Get a valid seeded target ID from /api/tree (preferably 8.8.8.8)"""
    try:
        response = requests.get(
            f"{BASE_URL}/tree",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            tree_data = response.json()
            # Try to find 8.8.8.8 target
            for group in tree_data:
                for target in group.get("children", []):
                    if target.get("host") == "8.8.8.8":
                        print(f"   Found 8.8.8.8 target with ID: {target['id']}")
                        return target["id"]
            
            # If 8.8.8.8 not found, return first available target
            if tree_data and tree_data[0].get("children"):
                target_id = tree_data[0]["children"][0]["id"]
                print(f"   Using first available target ID: {target_id}")
                return target_id
        
        print(f"   ❌ Could not get valid target ID from /api/tree")
        return None
    except Exception as e:
        print(f"   ❌ Exception getting target ID: {str(e)}")
        return None


# ============================================================================
# TEST 1: GET /api/targets/{id}/mtr - Valid target
# ============================================================================
def test_get_mtr_valid_target():
    """Test GET /api/targets/{id}/mtr returns {available, latest}"""
    print("\n" + "="*80)
    print("TEST 1: GET /api/targets/{id}/mtr - Valid target")
    print("="*80)
    
    target_id = get_valid_target_id()
    if not target_id:
        log_test("GET /api/targets/{id}/mtr - valid", False, 
                "Could not get valid target ID")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/targets/{target_id}/mtr",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            required_keys = ["available", "latest"]
            
            if all(key in data for key in required_keys):
                available = data["available"]
                latest = data["latest"]
                
                # In sandbox, available should be False (no raw socket)
                if available == False:
                    log_test("GET /api/targets/{id}/mtr - valid", True, 
                            f"available={available}, latest={latest} (expected available=False in sandbox)")
                    return True
                else:
                    log_test("GET /api/targets/{id}/mtr - valid", False, 
                            f"Expected available=False in sandbox, got available={available}")
            else:
                log_test("GET /api/targets/{id}/mtr - valid", False, 
                        f"Missing required keys. Got: {data.keys()}")
        else:
            log_test("GET /api/targets/{id}/mtr - valid", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/targets/{id}/mtr - valid", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 2: POST /api/targets/{id}/mtr/run - Valid target (should return 503)
# ============================================================================
def test_post_mtr_run_valid_target():
    """Test POST /api/targets/{id}/mtr/run returns 503 in sandbox (no raw socket)"""
    print("\n" + "="*80)
    print("TEST 2: POST /api/targets/{id}/mtr/run - Valid target (expect 503)")
    print("="*80)
    
    target_id = get_valid_target_id()
    if not target_id:
        log_test("POST /api/targets/{id}/mtr/run - valid", False, 
                "Could not get valid target ID")
        return False
    
    try:
        response = requests.post(
            f"{BASE_URL}/targets/{target_id}/mtr/run",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        # In sandbox, should return 503 (not 500)
        if response.status_code == 503:
            data = response.json()
            detail = data.get("detail", "")
            
            # Check if detail mentions elevated privileges / raw sockets / NET_RAW
            keywords = ["elevated privileges", "raw socket", "NET_RAW"]
            if any(keyword.lower() in detail.lower() for keyword in keywords):
                log_test("POST /api/targets/{id}/mtr/run - valid", True, 
                        f"Correctly returned 503 with message: {detail}")
                return True
            else:
                log_test("POST /api/targets/{id}/mtr/run - valid", False, 
                        f"Got 503 but detail doesn't mention privileges/raw sockets: {detail}")
        elif response.status_code == 500:
            log_test("POST /api/targets/{id}/mtr/run - valid", False, 
                    f"Server crashed with 500 (should be 503): {response.text}")
        else:
            log_test("POST /api/targets/{id}/mtr/run - valid", False, 
                    f"Expected 503, got {response.status_code}: {response.text}")
    except Exception as e:
        log_test("POST /api/targets/{id}/mtr/run - valid", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 3: GET /api/targets/{id}/mtr - Invalid target ID (should return 404)
# ============================================================================
def test_get_mtr_invalid_target():
    """Test GET /api/targets/{id}/mtr with invalid ID returns 404"""
    print("\n" + "="*80)
    print("TEST 3: GET /api/targets/{id}/mtr - Invalid target ID (expect 404)")
    print("="*80)
    
    invalid_id = "invalid-target-id-12345"
    
    try:
        response = requests.get(
            f"{BASE_URL}/targets/{invalid_id}/mtr",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 404:
            log_test("GET /api/targets/{id}/mtr - invalid", True, 
                    "Correctly returned 404 for invalid target ID")
            return True
        else:
            log_test("GET /api/targets/{id}/mtr - invalid", False, 
                    f"Expected 404, got {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/targets/{id}/mtr - invalid", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 4: POST /api/targets/{id}/mtr/run - Invalid target ID (should return 404)
# ============================================================================
def test_post_mtr_run_invalid_target():
    """Test POST /api/targets/{id}/mtr/run with invalid ID returns 404"""
    print("\n" + "="*80)
    print("TEST 4: POST /api/targets/{id}/mtr/run - Invalid target ID (expect 404)")
    print("="*80)
    
    invalid_id = "invalid-target-id-12345"
    
    try:
        response = requests.post(
            f"{BASE_URL}/targets/{invalid_id}/mtr/run",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 404:
            log_test("POST /api/targets/{id}/mtr/run - invalid", True, 
                    "Correctly returned 404 for invalid target ID")
            return True
        else:
            log_test("POST /api/targets/{id}/mtr/run - invalid", False, 
                    f"Expected 404, got {response.status_code}: {response.text}")
    except Exception as e:
        log_test("POST /api/targets/{id}/mtr/run - invalid", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 5: GET /api/targets/{id}/mtr - No auth (should return 401)
# ============================================================================
def test_get_mtr_no_auth():
    """Test GET /api/targets/{id}/mtr without Bearer token returns 401"""
    print("\n" + "="*80)
    print("TEST 5: GET /api/targets/{id}/mtr - No auth (expect 401)")
    print("="*80)
    
    target_id = get_valid_target_id()
    if not target_id:
        log_test("GET /api/targets/{id}/mtr - no auth", False, 
                "Could not get valid target ID")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/targets/{target_id}/mtr",
            headers={"Content-Type": "application/json"},  # No auth token
            timeout=10
        )
        
        if response.status_code == 401:
            log_test("GET /api/targets/{id}/mtr - no auth", True, 
                    "Correctly returned 401 without auth token")
            return True
        else:
            log_test("GET /api/targets/{id}/mtr - no auth", False, 
                    f"Expected 401, got {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/targets/{id}/mtr - no auth", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 6: Sanity check - GET /api/overview (ensure MTR didn't break existing endpoints)
# ============================================================================
def test_sanity_overview():
    """Sanity check: GET /api/overview still works"""
    print("\n" + "="*80)
    print("TEST 6: Sanity check - GET /api/overview")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/overview",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            required_keys = ["up", "warn", "down", "total", "avg_latency"]
            if all(key in data for key in required_keys):
                log_test("Sanity: GET /api/overview", True, 
                        f"total={data['total']}, avg_latency={data['avg_latency']}")
                return True
            else:
                log_test("Sanity: GET /api/overview", False, 
                        f"Missing required keys: {data.keys()}")
        else:
            log_test("Sanity: GET /api/overview", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Sanity: GET /api/overview", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 7: Sanity check - GET /api/targets/{id}/series?range=30h
# ============================================================================
def test_sanity_series():
    """Sanity check: GET /api/targets/{id}/series?range=30h still works"""
    print("\n" + "="*80)
    print("TEST 7: Sanity check - GET /api/targets/{id}/series?range=30h")
    print("="*80)
    
    target_id = get_valid_target_id()
    if not target_id:
        log_test("Sanity: GET /api/targets/{id}/series", False, 
                "Could not get valid target ID")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/targets/{target_id}/series",
            params={"range": "30h"},
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            required_keys = ["points", "stats"]
            if all(key in data for key in required_keys):
                points = data["points"]
                stats = data["stats"]
                log_test("Sanity: GET /api/targets/{id}/series", True, 
                        f"points={len(points)}, current={stats.get('current')}ms")
                return True
            else:
                log_test("Sanity: GET /api/targets/{id}/series", False, 
                        f"Missing required keys: {data.keys()}")
        else:
            log_test("Sanity: GET /api/targets/{id}/series", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Sanity: GET /api/targets/{id}/series", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def run_mtr_tests():
    """Run all MTR endpoint tests"""
    print("\n" + "="*80)
    print("CYANPING MTR ENDPOINT TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Credentials: {ADMIN_USERNAME}/{ADMIN_PASSWORD}")
    print("="*80)
    
    # Setup authentication
    if not setup_auth():
        print("\n❌ FATAL: Could not authenticate. Aborting tests.")
        return False
    
    tests = [
        ("GET /api/targets/{id}/mtr - valid", test_get_mtr_valid_target),
        ("POST /api/targets/{id}/mtr/run - valid (503)", test_post_mtr_run_valid_target),
        ("GET /api/targets/{id}/mtr - invalid (404)", test_get_mtr_invalid_target),
        ("POST /api/targets/{id}/mtr/run - invalid (404)", test_post_mtr_run_invalid_target),
        ("GET /api/targets/{id}/mtr - no auth (401)", test_get_mtr_no_auth),
        ("Sanity: GET /api/overview", test_sanity_overview),
        ("Sanity: GET /api/targets/{id}/series", test_sanity_series),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ FAIL: {test_name} - Unhandled exception: {str(e)}")
            failed += 1
    
    # Summary
    print("\n" + "="*80)
    print("MTR TEST SUMMARY")
    print("="*80)
    print(f"Total Tests: {passed + failed}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if test_failures:
        print("\n" + "="*80)
        print("FAILED TESTS DETAILS:")
        print("="*80)
        for failure in test_failures:
            print(f"  • {failure}")
    
    print("="*80)
    
    return failed == 0


if __name__ == "__main__":
    success = run_mtr_tests()
    sys.exit(0 if success else 1)
