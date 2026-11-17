"""
CAMPUS-FIND: Database Seeder
Populates both MySQL and MongoDB with rich fictional campus items, users, claims, and handoffs.
"""

import os
import json
import uuid
from werkzeug.security import generate_password_hash
import db_mysql
import db_mongo

SAMPLE_JSON_PATH = os.path.join(os.path.dirname(__file__), "database", "sample_item_reports.json")


def seed_mongodb():
    """Populates MongoDB 'item_reports' collection with sample documents."""
    coll = db_mongo.get_items_collection()
    existing_count = coll.count_documents({})
    if existing_count > 0:
        print(f"[MongoDB] Already seeded with {existing_count} items. Refreshing...")
        coll.delete_many({})

    if not os.path.exists(SAMPLE_JSON_PATH):
        print(f"[MongoDB] Warning: {SAMPLE_JSON_PATH} not found.")
        return 0

    with open(SAMPLE_JSON_PATH, "r", encoding="utf-8") as f:
        items = json.load(f)

    for item in items:
        # Generate a private secret detail for demo validation
        if item.get("nested_attributes", {}).get("distinguishing_mark"):
            item["private_secret_detail"] = item["nested_attributes"]["distinguishing_mark"]
        db_mongo.insert_item_report(item)

    print(f"[MongoDB] Successfully inserted {len(items)} nested item reports.")
    return len(items)


def seed_mysql():
    """Populates MySQL relational tables with users, claims, match suggestions, notifications, and handoffs."""
    # 1. Clean existing records in child-to-parent order
    for tbl in ["handoffs", "notifications", "match_suggestions", "claims", "users"]:
        try:
            db_mysql.execute_write(f"DELETE FROM {tbl}")
        except Exception:
            pass
    try:
        db_mysql.execute_write("DELETE FROM sqlite_sequence")
    except Exception:
        pass

    # 2. Seed Users
    default_pw = generate_password_hash("demo123", method="pbkdf2:sha256")
    users_data = [
        (1, "usr-student-001", "maya_lin", "maya.lin@campus.edu", default_pw, "Maya Lin", "student", "Computer Science", "***-***-4921"),
        (2, "usr-student-002", "alex_chen", "alex.chen@campus.edu", default_pw, "Alex Chen", "student", "Mechanical Eng", "***-***-8832"),
        (3, "usr-mod-001", "sarah_safety", "safety.office@campus.edu", default_pw, "Officer Sarah Jenkins", "moderator", "Campus Safety & Desk", "***-***-1100"),
        (4, "usr-admin-001", "dean_affairs", "affairs.admin@campus.edu", default_pw, "Dr. Evelyn Reed", "admin", "Dean of Students Office", "***-***-9999")
    ]

    for u in users_data:
        sql = """
        INSERT INTO users (id, user_uuid, username, email, password_hash, full_name, role, department, phone_masked)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        db_mysql.execute_write(sql, u)
    print(f"[MySQL] Inserted {len(users_data)} users.")

    # 3. Seed Claims (linking to cf-item-001 and cf-item-003 in MongoDB)
    claims_data = [
        (
            "clm-8821a", "cf-item-001", 1, "approved",
            "Scratch shaped like letter V near charging port; lockscreen has a golden retriever puppy.",
            "Space Gray iPad Air 5th Gen", "found", "Central Library",
            "Verified in person with student ID card. Screen wallpaper matches description.", 3
        ),
        (
            "clm-9943b", "cf-item-003", 2, "pending_review",
            "Has a red silicone key fob with the logo of North High Track & Field 2022.",
            "Dorm Room Brass Keys with Lanyard", "found", "South Residence",
            None, None
        )
    ]

    claim_ids = []
    for c in claims_data:
        sql = """
        INSERT INTO claims (claim_uuid, item_uuid, claimant_id, claim_status, private_verification_text,
                            snapshot_item_title, snapshot_report_type, snapshot_location_zone, reviewer_notes, reviewed_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cid = db_mysql.execute_write(sql, c)
        claim_ids.append(cid)
    print(f"[MySQL] Inserted {len(claims_data)} claims with report snapshots.")

    # 4. Seed Match Suggestions
    matches_data = [
        ("cf-item-002", "cf-item-001", 0.92, "Same category (Electronics), matching brand (Apple), matching color (Space Gray), and reported near Central Library within 14 hours.", "suggested"),
        ("cf-item-004", "cf-item-003", 0.88, "Matching category (Keys & Bags), building proximity (South Residence Hall B), and incident timestamp matches within 6 hours.", "suggested")
    ]
    for m in matches_data:
        sql = """
        INSERT INTO match_suggestions (lost_item_uuid, found_item_uuid, confidence_score, explanation, match_status)
        VALUES (%s, %s, %s, %s, %s)
        """
        db_mysql.execute_write(sql, m)
    print(f"[MySQL] Inserted {len(matches_data)} match suggestions.")

    # 5. Seed Notifications
    notifications_data = [
        (1, "Claim Approved & Return Ready", "Your claim for 'Space Gray iPad Air 5th Gen' was verified by Officer Jenkins. One-time handoff code: CF-7A9B2C.", "handoff_ready", "clm-8821a", 0),
        (2, "Promising Match Found", "A found report matching your lost dorm keys was logged in South Residence. Check possible matches!", "match_found", "cf-item-004", 0),
        (3, "Urgent Item Review Needed", "An urgent item (Prescription Glasses needed for exams) was reported in Science Complex.", "urgency_alert", "cf-item-005", 0)
    ]
    for n in notifications_data:
        sql = """
        INSERT INTO notifications (user_id, title, message, notification_type, reference_uuid, is_read)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        db_mysql.execute_write(sql, n)
    print(f"[MySQL] Inserted {len(notifications_data)} notifications.")

    # 6. Seed Handoffs
    handoffs_data = [
        ("CF-7A9B2C", claim_ids[0], "cf-item-001", "Student Center Lost & Found Desk (Room 102)", "Mon-Fri 9:00 AM - 5:00 PM", "completed", 3),
        ("CF-3D8E1F", claim_ids[1], "cf-item-003", "South Quad Security Station (Bldg C Lobby)", "Available 24/7 with Student ID", "scheduled", 3)
    ]
    for h in handoffs_data:
        sql = """
        INSERT INTO handoffs (handoff_code, claim_id, item_uuid, pickup_location, scheduled_window, status, moderator_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        db_mysql.execute_write(sql, h)
    print(f"[MySQL] Inserted {len(handoffs_data)} safe handoff tokens.")


def seed_all():
    """Seeds both databases."""
    print("--- Seeding CAMPUS-FIND Databases ---")
    m_count = seed_mongodb()
    seed_mysql()
    print("--- Seeding Complete ---")
    return m_count


if __name__ == "__main__":
    seed_all()
