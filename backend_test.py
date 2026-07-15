#!/usr/bin/env python3
"""
Comprehensive backend API tests for CyanPing
Tests all endpoints as specified in the review request
"""
import requests
import time
import sys
from typing import Optional

# Backend URL from frontend/.env
BASE_URL = "https://uptime-tracker-41.preview.emergentagent.com/api"

# Test credentials
ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin"

# Global token storage
auth_token: Optional[str] = None


def log_test(name: str, passed: bool, details: str = ""):
    """Log test result"""
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if details:
        print(f"   Details: {details}")
    if not passed:
        global test_failures
        test_failures.append(f"{name}: {details}")


def get_headers(with_auth: bool = True) -> dict:
    """Get request headers with optional auth token"""
    headers = {"Content-Type": "application/json"}
    if with_auth and auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    return headers


# ============================================================================
# TEST 1: POST /api/auth/login - Valid credentials
# ============================================================================
def test_login_valid():
    """Test login with valid credentials (admin/admin)"""
    print("\n" + "="*80)
    print("TEST 1: POST /api/auth/login - Valid credentials")
    print("="*80)
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": ADMIN_USERNAME, "password": ADMIN_PASSWORD},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                global auth_token
                auth_token = data["access_token"]
                user = data["user"]
                if user.get("username") == ADMIN_USERNAME and user.get("role") == "Administrator":
                    log_test("Login with valid credentials", True, 
                            f"Token received, user: {user['username']}, role: {user['role']}")
                    return True
                else:
                    log_test("Login with valid credentials", False, 
                            f"User data incorrect: {user}")
            else:
                log_test("Login with valid credentials", False, 
                        f"Missing access_token or user in response: {data}")
        else:
            log_test("Login with valid credentials", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Login with valid credentials", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 2: POST /api/auth/login - Invalid credentials
# ============================================================================
def test_login_invalid():
    """Test login with wrong password returns 401"""
    print("\n" + "="*80)
    print("TEST 2: POST /api/auth/login - Invalid credentials")
    print("="*80)
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": ADMIN_USERNAME, "password": "wrongpassword"},
            timeout=10
        )
        
        if response.status_code == 401:
            log_test("Login with invalid credentials returns 401", True, 
                    "Correctly rejected with 401")
            return True
        else:
            log_test("Login with invalid credentials returns 401", False, 
                    f"Expected 401, got {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Login with invalid credentials returns 401", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 3: GET /api/auth/me - With Bearer token
# ============================================================================
def test_auth_me_with_token():
    """Test /api/auth/me with Bearer token"""
    print("\n" + "="*80)
    print("TEST 3: GET /api/auth/me - With Bearer token")
    print("="*80)
    
    if not auth_token:
        log_test("GET /api/auth/me with token", False, "No auth token available")
        return False
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("username") == ADMIN_USERNAME and data.get("role") == "Administrator":
                log_test("GET /api/auth/me with token", True, 
                        f"User: {data['username']}, Role: {data['role']}")
                return True
            else:
                log_test("GET /api/auth/me with token", False, 
                        f"Unexpected user data: {data}")
        else:
            log_test("GET /api/auth/me with token", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/auth/me with token", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 4: GET /api/auth/me - Without token
# ============================================================================
def test_auth_me_without_token():
    """Test /api/auth/me without Bearer token returns 401"""
    print("\n" + "="*80)
    print("TEST 4: GET /api/auth/me - Without Bearer token")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/auth/me",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 401:
            log_test("GET /api/auth/me without token returns 401", True, 
                    "Correctly rejected with 401")
            return True
        else:
            log_test("GET /api/auth/me without token returns 401", False, 
                    f"Expected 401, got {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/auth/me without token returns 401", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 5: GET /api/overview
# ============================================================================
def test_overview():
    """Test GET /api/overview returns stats"""
    print("\n" + "="*80)
    print("TEST 5: GET /api/overview")
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
                total = data["total"]
                if total >= 10:  # Should have ~10 seeded targets
                    log_test("GET /api/overview", True, 
                            f"Stats: up={data['up']}, warn={data['warn']}, down={data['down']}, total={total}, avg_latency={data['avg_latency']}")
                    return True
                else:
                    log_test("GET /api/overview", False, 
                            f"Expected ~10 targets, got {total}")
            else:
                log_test("GET /api/overview", False, 
                        f"Missing required keys. Got: {data}")
        else:
            log_test("GET /api/overview", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/overview", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 6: GET /api/tree
# ============================================================================
def test_tree():
    """Test GET /api/tree returns groups with targets"""
    print("\n" + "="*80)
    print("TEST 6: GET /api/tree")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/tree",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                # Check structure of first group
                group = data[0]
                required_keys = ["id", "name", "children"]
                if all(key in group for key in required_keys):
                    if isinstance(group["children"], list) and len(group["children"]) > 0:
                        target = group["children"][0]
                        target_keys = ["id", "name", "host", "probe", "status", "current", "currentLoss"]
                        if all(key in target for key in target_keys):
                            log_test("GET /api/tree", True, 
                                    f"Found {len(data)} groups with targets. First group: {group['name']}")
                            return True
                        else:
                            log_test("GET /api/tree", False, 
                                    f"Target missing required keys. Got: {target.keys()}")
                    else:
                        log_test("GET /api/tree", False, 
                                f"Group has no children")
                else:
                    log_test("GET /api/tree", False, 
                            f"Group missing required keys. Got: {group.keys()}")
            else:
                log_test("GET /api/tree", False, 
                        f"Expected list of groups, got: {type(data)}")
        else:
            log_test("GET /api/tree", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/tree", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 7: GET /api/groups
# ============================================================================
def test_get_groups():
    """Test GET /api/groups returns list of groups"""
    print("\n" + "="*80)
    print("TEST 7: GET /api/groups")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/groups",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) > 0:
                group = data[0]
                if "id" in group and "name" in group:
                    log_test("GET /api/groups", True, 
                            f"Found {len(data)} groups")
                    return True
                else:
                    log_test("GET /api/groups", False, 
                            f"Group missing id or name: {group}")
            else:
                log_test("GET /api/groups", False, 
                        f"Expected list of groups, got: {type(data)}")
        else:
            log_test("GET /api/groups", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/groups", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 8: GET /api/targets
# ============================================================================
def test_get_targets():
    """Test GET /api/targets returns flat list of targets"""
    print("\n" + "="*80)
    print("TEST 8: GET /api/targets")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/targets",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) >= 10:
                target = data[0]
                required_keys = ["id", "name", "host", "probe", "status"]
                if all(key in target for key in required_keys):
                    log_test("GET /api/targets", True, 
                            f"Found {len(data)} targets")
                    return True
                else:
                    log_test("GET /api/targets", False, 
                            f"Target missing required keys: {target.keys()}")
            else:
                log_test("GET /api/targets", False, 
                        f"Expected ~10 targets, got {len(data) if isinstance(data, list) else 'not a list'}")
        else:
            log_test("GET /api/targets", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/targets", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 9: GET /api/targets/{id} - Valid ID
# ============================================================================
def test_get_target_by_id():
    """Test GET /api/targets/{id} for a valid seeded target"""
    print("\n" + "="*80)
    print("TEST 9: GET /api/targets/{id} - Valid ID")
    print("="*80)
    
    try:
        # First get a target ID from /api/tree
        tree_response = requests.get(
            f"{BASE_URL}/tree",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if tree_response.status_code != 200:
            log_test("GET /api/targets/{id} - valid", False, 
                    "Could not fetch tree to get target ID")
            return False
        
        tree_data = tree_response.json()
        if not tree_data or not tree_data[0]["children"]:
            log_test("GET /api/targets/{id} - valid", False, 
                    "No targets in tree")
            return False
        
        target_id = tree_data[0]["children"][0]["id"]
        
        # Now test GET /api/targets/{id}
        response = requests.get(
            f"{BASE_URL}/targets/{target_id}",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            required_keys = ["id", "name", "host", "probe", "groupName"]
            if all(key in data for key in required_keys):
                log_test("GET /api/targets/{id} - valid", True, 
                        f"Target: {data['name']}, Group: {data['groupName']}")
                return True
            else:
                log_test("GET /api/targets/{id} - valid", False, 
                        f"Missing required keys. Got: {data.keys()}")
        else:
            log_test("GET /api/targets/{id} - valid", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/targets/{id} - valid", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 10: GET /api/targets/{id} - Invalid ID
# ============================================================================
def test_get_target_invalid_id():
    """Test GET /api/targets/{id} with invalid ID returns 404"""
    print("\n" + "="*80)
    print("TEST 10: GET /api/targets/{id} - Invalid ID")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/targets/invalid-id-12345",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 404:
            log_test("GET /api/targets/{id} - invalid returns 404", True, 
                    "Correctly returned 404")
            return True
        else:
            log_test("GET /api/targets/{id} - invalid returns 404", False, 
                    f"Expected 404, got {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/targets/{id} - invalid returns 404", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 11: POST /api/targets - Create target
# ============================================================================
created_target_id = None

def test_create_target():
    """Test POST /api/targets to create a new target"""
    print("\n" + "="*80)
    print("TEST 11: POST /api/targets - Create target")
    print("="*80)
    
    try:
        # First get a valid group ID
        groups_response = requests.get(
            f"{BASE_URL}/groups",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if groups_response.status_code != 200:
            log_test("POST /api/targets - create", False, 
                    "Could not fetch groups")
            return False
        
        groups = groups_response.json()
        if not groups:
            log_test("POST /api/targets - create", False, 
                    "No groups available")
            return False
        
        group_id = groups[0]["id"]
        
        # Create a new target
        new_target = {
            "name": "Test Ping",
            "host": "1.1.1.1",
            "probe": "ICMP",
            "interval": 60,
            "group_id": group_id
        }
        
        response = requests.post(
            f"{BASE_URL}/targets",
            json=new_target,
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "id" in data and data.get("name") == "Test Ping":
                global created_target_id
                created_target_id = data["id"]
                log_test("POST /api/targets - create", True, 
                        f"Created target with ID: {created_target_id}")
                return True
            else:
                log_test("POST /api/targets - create", False, 
                        f"Unexpected response: {data}")
        else:
            log_test("POST /api/targets - create", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("POST /api/targets - create", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 12: PUT /api/targets/{id} - Update target
# ============================================================================
def test_update_target():
    """Test PUT /api/targets/{id} to update a target"""
    print("\n" + "="*80)
    print("TEST 12: PUT /api/targets/{id} - Update target")
    print("="*80)
    
    if not created_target_id:
        log_test("PUT /api/targets/{id} - update", False, 
                "No created target ID available")
        return False
    
    try:
        update_data = {"name": "Test Ping Renamed"}
        
        response = requests.put(
            f"{BASE_URL}/targets/{created_target_id}",
            json=update_data,
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("name") == "Test Ping Renamed":
                log_test("PUT /api/targets/{id} - update", True, 
                        f"Updated target name to: {data['name']}")
                return True
            else:
                log_test("PUT /api/targets/{id} - update", False, 
                        f"Name not updated. Got: {data.get('name')}")
        else:
            log_test("PUT /api/targets/{id} - update", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("PUT /api/targets/{id} - update", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 13: DELETE /api/targets/{id} - Delete target
# ============================================================================
def test_delete_target():
    """Test DELETE /api/targets/{id} and verify 404 on subsequent GET"""
    print("\n" + "="*80)
    print("TEST 13: DELETE /api/targets/{id} - Delete target")
    print("="*80)
    
    if not created_target_id:
        log_test("DELETE /api/targets/{id}", False, 
                "No created target ID available")
        return False
    
    try:
        # Delete the target
        response = requests.delete(
            f"{BASE_URL}/targets/{created_target_id}",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") == True:
                # Verify it's gone with GET
                get_response = requests.get(
                    f"{BASE_URL}/targets/{created_target_id}",
                    headers=get_headers(with_auth=True),
                    timeout=10
                )
                
                if get_response.status_code == 404:
                    log_test("DELETE /api/targets/{id}", True, 
                            "Target deleted and GET returns 404")
                    return True
                else:
                    log_test("DELETE /api/targets/{id}", False, 
                            f"Target deleted but GET returned {get_response.status_code}")
            else:
                log_test("DELETE /api/targets/{id}", False, 
                        f"Delete response not ok: {data}")
        else:
            log_test("DELETE /api/targets/{id}", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("DELETE /api/targets/{id}", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 14: GET /api/targets/{id}/series - All ranges
# ============================================================================
def test_series_all_ranges():
    """Test GET /api/targets/{id}/series for all ranges (3h, 30h, 10d, 360d)"""
    print("\n" + "="*80)
    print("TEST 14: GET /api/targets/{id}/series - All ranges")
    print("="*80)
    
    try:
        # Get a seeded target ID
        tree_response = requests.get(
            f"{BASE_URL}/tree",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if tree_response.status_code != 200:
            log_test("GET /api/targets/{id}/series", False, 
                    "Could not fetch tree to get target ID")
            return False
        
        tree_data = tree_response.json()
        if not tree_data or not tree_data[0]["children"]:
            log_test("GET /api/targets/{id}/series", False, 
                    "No targets in tree")
            return False
        
        target_id = tree_data[0]["children"][0]["id"]
        
        # Test all ranges
        ranges = ["3h", "30h", "10d", "360d"]
        all_passed = True
        
        for range_val in ranges:
            response = requests.get(
                f"{BASE_URL}/targets/{target_id}/series",
                params={"range": range_val},
                headers=get_headers(with_auth=True),
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                required_keys = ["points", "stats"]
                if all(key in data for key in required_keys):
                    points = data["points"]
                    stats = data["stats"]
                    
                    # Check points structure
                    if isinstance(points, list) and len(points) > 0:
                        point = points[0]
                        point_keys = ["time", "median", "min", "max", "band", "loss"]
                        if all(key in point for key in point_keys):
                            # Check stats structure
                            stats_keys = ["current", "currentLoss", "avg", "min", "max", "avgLoss"]
                            if all(key in stats for key in stats_keys):
                                log_test(f"GET /api/targets/{{id}}/series?range={range_val}", True, 
                                        f"Points: {len(points)}, Stats: current={stats['current']}ms")
                            else:
                                log_test(f"GET /api/targets/{{id}}/series?range={range_val}", False, 
                                        f"Stats missing keys: {stats.keys()}")
                                all_passed = False
                        else:
                            log_test(f"GET /api/targets/{{id}}/series?range={range_val}", False, 
                                    f"Point missing keys: {point.keys()}")
                            all_passed = False
                    else:
                        log_test(f"GET /api/targets/{{id}}/series?range={range_val}", False, 
                                f"Points is empty or not a list")
                        all_passed = False
                else:
                    log_test(f"GET /api/targets/{{id}}/series?range={range_val}", False, 
                            f"Missing points or stats: {data.keys()}")
                    all_passed = False
            else:
                log_test(f"GET /api/targets/{{id}}/series?range={range_val}", False, 
                        f"Status {response.status_code}: {response.text}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        log_test("GET /api/targets/{id}/series", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 15: GET /api/alerts
# ============================================================================
def test_get_alerts():
    """Test GET /api/alerts returns list of alerts"""
    print("\n" + "="*80)
    print("TEST 15: GET /api/alerts")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/alerts",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                log_test("GET /api/alerts", True, 
                        f"Found {len(data)} alerts (may be empty)")
                return True
            else:
                log_test("GET /api/alerts", False, 
                        f"Expected list, got: {type(data)}")
        else:
            log_test("GET /api/alerts", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/alerts", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 16: GET /api/alert-rules
# ============================================================================
def test_get_alert_rules():
    """Test GET /api/alert-rules returns 3 seeded rules"""
    print("\n" + "="*80)
    print("TEST 16: GET /api/alert-rules")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/alert-rules",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list) and len(data) >= 3:
                rule = data[0]
                required_keys = ["id", "name", "condition", "operator", "value", "severity", "enabled"]
                if all(key in rule for key in required_keys):
                    log_test("GET /api/alert-rules", True, 
                            f"Found {len(data)} rules")
                    return True
                else:
                    log_test("GET /api/alert-rules", False, 
                            f"Rule missing keys: {rule.keys()}")
            else:
                log_test("GET /api/alert-rules", False, 
                        f"Expected 3+ rules, got {len(data) if isinstance(data, list) else 'not a list'}")
        else:
            log_test("GET /api/alert-rules", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/alert-rules", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 17: PUT /api/alert-rules/{id} - Toggle rule
# ============================================================================
def test_toggle_alert_rule():
    """Test PUT /api/alert-rules/{id} to toggle enabled status"""
    print("\n" + "="*80)
    print("TEST 17: PUT /api/alert-rules/{id} - Toggle rule")
    print("="*80)
    
    try:
        # First get a rule
        rules_response = requests.get(
            f"{BASE_URL}/alert-rules",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if rules_response.status_code != 200:
            log_test("PUT /api/alert-rules/{id}", False, 
                    "Could not fetch alert rules")
            return False
        
        rules = rules_response.json()
        if not rules:
            log_test("PUT /api/alert-rules/{id}", False, 
                    "No alert rules available")
            return False
        
        rule_id = rules[0]["id"]
        original_enabled = rules[0]["enabled"]
        
        # Toggle the rule
        response = requests.put(
            f"{BASE_URL}/alert-rules/{rule_id}",
            json={"enabled": not original_enabled},
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") == True:
                # Verify the change
                verify_response = requests.get(
                    f"{BASE_URL}/alert-rules",
                    headers=get_headers(with_auth=True),
                    timeout=10
                )
                
                if verify_response.status_code == 200:
                    updated_rules = verify_response.json()
                    updated_rule = next((r for r in updated_rules if r["id"] == rule_id), None)
                    
                    if updated_rule and updated_rule["enabled"] == (not original_enabled):
                        log_test("PUT /api/alert-rules/{id}", True, 
                                f"Toggled rule from {original_enabled} to {not original_enabled}")
                        return True
                    else:
                        log_test("PUT /api/alert-rules/{id}", False, 
                                "Rule not toggled correctly")
                else:
                    log_test("PUT /api/alert-rules/{id}", False, 
                            "Could not verify rule update")
            else:
                log_test("PUT /api/alert-rules/{id}", False, 
                        f"Update response not ok: {data}")
        else:
            log_test("PUT /api/alert-rules/{id}", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("PUT /api/alert-rules/{id}", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 18: Real probes - Verify live measurements (OPTIONAL/BEST-EFFORT)
# ============================================================================
def test_real_probes():
    """Test that real probes populate target measurements after ~20-30s"""
    print("\n" + "="*80)
    print("TEST 18: Real probes - Verify live measurements (OPTIONAL)")
    print("="*80)
    
    try:
        # Create a new target to 1.1.1.1
        groups_response = requests.get(
            f"{BASE_URL}/groups",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if groups_response.status_code != 200:
            log_test("Real probes verification", False, 
                    "Could not fetch groups")
            return False
        
        groups = groups_response.json()
        if not groups:
            log_test("Real probes verification", False, 
                    "No groups available")
            return False
        
        group_id = groups[0]["id"]
        
        # Create target
        new_target = {
            "name": "Real Probe Test",
            "host": "1.1.1.1",
            "probe": "ICMP",
            "interval": 15,  # 15 seconds
            "group_id": group_id
        }
        
        create_response = requests.post(
            f"{BASE_URL}/targets",
            json=new_target,
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if create_response.status_code != 200:
            log_test("Real probes verification", False, 
                    f"Could not create target: {create_response.text}")
            return False
        
        probe_target_id = create_response.json()["id"]
        
        print("   Waiting 30 seconds for scheduler to probe the target...")
        time.sleep(30)
        
        # Check if target has measurements
        target_response = requests.get(
            f"{BASE_URL}/targets/{probe_target_id}",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if target_response.status_code == 200:
            target_data = target_response.json()
            current_latency = target_data.get("current")
            
            if current_latency is not None and current_latency > 0:
                log_test("Real probes verification", True, 
                        f"Target has live measurements: current={current_latency}ms")
                
                # Clean up - delete the test target
                requests.delete(
                    f"{BASE_URL}/targets/{probe_target_id}",
                    headers=get_headers(with_auth=True),
                    timeout=10
                )
                return True
            else:
                log_test("Real probes verification", False, 
                        f"Target has no live measurements yet (current={current_latency}). This is optional/best-effort.")
                # Clean up
                requests.delete(
                    f"{BASE_URL}/targets/{probe_target_id}",
                    headers=get_headers(with_auth=True),
                    timeout=10
                )
        else:
            log_test("Real probes verification", False, 
                    f"Could not fetch target: {target_response.text}")
    except Exception as e:
        log_test("Real probes verification", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
test_failures = []

def run_all_tests():
    """Run all backend API tests"""
    print("\n" + "="*80)
    print("CYANPING BACKEND API TEST SUITE")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Credentials: {ADMIN_USERNAME}/{ADMIN_PASSWORD}")
    print("="*80)
    
    tests = [
        ("Auth - Login Valid", test_login_valid),
        ("Auth - Login Invalid", test_login_invalid),
        ("Auth - Me With Token", test_auth_me_with_token),
        ("Auth - Me Without Token", test_auth_me_without_token),
        ("Overview", test_overview),
        ("Tree", test_tree),
        ("Groups", test_get_groups),
        ("Targets List", test_get_targets),
        ("Target By ID - Valid", test_get_target_by_id),
        ("Target By ID - Invalid", test_get_target_invalid_id),
        ("Create Target", test_create_target),
        ("Update Target", test_update_target),
        ("Delete Target", test_delete_target),
        ("Series All Ranges", test_series_all_ranges),
        ("Alerts", test_get_alerts),
        ("Alert Rules", test_get_alert_rules),
        ("Toggle Alert Rule", test_toggle_alert_rule),
        ("Real Probes (Optional)", test_real_probes),
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
    print("TEST SUMMARY")
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
    success = run_all_tests()
    sys.exit(0 if success else 1)
