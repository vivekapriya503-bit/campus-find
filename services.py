"""
CAMPUS-FIND: Business Logic & Multi-Database Services
Includes local heuristic AI matching, spam detection, hybrid workflow,
and atomic MySQL transactions.
"""

import re
import uuid
import random
import string
import datetime
from datetime import datetime as dt, timedelta
import db_mysql
import db_mongo


# ==============================================================================
# 1. AI-Style Heuristic Match Engine (Local, Transparent, No API keys required)
# ==============================================================================

def tokenize(text):
    """Simple lowercase alphanumeric word tokenizer."""
    if not text:
        return set()
    words = re.findall(r"\b[a-zA-Z0-9]{3,}\b", text.lower())
    # Strip common stop words
    stopwords = {"the", "and", "with", "for", "near", "from", "left", "found", "lost", "some", "this", "that"}
    return set(w for w in words if w not in stopwords)


def calculate_match_score(lost_item, found_item):
    """
    Compares a lost report with a found report.
    Returns: (score between 0.0 and 1.0, list_of_reasons)
    """
    score = 0.0
    reasons = []

    # Category matching (Weight: 0.35)
    lost_cat = (lost_item.get("category") or "").strip().lower()
    found_cat = (found_item.get("category") or "").strip().lower()
    if lost_cat and lost_cat == found_cat:
        score += 0.35
        reasons.append(f"Matching category '{lost_item.get('category')}'")
    else:
        # If categories clearly differ, match probability drops
        score -= 0.10

    # Location proximity (Weight: 0.25)
    lost_loc = lost_item.get("location", {})
    found_loc = found_item.get("location", {})
    lost_zone = (lost_loc.get("campus_zone") or "").strip().lower()
    found_zone = (found_loc.get("campus_zone") or "").strip().lower()
    lost_bldg = (lost_loc.get("building") or "").strip().lower()
    found_bldg = (found_loc.get("building") or "").strip().lower()

    if lost_zone and lost_zone == found_zone:
        score += 0.20
        reasons.append(f"Reported in same campus zone '{lost_loc.get('campus_zone')}'")
        if lost_bldg and lost_bldg == found_bldg:
            score += 0.05
            reasons.append(f"Identical building '{lost_loc.get('building')}'")

    # Brand and Color matching from nested_attributes (Weight: 0.20)
    lost_attrs = lost_item.get("nested_attributes", {})
    found_attrs = found_item.get("nested_attributes", {})
    lost_brand = (lost_attrs.get("brand") or "").strip().lower()
    found_brand = (found_attrs.get("brand") or "").strip().lower()
    lost_color = (lost_attrs.get("color") or "").strip().lower()
    found_color = (found_attrs.get("color") or "").strip().lower()

    if lost_brand and found_brand and (lost_brand in found_brand or found_brand in lost_brand):
        score += 0.12
        reasons.append(f"Matching brand '{lost_attrs.get('brand')}'")
    if lost_color and found_color and (lost_color in found_color or found_color in lost_color):
        score += 0.08
        reasons.append(f"Matching color '{lost_attrs.get('color')}'")

    # Text token overlap (Weight: 0.15)
    lost_text = f"{lost_item.get('title', '')} {lost_item.get('description', '')}"
    found_text = f"{found_item.get('title', '')} {found_item.get('description', '')}"
    tokens_lost = tokenize(lost_text)
    tokens_found = tokenize(found_text)
    if tokens_lost and tokens_found:
        intersection = tokens_lost.intersection(tokens_found)
        union = tokens_lost.union(tokens_found)
        jaccard = len(intersection) / len(union) if union else 0
        if jaccard > 0.15:
            overlap_score = min(0.15, jaccard * 0.4)
            score += overlap_score
            shared_words = ", ".join(list(intersection)[:3])
            reasons.append(f"Key descriptive words match: [{shared_words}]")

    # Date temporal proximity (Weight: 0.10)
    try:
        lost_d = lost_item.get("dates", {}).get("incident_date")
        found_d = found_item.get("dates", {}).get("incident_date")
        if lost_d and found_d:
            d1 = dt.strptime(lost_d[:10], "%Y-%m-%d")
            d2 = dt.strptime(found_d[:10], "%Y-%m-%d")
            diff_days = abs((d1 - d2).days)
            if diff_days <= 1:
                score += 0.10
                reasons.append("Reported within 24 hours of each other")
            elif diff_days <= 4:
                score += 0.05
                reasons.append(f"Reported within {diff_days} days")
    except Exception:
        pass

    final_score = max(0.0, min(0.99, round(score, 2)))
    explanation = "; ".join(reasons) if reasons else "General similarity in item characteristics."
    return final_score, explanation


