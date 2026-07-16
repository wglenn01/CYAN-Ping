#!/usr/bin/env python3
"""
Backend API Regression Test Suite for CyanPing
Regression-verify the CyanPing backend after MTR performance change (MAX_SERIES buffer reduced from 400 to 160)
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


def get_headers(include_auth: bool = True) -> Dict[str, str]:
    """Get request headers"""
    headers = {"Content-Type": "application/json"}
    if include_auth and auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


# ============================================================================
# TEST 1: Authentication
# ============================================================================

def test_auth_login() -> bool:
    """Test 1a: POST /api/auth/login admin/admin -> 200 with token"""
    print_test("Test 1a: POST /api/auth/login (admin/admin)")
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
            
            if not auth_token:
                print_result(False, "Login returns 200 but no access_token", data)
                return False
            
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


def test_auth_me() -> bool:
    """Test 1b: GET /api/auth/me -> 200"""
    print_test("Test 1b: GET /api/auth/me")
    try:
        response = requests.get(
            f"{API_BASE}/auth/me",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "username" in data:
                print_result(True, "Auth /me endpoint works", data)
                return True
            else:
                print_result(False, "Auth /me returns 200 but missing username", data)
                return False
        else:
            print_result(False, f"Auth /me failed with status {response.status_code}", response.text)
            return False
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


# ============================================================================
# TEST 2: Overview
# ============================================================================

def test_overview() -> bool:
    """Test 2: GET /api/overview -> 200 with {up,warn,down,total,avg_latency}"""
    print_test("Test 2: GET /api/overview")
    try:
        response = requests.get(
            f"{API_BASE}/overview",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            required_fields = ["up", "warn", "down", "total", "avg_latency"]
            missing_fields = [f for f in required_fields if f not in data]
            
            if missing_fields:
                print_result(False, f"Missing required fields: {missing_fields}", data)
                return False
            
            print_result(True, "Overview endpoint works with all required fields", data)
            return True
        else:
            print_result(False, f"Overview failed with status {response.status_code}", response.text)
            return False
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


# ============================================================================
# TEST 3: Tree
# ============================================================================

def test_tree() -> tuple[bool, Optional[str]]:
    """Test 3: GET /api/tree -> 200 (groups with children; each target has 'jitter'). Returns (success, target_id)"""
    print_test("Test 3: GET /api/tree")
    try:
        response = requests.get(
            f"{API_BASE}/tree",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Tree failed with status {response.status_code}", response.text)
            return False, None
        
        tree = response.json()
        
        if not isinstance(tree, list) or len(tree) == 0:
            print_result(False, "Tree returns empty or invalid structure", tree)
            return False, None
        
        # Check that groups have children and targets have jitter
        target_id = None
        has_jitter = False
        
        for group in tree:
            # Handle both "targets" and "children" keys
            targets = group.get("targets") or group.get("children") or []
            
            if len(targets) > 0:
                target = targets[0]
                target_id = target.get("id")
                
                # Check for jitter field
                if "jitter" in target:
                    has_jitter = True
                    break
        
        if not target_id:
            print_result(False, "No targets found in tree", tree)
            return False, None
        
        if not has_jitter:
            print_result(False, "Targets missing 'jitter' field", {"sample_target": targets[0] if targets else None})
            return False, target_id
        
        print_result(True, f"Tree endpoint works with {len(tree)} groups, targets have 'jitter' field", 
                    {"groups": len(tree), "sample_target_id": target_id})
        return True, target_id
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False, None


# ============================================================================
# TEST 4: Series
# ============================================================================

def test_series(target_id: str) -> bool:
    """Test 4: GET /api/targets/{id}/series?range=30h -> 200 with points + stats (incl jitter)"""
    print_test("Test 4: GET /api/targets/{id}/series?range=30h")
    try:
        response = requests.get(
            f"{API_BASE}/targets/{target_id}/series?range=30h",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Series failed with status {response.status_code}", response.text)
            return False
        
        data = response.json()
        
        # Check for points and stats
        if "points" not in data or "stats" not in data:
            print_result(False, "Series missing 'points' or 'stats'", data)
            return False
        
        points = data["points"]
        stats = data["stats"]
        
        if not isinstance(points, list):
            print_result(False, "Points is not a list", data)
            return False
        
        # Check that points have jitter field
        if len(points) > 0:
            sample_point = points[0]
            if "jitter" not in sample_point:
                print_result(False, "Points missing 'jitter' field", {"sample_point": sample_point})
                return False
        
        # Check that stats have jitter field
        if "jitter" not in stats:
            print_result(False, "Stats missing 'jitter' field", {"stats": stats})
            return False
        
        print_result(True, f"Series endpoint works with {len(points)} points, includes jitter in points and stats", 
                    {"points_count": len(points), "stats": stats})
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


# ============================================================================
# TEST 5: Per-target live MTR
# ============================================================================

def test_per_target_mtr_live(target_id: str) -> bool:
    """Test 5a: GET /api/targets/{id}/mtr/live -> 200 {running:false,hops:[],available:<bool>}"""
    print_test("Test 5a: GET /api/targets/{id}/mtr/live")
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
        required_fields = ["running", "hops", "available"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result(False, f"Missing required fields: {missing_fields}", data)
            return False
        
        if not isinstance(data["hops"], list):
            print_result(False, f"Expected hops to be list, got {type(data['hops'])}", data)
            return False
        
        print_result(True, "Per-target MTR live endpoint works", 
                    {"running": data["running"], "hops_count": len(data["hops"]), "available": data["available"]})
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_per_target_mtr_start(target_id: str) -> bool:
    """Test 5b: POST /api/targets/{id}/mtr/start -> 503 (graceful, not 500)"""
    print_test("Test 5b: POST /api/targets/{id}/mtr/start")
    try:
        response = requests.post(
            f"{API_BASE}/targets/{target_id}/mtr/start",
            headers=get_headers(),
            timeout=10
        )
        
        # In sandbox without NET_RAW, should return 503
        if response.status_code == 503:
            data = response.json()
            print_result(True, "Returns 503 (graceful degradation in sandbox)", data)
            return True
        
        # If it returns 200, that means NET_RAW is available
        elif response.status_code == 200:
            data = response.json()
            print_result(True, "⚠️  Returns 200 (NET_RAW appears to be available)", data)
            return True
        
        # 500 is a failure
        elif response.status_code == 500:
            print_result(False, "Returns 500 (should be 503 for graceful degradation)", response.text)
            return False
        
        # Any other status code
        else:
            print_result(False, f"Expected 503 or 200, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_per_target_mtr_stop(target_id: str) -> bool:
    """Test 5c: POST /api/targets/{id}/mtr/stop -> 200"""
    print_test("Test 5c: POST /api/targets/{id}/mtr/stop")
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
        print_result(True, "Per-target MTR stop works (idempotent)", data)
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


# ============================================================================
# TEST 6: Ad-hoc MTR tool
# ============================================================================

def test_adhoc_mtr_live() -> bool:
    """Test 6a: GET /api/mtr/tool/live?host=1.1.1.1 -> 200"""
    print_test("Test 6a: GET /api/mtr/tool/live?host=1.1.1.1")
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
        required_fields = ["running", "hops", "available"]
        missing_fields = [f for f in required_fields if f not in data]
        
        if missing_fields:
            print_result(False, f"Missing required fields: {missing_fields}", data)
            return False
        
        print_result(True, "Ad-hoc MTR live endpoint works", 
                    {"running": data["running"], "hops_count": len(data["hops"]), "available": data["available"]})
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_adhoc_mtr_start() -> bool:
    """Test 6b: POST /api/mtr/tool/start {"host":"1.1.1.1"} -> 503 (graceful, not 500)"""
    print_test("Test 6b: POST /api/mtr/tool/start")
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
            print_result(True, "Returns 503 (graceful degradation in sandbox)", data)
            return True
        
        # If it returns 200, that means NET_RAW is available
        elif response.status_code == 200:
            data = response.json()
            print_result(True, "⚠️  Returns 200 (NET_RAW appears to be available)", data)
            return True
        
        # 500 is a failure
        elif response.status_code == 500:
            print_result(False, "Returns 500 (should be 503 for graceful degradation)", response.text)
            return False
        
        # Any other status code
        else:
            print_result(False, f"Expected 503 or 200, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_adhoc_mtr_stop() -> bool:
    """Test 6c: POST /api/mtr/tool/stop {"host":"1.1.1.1"} -> 200"""
    print_test("Test 6c: POST /api/mtr/tool/stop")
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
        print_result(True, "Ad-hoc MTR stop works (idempotent)", data)
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


# ============================================================================
# TEST 7: Auth enforcement
# ============================================================================

def test_auth_enforcement() -> bool:
    """Test 7: GET /api/mtr/tool/live?host=1.1.1.1 without token -> 401"""
    print_test("Test 7: GET /api/mtr/tool/live (no auth)")
    try:
        response = requests.get(
            f"{API_BASE}/mtr/tool/live?host=1.1.1.1",
            headers=get_headers(include_auth=False),
            timeout=10
        )
        
        if response.status_code == 401:
            print_result(True, "Returns 401 without Bearer token (auth enforced)", response.json())
            return True
        else:
            print_result(False, f"Expected 401, got {response.status_code}", response.text)
            return False
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


# ============================================================================
# TEST 8: Alerts
# ============================================================================

def test_alerts() -> bool:
    """Test 8a: GET /api/alerts -> 200"""
    print_test("Test 8a: GET /api/alerts")
    try:
        response = requests.get(
            f"{API_BASE}/alerts",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Expected 200, got {response.status_code}", response.text)
            return False
        
        data = response.json()
        
        if not isinstance(data, list):
            print_result(False, "Alerts should return a list", data)
            return False
        
        print_result(True, f"Alerts endpoint works, {len(data)} alerts returned", {"count": len(data)})
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


def test_alert_rules() -> bool:
    """Test 8b: GET /api/alert-rules -> 200"""
    print_test("Test 8b: GET /api/alert-rules")
    try:
        response = requests.get(
            f"{API_BASE}/alert-rules",
            headers=get_headers(),
            timeout=10
        )
        
        if response.status_code != 200:
            print_result(False, f"Expected 200, got {response.status_code}", response.text)
            return False
        
        data = response.json()
        
        if not isinstance(data, list):
            print_result(False, "Alert rules should return a list", data)
            return False
        
        print_result(True, f"Alert rules endpoint works, {len(data)} rules returned", {"count": len(data)})
        return True
        
    except Exception as e:
        print_result(False, f"Exception: {str(e)}")
        return False


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Run all regression tests"""
    print("\n" + "="*80)
    print("CyanPing Backend Regression Test Suite")
    print("Verifying backend after MTR performance change (MAX_SERIES 400->160)")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"API Base: {API_BASE}")
    print(f"Credentials: {ADMIN_USERNAME}/{ADMIN_PASSWORD}")
    
    # Run all tests
    results = []
    target_id = None
    
    # Test 1: Authentication
    results.append(("Test 1a: POST /api/auth/login", test_auth_login()))
    if not auth_token:
        print("\n❌ FATAL: Login failed, cannot proceed with tests")
        sys.exit(1)
    
    results.append(("Test 1b: GET /api/auth/me", test_auth_me()))
    
    # Test 2: Overview
    results.append(("Test 2: GET /api/overview", test_overview()))
    
    # Test 3: Tree (also gets target_id)
    tree_success, target_id = test_tree()
    results.append(("Test 3: GET /api/tree", tree_success))
    
    if not target_id:
        print("\n❌ FATAL: Could not get valid target ID, cannot proceed with target-specific tests")
        sys.exit(1)
    
    # Test 4: Series
    results.append(("Test 4: GET /api/targets/{id}/series?range=30h", test_series(target_id)))
    
    # Test 5: Per-target live MTR
    results.append(("Test 5a: GET /api/targets/{id}/mtr/live", test_per_target_mtr_live(target_id)))
    results.append(("Test 5b: POST /api/targets/{id}/mtr/start", test_per_target_mtr_start(target_id)))
    results.append(("Test 5c: POST /api/targets/{id}/mtr/stop", test_per_target_mtr_stop(target_id)))
    
    # Test 6: Ad-hoc MTR tool
    results.append(("Test 6a: GET /api/mtr/tool/live?host=1.1.1.1", test_adhoc_mtr_live()))
    results.append(("Test 6b: POST /api/mtr/tool/start", test_adhoc_mtr_start()))
    results.append(("Test 6c: POST /api/mtr/tool/stop", test_adhoc_mtr_stop()))
    
    # Test 7: Auth enforcement
    results.append(("Test 7: Auth enforcement on MTR tool", test_auth_enforcement()))
    
    # Test 8: Alerts
    results.append(("Test 8a: GET /api/alerts", test_alerts()))
    results.append(("Test 8b: GET /api/alert-rules", test_alert_rules()))
    
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
        print("\nKEY ACCEPTANCE CRITERIA MET:")
        print("✅ No 500 errors anywhere")
        print("✅ All listed endpoints return expected status codes")
        print("✅ MTR start endpoints return clean 503 in sandbox (graceful degradation)")
        print("✅ All endpoints include required fields (jitter in tree/series/stats)")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
