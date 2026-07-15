#!/usr/bin/env python3
"""
HIGH-RESOLUTION PROBE ENGINE RE-TEST for CyanPing
Tests all requirements from the review request after the rewrite
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
# TEST 1: POST /api/auth/login - Valid credentials
# ============================================================================
def test_1_login_valid():
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
                if user.get("username") == ADMIN_USERNAME:
                    log_test("Login with admin/admin", True, 
                            f"Token received, user: {user['username']}")
                    return True
                else:
                    log_test("Login with admin/admin", False, 
                            f"User data incorrect: {user}")
            else:
                log_test("Login with admin/admin", False, 
                        f"Missing access_token or user: {data}")
        else:
            log_test("Login with admin/admin", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Login with admin/admin", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 2: POST /api/auth/login - Invalid credentials (wrong password -> 401)
# ============================================================================
def test_2_login_invalid():
    """Test login with wrong password returns 401"""
    print("\n" + "="*80)
    print("TEST 2: POST /api/auth/login - Wrong password -> 401")
    print("="*80)
    
    try:
        response = requests.post(
            f"{BASE_URL}/auth/login",
            json={"username": ADMIN_USERNAME, "password": "wrongpassword"},
            timeout=10
        )
        
        if response.status_code == 401:
            log_test("Wrong password returns 401", True, "Correctly rejected")
            return True
        else:
            log_test("Wrong password returns 401", False, 
                    f"Expected 401, got {response.status_code}")
    except Exception as e:
        log_test("Wrong password returns 401", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 3: GET /api/overview -> {up,warn,down,total(=10),avg_latency}
# ============================================================================
def test_3_overview():
    """Test GET /api/overview returns correct stats"""
    print("\n" + "="*80)
    print("TEST 3: GET /api/overview")
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
                if total == 10:
                    log_test("GET /api/overview", True, 
                            f"up={data['up']}, warn={data['warn']}, down={data['down']}, total={total}, avg_latency={data['avg_latency']}")
                    return True
                else:
                    log_test("GET /api/overview", False, 
                            f"Expected total=10, got {total}")
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
# TEST 4: GET /api/tree -> each target must include 'jitter' key (numeric)
# ============================================================================
def test_4_tree_with_jitter():
    """Test GET /api/tree returns groups with targets including jitter field"""
    print("\n" + "="*80)
    print("TEST 4: GET /api/tree - Verify jitter field in targets")
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
                all_have_jitter = True
                missing_jitter = []
                
                for group in data:
                    if "children" in group and isinstance(group["children"], list):
                        for target in group["children"]:
                            if "jitter" not in target:
                                all_have_jitter = False
                                missing_jitter.append(f"{target.get('name', 'unknown')}")
                            elif not isinstance(target["jitter"], (int, float)):
                                all_have_jitter = False
                                missing_jitter.append(f"{target.get('name', 'unknown')} (jitter not numeric)")
                
                if all_have_jitter:
                    log_test("GET /api/tree - jitter field", True, 
                            f"All targets have numeric jitter field. Found {len(data)} groups")
                    return True
                else:
                    log_test("GET /api/tree - jitter field", False, 
                            f"Targets missing/invalid jitter: {missing_jitter}")
            else:
                log_test("GET /api/tree - jitter field", False, 
                        f"Expected list of groups, got: {type(data)}")
        else:
            log_test("GET /api/tree - jitter field", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/tree - jitter field", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 5: GET /api/targets/{id} -> includes jitter + groupName
# ============================================================================
def test_5_target_by_id_with_jitter():
    """Test GET /api/targets/{id} includes jitter and groupName"""
    print("\n" + "="*80)
    print("TEST 5: GET /api/targets/{id} - Verify jitter + groupName")
    print("="*80)
    
    try:
        # Get a target ID from tree
        tree_response = requests.get(
            f"{BASE_URL}/tree",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if tree_response.status_code != 200:
            log_test("GET /api/targets/{id} - jitter", False, 
                    "Could not fetch tree")
            return False
        
        tree_data = tree_response.json()
        if not tree_data or not tree_data[0]["children"]:
            log_test("GET /api/targets/{id} - jitter", False, 
                    "No targets in tree")
            return False
        
        target_id = tree_data[0]["children"][0]["id"]
        
        # Get target by ID
        response = requests.get(
            f"{BASE_URL}/targets/{target_id}",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if "jitter" in data and "groupName" in data:
                if isinstance(data["jitter"], (int, float)):
                    log_test("GET /api/targets/{id} - jitter + groupName", True, 
                            f"jitter={data['jitter']}, groupName={data['groupName']}")
                    return True
                else:
                    log_test("GET /api/targets/{id} - jitter + groupName", False, 
                            f"jitter not numeric: {data['jitter']}")
            else:
                log_test("GET /api/targets/{id} - jitter + groupName", False, 
                        f"Missing jitter or groupName. Got keys: {data.keys()}")
        else:
            log_test("GET /api/targets/{id} - jitter + groupName", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/targets/{id} - jitter + groupName", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 6: SERIES endpoint - Verify jitter in points and stats for all ranges
# ============================================================================
def test_6_series_with_jitter():
    """Test GET /api/targets/{id}/series for all ranges with jitter validation"""
    print("\n" + "="*80)
    print("TEST 6: GET /api/targets/{id}/series - Verify jitter in points & stats")
    print("="*80)
    
    try:
        # Get a seeded target (preferably 8.8.8.8)
        tree_response = requests.get(
            f"{BASE_URL}/tree",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if tree_response.status_code != 200:
            log_test("SERIES - jitter validation", False, "Could not fetch tree")
            return False
        
        tree_data = tree_response.json()
        target_id = None
        
        # Try to find 8.8.8.8 target
        for group in tree_data:
            for target in group.get("children", []):
                if target.get("host") == "8.8.8.8":
                    target_id = target["id"]
                    break
            if target_id:
                break
        
        # Fallback to first target if 8.8.8.8 not found
        if not target_id and tree_data and tree_data[0]["children"]:
            target_id = tree_data[0]["children"][0]["id"]
        
        if not target_id:
            log_test("SERIES - jitter validation", False, "No target found")
            return False
        
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
                
                # Check structure
                if "points" not in data or "stats" not in data:
                    log_test(f"SERIES range={range_val}", False, 
                            f"Missing points or stats")
                    all_passed = False
                    continue
                
                points = data["points"]
                stats = data["stats"]
                
                # Verify points is NON-EMPTY
                if not isinstance(points, list) or len(points) == 0:
                    log_test(f"SERIES range={range_val}", False, 
                            f"Points is empty or not a list")
                    all_passed = False
                    continue
                
                # Verify each point has required keys including jitter
                point = points[0]
                required_point_keys = ["time", "median", "min", "max", "band", "jitter", "loss"]
                if not all(key in point for key in required_point_keys):
                    log_test(f"SERIES range={range_val}", False, 
                            f"Point missing keys. Expected {required_point_keys}, got {list(point.keys())}")
                    all_passed = False
                    continue
                
                # Verify stats has required keys including jitter
                required_stats_keys = ["current", "currentLoss", "avg", "min", "max", "avgLoss", "jitter"]
                if not all(key in stats for key in required_stats_keys):
                    log_test(f"SERIES range={range_val}", False, 
                            f"Stats missing keys. Expected {required_stats_keys}, got {list(stats.keys())}")
                    all_passed = False
                    continue
                
                log_test(f"SERIES range={range_val}", True, 
                        f"Points: {len(points)}, stats.jitter={stats['jitter']}")
            else:
                log_test(f"SERIES range={range_val}", False, 
                        f"Status {response.status_code}")
                all_passed = False
        
        return all_passed
        
    except Exception as e:
        log_test("SERIES - jitter validation", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 7: CREATE fractional-interval target (interval=0.5)
# ============================================================================
fractional_target_id = None

def test_7_create_fractional_interval_target():
    """Test POST /api/targets with interval=0.5 (fractional)"""
    print("\n" + "="*80)
    print("TEST 7: POST /api/targets - Fractional interval (0.5s)")
    print("="*80)
    
    try:
        # Get a valid group ID
        groups_response = requests.get(
            f"{BASE_URL}/groups",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if groups_response.status_code != 200:
            log_test("CREATE fractional interval target", False, 
                    "Could not fetch groups")
            return False
        
        groups = groups_response.json()
        if not groups:
            log_test("CREATE fractional interval target", False, 
                    "No groups available")
            return False
        
        group_id = groups[0]["id"]
        
        # Create target with interval=0.5
        new_target = {
            "name": "HiRes",
            "host": "1.1.1.1",
            "probe": "ICMP",
            "interval": 0.5,
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
            if "id" in data and "interval" in data:
                global fractional_target_id
                fractional_target_id = data["id"]
                
                # CRITICAL: interval MUST equal 0.5 (float)
                if data["interval"] == 0.5:
                    log_test("CREATE fractional interval target (0.5s)", True, 
                            f"Created target with interval={data['interval']}, id={fractional_target_id}")
                    return True
                else:
                    log_test("CREATE fractional interval target (0.5s)", False, 
                            f"Expected interval=0.5, got {data['interval']}")
            else:
                log_test("CREATE fractional interval target (0.5s)", False, 
                        f"Missing id or interval in response: {data}")
        else:
            log_test("CREATE fractional interval target (0.5s)", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("CREATE fractional interval target (0.5s)", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 8: Wait ~12s, verify 'current' latency is populated
# ============================================================================
def test_8_verify_live_probing():
    """Wait ~12s and verify target has live measurements"""
    print("\n" + "="*80)
    print("TEST 8: Verify live probing after ~12s")
    print("="*80)
    
    if not fractional_target_id:
        log_test("Verify live probing", False, "No fractional target ID")
        return False
    
    try:
        print("   Waiting 12 seconds for probing...")
        time.sleep(12)
        
        response = requests.get(
            f"{BASE_URL}/targets/{fractional_target_id}",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            current = data.get("current")
            
            if current is not None and current > 0:
                log_test("Verify live probing (0.5s interval)", True, 
                        f"current={current}ms (probing working)")
                return True
            else:
                # Best-effort: try waiting a bit more
                print("   Current still null, waiting 3 more seconds...")
                time.sleep(3)
                
                response2 = requests.get(
                    f"{BASE_URL}/targets/{fractional_target_id}",
                    headers=get_headers(with_auth=True),
                    timeout=10
                )
                
                if response2.status_code == 200:
                    data2 = response2.json()
                    current2 = data2.get("current")
                    
                    if current2 is not None and current2 > 0:
                        log_test("Verify live probing (0.5s interval)", True, 
                                f"current={current2}ms (probing working after 15s)")
                        return True
                    else:
                        log_test("Verify live probing (0.5s interval)", False, 
                                f"current still null after 15s (best-effort test)")
                else:
                    log_test("Verify live probing (0.5s interval)", False, 
                            f"Could not fetch target: {response2.status_code}")
        else:
            log_test("Verify live probing (0.5s interval)", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Verify live probing (0.5s interval)", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 9: UPDATE interval to 0.25
# ============================================================================
def test_9_update_interval_to_025():
    """Test PUT /api/targets/{id} to update interval to 0.25"""
    print("\n" + "="*80)
    print("TEST 9: PUT /api/targets/{id} - Update interval to 0.25")
    print("="*80)
    
    if not fractional_target_id:
        log_test("UPDATE interval to 0.25", False, "No fractional target ID")
        return False
    
    try:
        response = requests.put(
            f"{BASE_URL}/targets/{fractional_target_id}",
            json={"interval": 0.25},
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("interval") == 0.25:
                log_test("UPDATE interval to 0.25", True, 
                        f"interval={data['interval']}")
                return True
            else:
                log_test("UPDATE interval to 0.25", False, 
                        f"Expected interval=0.25, got {data.get('interval')}")
        else:
            log_test("UPDATE interval to 0.25", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("UPDATE interval to 0.25", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 10: Test min clamp (interval=0.1 should clamp to 0.25)
# ============================================================================
def test_10_min_interval_clamp():
    """Test PUT /api/targets/{id} with interval=0.1 should clamp to 0.25"""
    print("\n" + "="*80)
    print("TEST 10: PUT /api/targets/{id} - Min clamp (0.1 -> 0.25)")
    print("="*80)
    
    if not fractional_target_id:
        log_test("Min interval clamp", False, "No fractional target ID")
        return False
    
    try:
        response = requests.put(
            f"{BASE_URL}/targets/{fractional_target_id}",
            json={"interval": 0.1},
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("interval") == 0.25:
                log_test("Min interval clamp (0.1 -> 0.25)", True, 
                        f"Correctly clamped to {data['interval']}")
                return True
            else:
                log_test("Min interval clamp (0.1 -> 0.25)", False, 
                        f"Expected clamp to 0.25, got {data.get('interval')}")
        else:
            log_test("Min interval clamp (0.1 -> 0.25)", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Min interval clamp (0.1 -> 0.25)", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 11: DELETE fractional target
# ============================================================================
def test_11_delete_fractional_target():
    """Test DELETE /api/targets/{id} and verify 404 on subsequent GET"""
    print("\n" + "="*80)
    print("TEST 11: DELETE /api/targets/{id} - Fractional target")
    print("="*80)
    
    if not fractional_target_id:
        log_test("DELETE fractional target", False, "No fractional target ID")
        return False
    
    try:
        response = requests.delete(
            f"{BASE_URL}/targets/{fractional_target_id}",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("ok") == True:
                # Verify 404 on GET
                get_response = requests.get(
                    f"{BASE_URL}/targets/{fractional_target_id}",
                    headers=get_headers(with_auth=True),
                    timeout=10
                )
                
                if get_response.status_code == 404:
                    log_test("DELETE fractional target", True, 
                            "Deleted and GET returns 404")
                    return True
                else:
                    log_test("DELETE fractional target", False, 
                            f"Deleted but GET returned {get_response.status_code}")
            else:
                log_test("DELETE fractional target", False, 
                        f"Delete response not ok: {data}")
        else:
            log_test("DELETE fractional target", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("DELETE fractional target", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 12: GET /api/alert-rules - Should have 4 rules including "High Jitter"
# ============================================================================
def test_12_alert_rules_with_jitter():
    """Test GET /api/alert-rules returns 4 rules including 'High Jitter' with condition 'jitter'"""
    print("\n" + "="*80)
    print("TEST 12: GET /api/alert-rules - Verify 4 rules including 'High Jitter'")
    print("="*80)
    
    try:
        response = requests.get(
            f"{BASE_URL}/alert-rules",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                if len(data) == 4:
                    # Check for "High Jitter" rule
                    high_jitter_rule = None
                    for rule in data:
                        if rule.get("name") == "High Jitter":
                            high_jitter_rule = rule
                            break
                    
                    if high_jitter_rule:
                        if high_jitter_rule.get("condition") == "jitter":
                            log_test("GET /api/alert-rules - 4 rules + High Jitter", True, 
                                    f"Found 4 rules including 'High Jitter' (condition=jitter)")
                            return True
                        else:
                            log_test("GET /api/alert-rules - 4 rules + High Jitter", False, 
                                    f"High Jitter rule has wrong condition: {high_jitter_rule.get('condition')}")
                    else:
                        log_test("GET /api/alert-rules - 4 rules + High Jitter", False, 
                                f"'High Jitter' rule not found. Rules: {[r.get('name') for r in data]}")
                else:
                    log_test("GET /api/alert-rules - 4 rules + High Jitter", False, 
                            f"Expected 4 rules, got {len(data)}")
            else:
                log_test("GET /api/alert-rules - 4 rules + High Jitter", False, 
                        f"Expected list, got: {type(data)}")
        else:
            log_test("GET /api/alert-rules - 4 rules + High Jitter", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("GET /api/alert-rules - 4 rules + High Jitter", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 13: PUT /api/alert-rules/{id} - Toggle "High Jitter" rule
# ============================================================================
def test_13_toggle_high_jitter_rule():
    """Test PUT /api/alert-rules/{id} to toggle 'High Jitter' rule"""
    print("\n" + "="*80)
    print("TEST 13: PUT /api/alert-rules/{id} - Toggle 'High Jitter' rule")
    print("="*80)
    
    try:
        # Get alert rules
        rules_response = requests.get(
            f"{BASE_URL}/alert-rules",
            headers=get_headers(with_auth=True),
            timeout=10
        )
        
        if rules_response.status_code != 200:
            log_test("Toggle High Jitter rule", False, "Could not fetch alert rules")
            return False
        
        rules = rules_response.json()
        high_jitter_rule = None
        
        for rule in rules:
            if rule.get("name") == "High Jitter":
                high_jitter_rule = rule
                break
        
        if not high_jitter_rule:
            log_test("Toggle High Jitter rule", False, "'High Jitter' rule not found")
            return False
        
        rule_id = high_jitter_rule["id"]
        original_enabled = high_jitter_rule["enabled"]
        
        # Toggle the rule
        response = requests.put(
            f"{BASE_URL}/alert-rules/{rule_id}",
            json={"enabled": True},
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
                    
                    if updated_rule and updated_rule["enabled"] == True:
                        log_test("Toggle High Jitter rule", True, 
                                f"Toggled from {original_enabled} to True")
                        return True
                    else:
                        log_test("Toggle High Jitter rule", False, 
                                "Rule not toggled correctly")
                else:
                    log_test("Toggle High Jitter rule", False, 
                            "Could not verify rule update")
            else:
                log_test("Toggle High Jitter rule", False, 
                        f"Update response not ok: {data}")
        else:
            log_test("Toggle High Jitter rule", False, 
                    f"Status {response.status_code}: {response.text}")
    except Exception as e:
        log_test("Toggle High Jitter rule", False, f"Exception: {str(e)}")
    
    return False


# ============================================================================
# TEST 14: GET /api/alerts - Verify structure
# ============================================================================
def test_14_get_alerts():
    """Test GET /api/alerts returns list with correct structure"""
    print("\n" + "="*80)
    print("TEST 14: GET /api/alerts - Verify structure")
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
                # Check structure if alerts exist
                if len(data) > 0:
                    alert = data[0]
                    required_keys = ["id", "target", "targetId", "rule", "severity", "status", "message", "since"]
                    if all(key in alert for key in required_keys):
                        log_test("GET /api/alerts", True, 
                                f"Found {len(data)} alerts with correct structure")
                        return True
                    else:
                        log_test("GET /api/alerts", False, 
                                f"Alert missing keys. Expected {required_keys}, got {list(alert.keys())}")
                else:
                    log_test("GET /api/alerts", True, 
                            "Alerts list is empty (valid)")
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
# MAIN TEST RUNNER
# ============================================================================
def run_all_tests():
    """Run all backend API tests"""
    print("\n" + "="*80)
    print("CYANPING HIGH-RESOLUTION PROBE ENGINE RE-TEST")
    print("="*80)
    print(f"Base URL: {BASE_URL}")
    print(f"Credentials: {ADMIN_USERNAME}/{ADMIN_PASSWORD}")
    print("="*80)
    
    tests = [
        ("1. Auth - Login Valid", test_1_login_valid),
        ("2. Auth - Login Invalid (401)", test_2_login_invalid),
        ("3. Overview", test_3_overview),
        ("4. Tree - Jitter Field", test_4_tree_with_jitter),
        ("5. Target By ID - Jitter + GroupName", test_5_target_by_id_with_jitter),
        ("6. Series - Jitter in Points & Stats", test_6_series_with_jitter),
        ("7. Create Fractional Interval Target (0.5s)", test_7_create_fractional_interval_target),
        ("8. Verify Live Probing (~12s)", test_8_verify_live_probing),
        ("9. Update Interval to 0.25", test_9_update_interval_to_025),
        ("10. Min Interval Clamp (0.1 -> 0.25)", test_10_min_interval_clamp),
        ("11. Delete Fractional Target", test_11_delete_fractional_target),
        ("12. Alert Rules - 4 Rules + High Jitter", test_12_alert_rules_with_jitter),
        ("13. Toggle High Jitter Rule", test_13_toggle_high_jitter_rule),
        ("14. Get Alerts - Structure", test_14_get_alerts),
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