def find_possible_matches_for_item(item_uuid):
    """
    Finds and explains potential matches for a given item by querying MongoDB
    for candidate counterparts and saving promising suggestions to MySQL.
    """
    target = db_mongo.find_item_by_uuid(item_uuid)
    if not target:
        return []

    target_type = target.get("report_type")
    counterpart_type = "found" if target_type == "lost" else "lost"

    candidates = db_mongo.query_items({
        "report_type": counterpart_type,
        "status": {"$in": ["open", "possible_match", "claimed"]}
    })
    matches = []

    for c in candidates:
        c.pop("_id", None)
        lost_obj = target if target_type == "lost" else c
        found_obj = c if target_type == "lost" else target

        score, explanation = calculate_match_score(lost_obj, found_obj)
        if score >= 0.45:  # threshold for a plausible candidate
            matches.append({
                "candidate": c,
                "confidence_score": score,
                "explanation": explanation,
                "confidence_percent": int(score * 100)
            })

    # Sort descending by confidence score
    matches.sort(key=lambda m: m["confidence_score"], reverse=True)
    return matches


# ==============================================================================
# 2. Duplicate & Spam Submission Detector
# ==============================================================================

def check_duplicate_or_spam(new_report_data):
    """
    Warns if an incoming report looks like a suspicious repeated submission.
    Checks recent reports in MongoDB in the same category and campus zone.
    """
    category = new_report_data.get("category")
    title = new_report_data.get("title", "")
    new_tokens = tokenize(title + " " + new_report_data.get("description", ""))

    existing_reports = db_mongo.query_items({
        "category": category,
        "report_type": new_report_data.get("report_type")
    }, limit=20)

    for ex in existing_reports:
        ex_tokens = tokenize(ex.get("title", "") + " " + ex.get("description", ""))
        if not new_tokens or not ex_tokens:
            continue
        intersection = new_tokens.intersection(ex_tokens)
        union = new_tokens.union(ex_tokens)
        similarity = len(intersection) / len(union) if union else 0

        if similarity >= 0.50:
            return {
                "is_duplicate_warning": True,
                "confidence": round(similarity, 2),
                "matched_uuid": ex.get("item_uuid"),
                "matched_title": ex.get("title"),
                "message": f"Warning: Highly similar report '{ex.get('title')}' already exists in {category}. Please avoid submitting duplicates."
            }

    return {"is_duplicate_warning": False, "message": "No duplicates detected."}


# ==============================================================================
# 3. Hybrid Workflow: Create Report & Sync Match Suggestions
# ==============================================================================

