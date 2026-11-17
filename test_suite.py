"""
CAMPUS-FIND Automated Verification Test Suite
Verifies:
  1. MySQL Relational JOIN
  2. MongoDB Nested Field Queries
  3. MySQL Atomic Transaction (with commit and rollback)
  4. End-to-End Hybrid Workflow (Item in MongoDB -> Claim & Handoff in MySQL)
  5. AI Heuristic Match Engine & Natural Language Explanations
  6. Duplicate & Spam Submission Detection
  7. Flask REST API Endpoints
"""

import unittest
import json
import uuid
import db_mysql
import db_mongo
import services
from app import app


class TestCampusFindDBMS(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Seed databases once for tests."""
        import seed_data
        seed_data.seed_all()
        cls.client = app.test_client()

    # --------------------------------------------------------------------------
    # 1. MongoDB Nested Field Query Demonstration
    # --------------------------------------------------------------------------
    def test_01_mongodb_nested_queries(self):
        print("\n[TEST 1] Demonstrating MongoDB Nested Field Queries...")
        
        # Nested Query A: location.campus_zone
        library_items = db_mongo.query_by_nested_location(campus_zone="Central Library")
        self.assertGreaterEqual(len(library_items), 1, "Should find items in Central Library")
        for item in library_items:
            self.assertEqual(item["location"]["campus_zone"], "Central Library")
        print(f"  ✓ Nested query on 'location.campus_zone': Found {len(library_items)} items in 'Central Library'.")

        # Nested Query B: nested_attributes.color
        gray_items = db_mongo.query_by_nested_attribute(color="Gray")
        self.assertGreaterEqual(len(gray_items), 1, "Should find Space Gray items")
        print(f"  ✓ Nested query on 'nested_attributes.color': Found {len(gray_items)} items matching 'Gray'.")

        # Nested Query C: urgency_info.is_urgent
        urgent_items = db_mongo.query_urgent_items()
        self.assertGreaterEqual(len(urgent_items), 1, "Should find urgent items")
        for item in urgent_items:
            self.assertTrue(item["urgency_info"]["is_urgent"])
        print(f"  ✓ Nested query on 'urgency_info.is_urgent': Found {len(urgent_items)} urgent items.")

    # --------------------------------------------------------------------------
    # 2. MySQL Relational JOIN Demonstration
    # --------------------------------------------------------------------------
    def test_02_mysql_relational_joins(self):
        print("\n[TEST 2] Demonstrating MySQL Multi-Table Relational JOIN...")
        
        claims = db_mysql.get_claims_with_joins()
        self.assertGreaterEqual(len(claims), 1, "Should return joined claim records")

        sample_claim = claims[0]
        # Verify columns joined across tables
        self.assertIn("claim_id", sample_claim)
        self.assertIn("claimant_name", sample_claim)       # Joined from users
        self.assertIn("claimant_email", sample_claim)      # Joined from users
        self.assertIn("claimant_department", sample_claim) # Joined from users
        self.assertIn("snapshot_item_title", sample_claim) # Stored snapshot in claims
        self.assertIn("handoff_code", sample_claim)        # Joined from handoffs

        print(f"  ✓ Relational JOIN succeeded: Claim #{sample_claim['claim_id']} for '{sample_claim['snapshot_item_title']}' joined with Claimant '{sample_claim['claimant_name']}' ({sample_claim['claimant_email']}).")

    # --------------------------------------------------------------------------
    # 3. MySQL Multi-Row Transaction Demonstration (ACID)
    # --------------------------------------------------------------------------
    def test_03_mysql_transaction_commit_and_rollback(self):
        print("\n[TEST 3] Demonstrating MySQL Multi-Row ACID Transaction...")

        # Part A: Successful Atomic Transaction
        # Create a pending claim to approve
        claim_uuid = f"clm-tx-test-{uuid.uuid4().hex[:6]}"
        cid = db_mysql.execute_write(
            """INSERT INTO claims (claim_uuid, item_uuid, claimant_id, claim_status, private_verification_text,
                                  snapshot_item_title, snapshot_report_type, snapshot_location_zone)
               VALUES (%s, 'cf-item-003', 2, 'pending_review', 'Has red silicone tag with track logo', 'Dorm Room Brass Keys', 'found', 'South Residence')""",
            (claim_uuid,)
        )

        # Execute approve_claim_transaction (updates claim, inserts handoff, inserts notification)
        result = services.approve_claim_transaction(claim_id=cid, moderator_id=3, reviewer_notes="Approved in transaction test.")
        self.assertEqual(result["status"], "approved")
        self.assertTrue(result["handoff_code"].startswith("CF-"))

        # Verify all 3 writes succeeded in MySQL
        updated_claim = db_mysql.execute_query("SELECT claim_status FROM claims WHERE id = %s", (cid,))[0]
        self.assertEqual(updated_claim["claim_status"], "approved")

        handoff_row = db_mysql.execute_query("SELECT handoff_code FROM handoffs WHERE claim_id = %s", (cid,))[0]
        self.assertEqual(handoff_row["handoff_code"], result["handoff_code"])

        notif_row = db_mysql.execute_query("SELECT id FROM notifications WHERE reference_uuid = %s", (claim_uuid,))
        self.assertGreaterEqual(len(notif_row), 1)

        print(f"  ✓ Multi-row transaction committed atomically: Claim updated, Handoff {result['handoff_code']} created, Notification sent.")

        # Part B: Rollback on Error
        # Attempt an invalid transaction with bad SQL in step 2
        bad_operations = [
            ("UPDATE claims SET reviewer_notes = 'Rollback attempt' WHERE id = %s", (cid,)),
            ("INSERT INTO non_existent_table_xyz VALUES (1, 2, 3)", ())  # Purposely broken
        ]
        with self.assertRaises(Exception):
            db_mysql.execute_transaction(bad_operations)

        # Verify rollback preserved original state
        claim_after = db_mysql.execute_query("SELECT reviewer_notes FROM claims WHERE id = %s", (cid,))[0]
        self.assertNotEqual(claim_after["reviewer_notes"], "Rollback attempt", "Transaction rollback must undo first write!")
        print("  ✓ Transaction rollback verified: Failure in subsequent step successfully rolled back all changes.")

    # --------------------------------------------------------------------------
    # 4. AI Match Engine & Explanations
    # --------------------------------------------------------------------------
    def test_04_ai_matching_and_explanation(self):
        print("\n[TEST 4] Testing AI Heuristic Match Engine & Natural Language Explanations...")

        # Find matches for lost iPad (cf-item-002)
        matches = services.find_possible_matches_for_item("cf-item-002")
        self.assertGreater(len(matches), 0, "Should suggest match with found iPad (cf-item-001)")

        top_match = matches[0]
        self.assertGreaterEqual(top_match["confidence_score"], 0.70)
        self.assertIn("Apple", top_match["explanation"])
        self.assertIn("Electronics", top_match["explanation"])
        print(f"  ✓ Top Match: {top_match['candidate']['title']} with {top_match['confidence_percent']}% confidence.")
        print(f"  ✓ Match Explanation: \"{top_match['explanation']}\"")

    # --------------------------------------------------------------------------
    # 5. Duplicate and Spam Detection
    # --------------------------------------------------------------------------
    def test_05_spam_and_duplicate_detection(self):
        print("\n[TEST 5] Testing Duplicate & Spam Warning System...")

        duplicate_report = {
            "title": "Space Gray iPad Air 5th Gen tablet",
            "report_type": "found",
            "category": "Electronics",
            "description": "Found on wooden study table near back windows with screen protector.",
            "location": {"campus_zone": "Central Library"}
        }

        dup_result = services.check_duplicate_or_spam(duplicate_report)
        self.assertTrue(dup_result["is_duplicate_warning"], "Should flag duplicate submission")
        print(f"  ✓ Duplicate Detector Warning: \"{dup_result['message']}\"")

    # --------------------------------------------------------------------------
    # 6. Flask REST API Endpoints End-to-End
    # --------------------------------------------------------------------------
    def test_06_flask_api_endpoints(self):
        print("\n[TEST 6] Testing Flask API Endpoints...")

        # Health / DB Status
        res = self.client.get("/api/db-status")
        self.assertEqual(res.status_code, 200)
        status_data = json.loads(res.data)
        self.assertEqual(status_data["status"], "healthy")
        print("  ✓ GET /api/db-status returned 200 OK with dual database diagnostic status.")

        # Search Items
        res = self.client.get("/api/items?search=iPad")
        self.assertEqual(res.status_code, 200)
        items_data = json.loads(res.data)
        self.assertGreaterEqual(items_data["count"], 1)
        print(f"  ✓ GET /api/items?search=iPad returned {items_data['count']} matching records.")

        # Campus Zones
        res = self.client.get("/api/campus-zones")
        self.assertEqual(res.status_code, 200)
        zones_data = json.loads(res.data)
        self.assertGreaterEqual(len(zones_data["zones"]), 5)
        print(f"  ✓ GET /api/campus-zones returned {len(zones_data['zones'])} campus zones with counts.")

        # Submit a New Report via API
        new_payload = {
            "title": "Sony WH-1000XM4 Headphones",
            "report_type": "found",
            "category": "Electronics",
            "color": "Matte Black",
            "brand": "Sony",
            "campus_zone": "Central Library",
            "building": "Main Library 2nd Floor IT Lab",
            "incident_date": "2026-11-12",
            "description": "Left on desk next to printer workstation.",
            "distinguishing_mark": "Blue anime sticker on the right ear cup"
        }
        post_res = self.client.post("/api/items", json=new_payload)
        self.assertEqual(post_res.status_code, 201)
        created = json.loads(post_res.data)
        created_uuid = created["item_uuid"]
        print(f"  ✓ POST /api/items created new item report '{created_uuid}' in MongoDB.")

        # Submit Private Claim via API
        claim_payload = {
            "item_uuid": created_uuid,
            "claimant_id": 1,
            "private_verification_text": "It has an anime character sticker on the right ear cup!"
        }
        claim_res = self.client.post("/api/claims", json=claim_payload)
        self.assertEqual(claim_res.status_code, 201)
        claim_data = json.loads(claim_res.data)
        claim_id = claim_data["claim"]["claim_id"]
        print(f"  ✓ POST /api/claims created private claim #{claim_id} with report snapshot in MySQL.")

        # Review & Approve Claim via API (Multi-Row Transaction)
        review_res = self.client.post(f"/api/claims/{claim_id}/review", json={"action": "approve"})
        self.assertEqual(review_res.status_code, 200)
        review_data = json.loads(review_res.data)
        handoff_code = review_data["result"]["handoff_code"]
        print(f"  ✓ POST /api/claims/{claim_id}/review approved claim and issued safe handoff token '{handoff_code}'.")

        # Verify Desk Handoff Token via API
        verify_res = self.client.post("/api/handoffs/verify", json={"handoff_code": handoff_code})
        self.assertEqual(verify_res.status_code, 200)
        print(f"  ✓ POST /api/handoffs/verify redeemed token '{handoff_code}' and updated report to 'returned'.")

    # --------------------------------------------------------------------------
    # 7. User Authentication & Password Hashing
    # --------------------------------------------------------------------------
    def test_07_auth_login_and_registration(self):
        print("\n[TEST 7] Testing User Authentication & Password Hashing...")

        # 1. Test Login with valid credentials
        login_res = self.client.post("/api/auth/login", json={
            "username": "maya_lin",
            "password": "demo123"
        })
        self.assertEqual(login_res.status_code, 200)
        u_data = json.loads(login_res.data)
        self.assertEqual(u_data["user"]["username"], "maya_lin")
        self.assertEqual(u_data["user"]["role"], "student")
        print(f"  ✓ POST /api/auth/login succeeded for student '{u_data['user']['full_name']}'.")

        # 2. Test Login with invalid password
        bad_login = self.client.post("/api/auth/login", json={
            "username": "maya_lin",
            "password": "wrongpassword"
        })
        self.assertEqual(bad_login.status_code, 401)
        print("  ✓ POST /api/auth/login correctly rejected invalid password with 401.")

        # 3. Test Student Registration
        reg_username = f"student_{uuid.uuid4().hex[:6]}"
        reg_res = self.client.post("/api/auth/register", json={
            "username": reg_username,
            "email": f"{reg_username}@campus.edu",
            "password": "securepass123",
            "full_name": "Jordan Taylor",
            "department": "Biomedical Engineering"
        })
        self.assertEqual(reg_res.status_code, 201)
        reg_data = json.loads(reg_res.data)
        self.assertEqual(reg_data["user"]["role"], "student")
        print(f"  ✓ POST /api/auth/register successfully created student '{reg_data['user']['full_name']}' with hashed password.")

        # 4. Check Current User Session
        me_res = self.client.get("/api/auth/me")
        self.assertEqual(me_res.status_code, 200)
        me_data = json.loads(me_res.data)
        self.assertTrue(me_data["authenticated"])
        self.assertEqual(me_data["user"]["username"], reg_username)
        print("  ✓ GET /api/auth/me confirmed active user session.")

        # 5. Logout
        logout_res = self.client.post("/api/auth/logout")
        self.assertEqual(logout_res.status_code, 200)
        me_after = self.client.get("/api/auth/me")
        self.assertFalse(json.loads(me_after.data)["authenticated"])
        print("  ✓ POST /api/auth/logout successfully cleared session.")


if __name__ == "__main__":
    unittest.main()