def create_item_report_workflow(report_dict):
    """
    Hybrid Workflow:
    1. Checks for spam / duplicate.
    2. Writes the flexible nested document to MongoDB.
    3. Triggers the AI match engine to discover counterparts.
    4. Writes discovered match suggestions and notifications to MySQL.
    """
    # 1. Spam check
    dup_check = check_duplicate_or_spam(report_dict)

    # 2. Insert to MongoDB
    item_uuid = report_dict.get("item_uuid")
    db_mongo.insert_item_report(report_dict)

    # 3. Find potential matches
    matches = find_possible_matches_for_item(item_uuid)
    
    # 4. Write high-confidence suggestions to MySQL
    for m in matches:
        if m["confidence_score"] >= 0.65:
            cand = m["candidate"]
            lost_uuid = item_uuid if report_dict.get("report_type") == "lost" else cand.get("item_uuid")
            found_uuid = cand.get("item_uuid") if report_dict.get("report_type") == "lost" else item_uuid
            
            try:
                sql = """
                INSERT INTO match_suggestions (lost_item_uuid, found_item_uuid, confidence_score, explanation, match_status)
                VALUES (%s, %s, %s, %s, 'suggested')
                """
                db_mysql.execute_write(sql, (lost_uuid, found_uuid, m["confidence_score"], m["explanation"]))
                
                # Update MongoDB items status to 'possible_match'
                db_mongo.update_item_status(lost_uuid, "possible_match")
                db_mongo.update_item_status(found_uuid, "possible_match")
            except Exception:
                # Pair might already exist in unique constraint
                pass

    return {
        "item_uuid": item_uuid,
        "duplicate_warning": dup_check,
        "match_count": len(matches),
        "top_match": matches[0] if matches else None
    }


# ==============================================================================
# 4. Private Claim Submission with Snapshot
# ==============================================================================

def submit_private_claim(item_uuid, claimant_id, private_verification_text):
    """
    Submits a private ownership claim on an item.
    - Saves an immutable snapshot of MongoDB item state to MySQL.
    - Secret identifying detail is saved in MySQL and NEVER exposed in public endpoints.
    - Creates a notification for campus moderators.
    """
    item = db_mongo.find_item_by_uuid(item_uuid, include_private_secret=False)
    if not item:
        raise ValueError("Item report not found")

    claim_uuid = f"clm-{uuid.uuid4().hex[:8]}"
    snapshot_title = item.get("title", "Untitled Item")
    snapshot_type = item.get("report_type", "unknown")
    snapshot_zone = item.get("location", {}).get("campus_zone", "General Campus")

    sql = """
    INSERT INTO claims (claim_uuid, item_uuid, claimant_id, claim_status, private_verification_text,
                        snapshot_item_title, snapshot_report_type, snapshot_location_zone)
    VALUES (%s, %s, %s, 'pending_review', %s, %s, %s, %s)
    """
    claim_id = db_mysql.execute_write(sql, (
        claim_uuid, item_uuid, claimant_id, private_verification_text,
        snapshot_title, snapshot_type, snapshot_zone
    ))

    # Notify campus moderators
    try:
        mod_rows = db_mysql.execute_query("SELECT id FROM users WHERE role = 'moderator' LIMIT 1")
        if mod_rows:
            mod_id = mod_rows[0]["id"]
            db_mysql.execute_write(
                "INSERT INTO notifications (user_id, title, message, notification_type, reference_uuid) VALUES (%s, %s, %s, %s, %s)",
                (mod_id, "New Claim Awaiting Review", f"A private claim was submitted for '{snapshot_title}'. Verify hidden detail.", "moderation", claim_uuid)
            )
    except Exception:
        pass

    return {
        "claim_id": claim_id,
        "claim_uuid": claim_uuid,
        "status": "pending_review",
        "snapshot_title": snapshot_title
    }


# ==============================================================================
# 5. MySQL ACID Multi-Row Transaction: Claim Approval & Safe Return Handoff
# ==============================================================================

def generate_handoff_token():
    """Generates a secure, human-readable 6-character return code."""
    chars = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    token = "".join(random.choice(chars) for _ in range(6))
    return f"CF-{token}"


def approve_claim_transaction(claim_id, moderator_id, reviewer_notes=None):
    """
    Demonstrates a complete relational MySQL transaction:
    Atomically:
      1. Updates claim status to 'approved' and records reviewer notes.
      2. Generates and inserts a safe handoff record with a one-time handoff code.
      3. Inserts a student notification with the handoff code.
    Then synchronizes status with MongoDB:
      4. Updates MongoDB item report status to 'claimed'.
    """
    # Fetch claim details
    claims = db_mysql.execute_query("SELECT * FROM claims WHERE id = %s", (claim_id,))
    if not claims:
        raise ValueError("Claim record not found")
    claim = claims[0]
    item_uuid = claim["item_uuid"]
    claimant_id = claim["claimant_id"]
    item_title = claim["snapshot_item_title"]

    handoff_code = generate_handoff_token()
    notes = reviewer_notes or "Ownership verified through distinctive secret mark."

    # Define atomic SQL operations
    operations = [
        # Op 1: Update claim
        (
            "UPDATE claims SET claim_status = %s, reviewed_by = %s, reviewer_notes = %s WHERE id = %s",
            ("approved", moderator_id, notes, claim_id)
        ),
        # Op 2: Insert handoff token
        (
            """INSERT INTO handoffs (handoff_code, claim_id, item_uuid, pickup_location, scheduled_window, status, moderator_id)
               VALUES (%s, %s, %s, %s, %s, 'scheduled', %s)""",
            (handoff_code, claim_id, item_uuid, "Student Center Lost & Found Desk (Room 102)", "Mon-Fri 9:00 AM - 5:00 PM", moderator_id)
        ),
        # Op 3: Insert student notification
        (
            """INSERT INTO notifications (user_id, title, message, notification_type, reference_uuid)
               VALUES (%s, %s, %s, %s, %s)""",
            (
                claimant_id,
                "Claim Approved - Handoff Code Issued",
                f"Your claim for '{item_title}' is approved! Bring student ID & pickup code {handoff_code} to Room 102.",
                "handoff_ready",
                claim["claim_uuid"]
            )
        )
    ]

    # Execute atomic MySQL transaction
    db_mysql.execute_transaction(operations)

    # Cross-database update: MongoDB item status
    db_mongo.update_item_status(item_uuid, "claimed")

    return {
        "claim_id": claim_id,
        "status": "approved",
        "handoff_code": handoff_code,
        "pickup_location": "Student Center Lost & Found Desk (Room 102)"
    }


def complete_handoff_verification(handoff_code, moderator_id):
    """
    Desk Verification:
    Moderator enters the claimant's one-time code to confirm physical handoff.
    Updates MySQL handoff record to 'completed' and MongoDB item report to 'returned'.
    """
    code = handoff_code.strip().upper()
    rows = db_mysql.execute_query("SELECT * FROM handoffs WHERE handoff_code = %s", (code,))
    if not rows:
        return {"success": False, "message": "Invalid handoff code. Please re-check the student receipt."}

    handoff = rows[0]
    if handoff["status"] == "completed":
        return {"success": False, "message": "This handoff code was already completed and redeemed."}

    # Atomic MySQL update
    now = dt.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    db_mysql.execute_write(
        "UPDATE handoffs SET status = 'completed', completed_at = %s, moderator_id = %s WHERE id = %s",
        (now, moderator_id, handoff["id"])
    )

    # Update MongoDB report to 'returned'
    db_mongo.update_item_status(handoff["item_uuid"], "returned")

    return {
        "success": True,
        "message": f"Handoff {code} confirmed! Item successfully returned to verified student.",
        "item_uuid": handoff["item_uuid"]
    }


# ==============================================================================
# 6. Moderator Aging Review (Unclaimed-Item Reminders)
# ==============================================================================

def get_unclaimed_aging_reports(days_threshold=30):
    """
    Identifies found reports older than 30 days that remain open or unclaimed,
    assisting moderators in deciding on campus donation or disposition.
    """
    cutoff_date = (dt.utcnow() - timedelta(days=days_threshold)).strftime("%Y-%m-%d")
    all_found = db_mongo.query_items({"report_type": "found", "status": {"$in": ["open", "possible_match"]}})

    aging_items = []
    for item in all_found:
        incident_date = item.get("dates", {}).get("incident_date", "")
        if incident_date and incident_date < cutoff_date:
            aging_items.append(item)

    return aging_items
