"""
CAMPUS-FIND: Smart Lost & Found Management System
Flask Backend Application serving single-page frontend and API endpoints.
"""

import os
import uuid
import datetime
from datetime import datetime as dt
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

import db_mysql
import db_mongo
import services
import seed_data

load_dotenv()

app = Flask(__name__, template_folder="templates")
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "campus-find-secret-dev-2026")
app.config["JSON_SORT_KEYS"] = False


# ==============================================================================
# Initialization & Startup Hook
# ==============================================================================

@app.before_request
def ensure_seed_on_first_request():
    """Seeds initial sample data if the document collection is empty."""
    if not getattr(app, "_seeded", False):
        try:
            coll = db_mongo.get_items_collection()
            if coll.count_documents({}) == 0:
                print("[CAMPUS-FIND] Empty database detected. Auto-seeding sample campus items...")
                seed_data.seed_all()
            app._seeded = True
        except Exception as e:
            print(f"[CAMPUS-FIND] Startup check notice: {e}")


# ==============================================================================
# Frontend Route
# ==============================================================================

@app.route("/")
def index():
    """Serves the single-page responsive application."""
    return render_template("index.html")


# ==============================================================================
# Health & Dual Database Diagnostics APIs
# ==============================================================================

@app.route("/api/health")
@app.route("/api/db-status")
def db_status():
    """
    Returns real-time diagnostic status for both MySQL and MongoDB engines.
    Demonstrates independence of connections and resilience handling.
    """
    mysql_info = db_mysql.get_mysql_status()
    mongo_info = db_mongo.get_mongo_status()

    return jsonify({
        "status": "healthy",
        "timestamp": dt.utcnow().isoformat() + "Z",
        "databases": {
            "mysql": mysql_info,
            "mongodb": mongo_info
        },
        "resilience_mode": os.getenv("RESILIENCE_MODE", "auto")
    })


# ==============================================================================
# Authentication & User Management APIs
# ==============================================================================

def get_current_user():
    """Returns currently authenticated user dict from session, or None."""
    user_id = session.get("user_id")
    if not user_id:
        return None
    rows = db_mysql.execute_query(
        "SELECT id, user_uuid, username, email, full_name, role, department, phone_masked FROM users WHERE id = %s",
        (user_id,)
    )
    return rows[0] if rows else None


@app.route("/api/auth/me", methods=["GET"])
def auth_me():
    """Returns the currently logged-in user or null."""
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None})
    return jsonify({"authenticated": True, "user": user})


@app.route("/api/auth/demo-users", methods=["GET"])
def auth_demo_users():
    """Returns the seed personas for 1-click role testing in demos and evaluations."""
    rows = db_mysql.execute_query(
        "SELECT id, user_uuid, username, email, full_name, role, department FROM users ORDER BY id ASC"
    )
    return jsonify({"users": rows})


@app.route("/api/auth/login", methods=["POST"])
def auth_login():
    """
    Authenticates student or staff member.
    Verifies password using werkzeug.security check_password_hash.
    """
    data = request.get_json() or {}
    identifier = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()

    if not identifier or not password:
        return jsonify({"error": "Username/Email and password are required."}), 400

    rows = db_mysql.execute_query(
        "SELECT * FROM users WHERE username = %s OR email = %s",
        (identifier, identifier)
    )
    if not rows:
        return jsonify({"error": "Account not found. Please check username/email or register."}), 404

    user = rows[0]
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": "Invalid password. (Default demo accounts use password: 'demo123')"}), 401

    session["user_id"] = user["id"]
    session["user_role"] = user["role"]
    session["username"] = user["username"]

    safe_user = {
        "id": user["id"],
        "user_uuid": user["user_uuid"],
        "username": user["username"],
        "email": user["email"],
        "full_name": user["full_name"],
        "role": user["role"],
        "department": user["department"],
        "phone_masked": user.get("phone_masked")
    }

    return jsonify({
        "message": f"Welcome back, {safe_user['full_name']}!",
        "user": safe_user
    })


@app.route("/api/auth/register", methods=["POST"])
def auth_register():
    """
    Registers a new student user account with securely hashed password.
    """
    data = request.get_json() or {}
    username = (data.get("username") or "").strip().lower()
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()
    full_name = (data.get("full_name") or "").strip()
    department = (data.get("department") or "General Campus").strip()
    phone = (data.get("phone") or "***-***-0000").strip()

    if not username or len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters."}), 400
    if not email or "@" not in email:
        return jsonify({"error": "Valid campus email is required."}), 400
    if not password or len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters."}), 400
    if not full_name:
        return jsonify({"error": "Full name is required."}), 400

    existing = db_mysql.execute_query(
        "SELECT id FROM users WHERE username = %s OR email = %s",
        (username, email)
    )
    if existing:
        return jsonify({"error": "An account with that username or email already exists."}), 409

    new_user_uuid = f"usr-student-{uuid.uuid4().hex[:8]}"
    hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")

    sql = """
    INSERT INTO users (user_uuid, username, email, password_hash, full_name, role, department, phone_masked)
    VALUES (%s, %s, %s, %s, %s, 'student', %s, %s)
    """
    new_id = db_mysql.execute_write(sql, (
        new_user_uuid, username, email, hashed_pw, full_name, department, phone
    ))

    session["user_id"] = new_id
    session["user_role"] = "student"
    session["username"] = username

    user_info = {
        "id": new_id,
        "user_uuid": new_user_uuid,
        "username": username,
        "email": email,
        "full_name": full_name,
        "role": "student",
        "department": department,
        "phone_masked": phone
    }

    return jsonify({
        "message": f"Account registered successfully! Welcome to CAMPUS-FIND, {full_name}.",
        "user": user_info
    }), 201


@app.route("/api/auth/logout", methods=["POST"])
def auth_logout():
    """Logs out the current session."""
    session.clear()
    return jsonify({"message": "Successfully signed out."})


# ==============================================================================
# Item Reports APIs (MongoDB Document Operations)
# ==============================================================================

@app.route("/api/items", methods=["GET"])
def get_items():
    """
    Search and filter item reports.
    Supports query parameters:
      - search: natural language or keyword search
      - category: filter by campus category
      - campus_zone: filter by campus location zone
      - report_type: 'lost' | 'found' | 'all'
      - status: 'open' | 'possible_match' | 'claimed' | 'returned' | 'closed'
      - urgent_only: 'true' | 'false'
    """
    search_q = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()
    campus_zone = request.args.get("campus_zone", "").strip()
    report_type = request.args.get("report_type", "all").strip().lower()
    status = request.args.get("status", "").strip()
    urgent_only = request.args.get("urgent_only", "false").lower() == "true"

    mongo_filter = {}

    if report_type in ["lost", "found"]:
        mongo_filter["report_type"] = report_type

    if category and category != "all":
        mongo_filter["category"] = category

    if campus_zone and campus_zone != "all":
        mongo_filter["location.campus_zone"] = campus_zone

    if status and status != "all":
        mongo_filter["status"] = status

    if urgent_only:
        mongo_filter["urgency_info.is_urgent"] = True

    # Natural-language text search
    if search_q:
        search_regex = {"$regex": search_q, "$options": "i"}
        mongo_filter["$or"] = [
            {"title": search_regex},
            {"description": search_regex},
            {"category": search_regex},
            {"location.building": search_regex},
            {"location.campus_zone": search_regex},
            {"nested_attributes.color": search_regex},
            {"nested_attributes.brand": search_regex}
        ]

    items = db_mongo.query_items(mongo_filter, limit=100)
    return jsonify({
        "count": len(items),
        "items": items
    })


@app.route("/api/items/<item_uuid>", methods=["GET"])
def get_item_detail(item_uuid):
    """
    Fetches detailed report from MongoDB and merges active relational
    match suggestions, claims, and handoff state from MySQL using item_uuid.
    """
    item = db_mongo.find_item_by_uuid(item_uuid)
    if not item:
        return jsonify({"error": "Item not found"}), 404

    # Relational MySQL lookup for related claims
    claims = db_mysql.execute_query(
        "SELECT id, claim_uuid, claim_status, created_at, snapshot_item_title FROM claims WHERE item_uuid = %s",
        (item_uuid,)
    )

    # Relational MySQL lookup for related match suggestions
    matches = db_mysql.execute_query(
        """SELECT m.*, 
                  CASE WHEN m.lost_item_uuid = %s THEN m.found_item_uuid ELSE m.lost_item_uuid END AS counterpart_uuid
           FROM match_suggestions m
           WHERE m.lost_item_uuid = %s OR m.found_item_uuid = %s
           ORDER BY m.confidence_score DESC""",
        (item_uuid, item_uuid, item_uuid)
    )

    # Relational lookup for handoffs
    handoffs = db_mysql.execute_query(
        "SELECT handoff_code, status, pickup_location, scheduled_window FROM handoffs WHERE item_uuid = %s",
        (item_uuid,)
    )

    return jsonify({
        "item": item,
        "mysql_relations": {
            "claims": claims,
            "match_suggestions": matches,
            "handoffs": handoffs
        }
    })


@app.route("/api/items", methods=["POST"])
def create_item():
    """
    Submits a new Lost or Found item report.
    Demonstrates input validation, spam check, nested document insertion into MongoDB,
    and automatic AI match evaluation saving suggestions to MySQL.
    """
    data = request.get_json() or {}
    
    # Validation
    title = (data.get("title") or "").strip()
    report_type = (data.get("report_type") or "").strip().lower()
    category = (data.get("category") or "Other").strip()
    campus_zone = (data.get("campus_zone") or "General Campus").strip()
    building = (data.get("building") or "Campus Grounds").strip()
    description = (data.get("description") or "").strip()

    if not title:
        return jsonify({"error": "Item title is required."}), 400
    if report_type not in ["lost", "found"]:
        return jsonify({"error": "report_type must be 'lost' or 'found'."}), 400

    new_uuid = f"cf-item-{uuid.uuid4().hex[:8]}"
    now_iso = dt.utcnow().isoformat() + "Z"
    incident_date = data.get("incident_date") or dt.utcnow().strftime("%Y-%m-%d")

    # Build nested document for MongoDB
    doc = {
        "item_uuid": new_uuid,
        "report_type": report_type,
        "title": title,
        "category": category,
        "status": "open",
        "description": description,
        "nested_attributes": {
            "color": (data.get("color") or "").strip(),
            "brand": (data.get("brand") or "").strip(),
            "model": (data.get("model") or "").strip(),
            "distinguishing_mark": (data.get("distinguishing_mark") or "").strip(),
            "condition": (data.get("condition") or "Used").strip()
        },
        "location": {
            "campus_zone": campus_zone,
            "building": building,
            "floor": (data.get("floor") or "Ground Floor").strip(),
            "room_or_area": (data.get("room_or_area") or "").strip()
        },
        "urgency_info": {
            "is_urgent": bool(data.get("is_urgent", False)),
            "urgency_reason": (data.get("urgency_reason") or "").strip(),
            "is_perishable": bool(data.get("is_perishable", False))
        },
        "dates": {
            "incident_date": incident_date,
            "reported_at": now_iso
        },
        "reporter": {
            "user_uuid": data.get("reporter_uuid") or (get_current_user()["user_uuid"] if get_current_user() else "usr-student-001"),
            "display_name": data.get("reporter_name") or (get_current_user()["full_name"] if get_current_user() else "Maya Lin"),
            "role": (get_current_user()["role"] if get_current_user() else "student")
        },
        "private_secret_hint": (data.get("private_secret_hint") or "Describe any hidden detail or sticker").strip(),
        "photo_meta": {
            "has_photo": bool(data.get("image_url")),
            "image_url": (data.get("image_url") or "").strip()
        }
    }

    # Store private secret for claimant validation
    if doc["nested_attributes"]["distinguishing_mark"]:
        doc["private_secret_detail"] = doc["nested_attributes"]["distinguishing_mark"]

    # Execute Hybrid creation workflow
    workflow_result = services.create_item_report_workflow(doc)
    doc.pop("_id", None)
    if workflow_result.get("top_match") and "candidate" in workflow_result["top_match"]:
        workflow_result["top_match"]["candidate"].pop("_id", None)

    return jsonify({
        "message": f"Successfully published {report_type} report!",
        "item_uuid": new_uuid,
        "item": doc,
        "workflow": workflow_result
    }), 201


@app.route("/api/items/<item_uuid>/matches", methods=["GET"])
def get_item_matches(item_uuid):
    """
    Returns AI-style possible matches with detailed natural language explanations.
    """
    matches = services.find_possible_matches_for_item(item_uuid)
    return jsonify({
        "item_uuid": item_uuid,
        "total_candidates": len(matches),
        "matches": matches
    })


# ==============================================================================
# Claims & Safe Return APIs (MySQL Relational & Transaction Operations)
# ==============================================================================

@app.route("/api/claims", methods=["POST"])
def submit_claim():
    """
    Student submits a private claim with hidden proof detail.
    Takes a snapshot of MongoDB item state and writes to MySQL `claims`.
    """
    data = request.get_json() or {}
    item_uuid = data.get("item_uuid")
    curr_u = get_current_user()
    claimant_id = int(data.get("claimant_id") or (curr_u["id"] if curr_u else 1))
    secret_text = (data.get("private_verification_text") or "").strip()

    if not item_uuid:
        return jsonify({"error": "item_uuid is required"}), 400
    if not secret_text:
        return jsonify({"error": "Private verification text (hidden identifying detail) is required."}), 400

    try:
        result = services.submit_private_claim(item_uuid, claimant_id, secret_text)
        return jsonify({
            "message": "Private claim submitted for moderator review. Details are secured and kept private.",
            "claim": result
        }), 201
    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        return jsonify({"error": f"Failed to submit claim: {e}"}), 500


@app.route("/api/claims", methods=["GET"])
def list_claims():
    """
    Demonstrates a MySQL JOIN:
    Fetches claims joined with claimant info, reviewer info, and handoff token.
    Used by Moderator review queue.
    """
    status_filter = request.args.get("status")
    claims = db_mysql.get_claims_with_joins(status_filter)
    return jsonify({
        "count": len(claims),
        "claims": claims
    })


@app.route("/api/claims/<int:claim_id>/review", methods=["POST"])
def review_claim(claim_id):
    """
    Demonstrates MySQL multi-row ACID transaction:
    Approves or rejects a claim.
    If approved:
      1. Updates claim status.
      2. Inserts handoff token (CF-XXXXXX).
      3. Inserts student notification.
      4. Updates MongoDB item report status to 'claimed'.
    """
    data = request.get_json() or {}
    action = data.get("action", "").lower()
    notes = data.get("notes", "")
    curr_u = get_current_user()
    moderator_id = int(data.get("moderator_id") or (curr_u["id"] if curr_u and curr_u.get("role") in ["moderator", "admin"] else 3))

    if action not in ["approve", "reject"]:
        return jsonify({"error": "action must be 'approve' or 'reject'"}), 400

    if action == "approve":
        try:
            res = services.approve_claim_transaction(claim_id, moderator_id, notes)
            return jsonify({
                "message": "Claim approved via atomic MySQL transaction! Safe return code issued.",
                "result": res
            })
        except Exception as e:
            return jsonify({"error": f"Transaction failed and was rolled back: {e}"}), 500
    else:
        # Rejection
        db_mysql.execute_write(
            "UPDATE claims SET claim_status = 'rejected', reviewed_by = %s, reviewer_notes = %s WHERE id = %s",
            (moderator_id, notes or "Details did not match item characteristics.", claim_id)
        )
        return jsonify({"message": "Claim has been marked as rejected."})


@app.route("/api/handoffs/verify", methods=["POST"])
def verify_handoff_code():
    """
    Safe Return Verification:
    Moderator enters the claimant's one-time code to complete return at campus desk.
    """
    data = request.get_json() or {}
    code = (data.get("handoff_code") or "").strip()
    curr_u = get_current_user()
    moderator_id = int(data.get("moderator_id") or (curr_u["id"] if curr_u and curr_u.get("role") in ["moderator", "admin"] else 3))

    if not code:
        return jsonify({"error": "Handoff code is required"}), 400

    result = services.complete_handoff_verification(code, moderator_id)
    if not result.get("success"):
        return jsonify({"error": result.get("message")}), 400

    return jsonify(result)


# ==============================================================================
# Notifications & Campus Zones APIs
# ==============================================================================

@app.route("/api/notifications", methods=["GET"])
def get_notifications():
    """Fetches user notifications from MySQL."""
    curr_u = get_current_user()
    default_uid = curr_u["id"] if curr_u else 1
    user_id = request.args.get("user_id", default_uid, type=int)
    notifs = db_mysql.execute_query(
        "SELECT * FROM notifications WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
        (user_id,)
    )
    unread_count = sum(1 for n in notifs if not n.get("is_read"))
    return jsonify({
        "user_id": user_id,
        "unread_count": unread_count,
        "notifications": notifs
    })


@app.route("/api/notifications/<int:notif_id>/read", methods=["POST"])
def mark_notification_read(notif_id):
    """Marks a notification as read."""
    db_mysql.execute_write("UPDATE notifications SET is_read = 1 WHERE id = %s", (notif_id,))
    return jsonify({"success": True})


@app.route("/api/campus-zones", methods=["GET"])
def get_campus_zones():
    """
    Aggregates report counts by campus zone for interactive map and 'Found Near Me'.
    Uses MongoDB nested field aggregation on 'location.campus_zone'.
    """
    zones = [
        {"id": "Central Library", "name": "Central Library", "icon": "📚", "description": "Study stacks, reading carrels, IT helpdesk"},
        {"id": "Student Center", "name": "Student Center & Union", "icon": "🍔", "description": "Dining hall, bookstore, lounge, clubs"},
        {"id": "Science Complex", "name": "Science Complex", "icon": "🔬", "description": "Lecture halls 100-300, labs, research hub"},
        {"id": "South Residence", "name": "South Residence", "icon": "🏠", "description": "Birch & Elm dorms, laundry, courtyard"},
        {"id": "North Quad", "name": "North Quad", "icon": "🏛️", "description": "Humanities, arts pavilion, outdoor lawn"},
        {"id": "Sports Arena", "name": "Sports & Recreation", "icon": "🏀", "description": "Courts, fitness gym, locker rooms"}
    ]

    # Calculate item counts per zone
    coll = db_mongo.get_items_collection()
    for z in zones:
        z["lost_count"] = coll.count_documents({"location.campus_zone": z["id"], "report_type": "lost", "status": {"$in": ["open", "possible_match"]}})
        z["found_count"] = coll.count_documents({"location.campus_zone": z["id"], "report_type": "found", "status": {"$in": ["open", "possible_match"]}})
        z["total_active"] = z["lost_count"] + z["found_count"]

    return jsonify({"zones": zones})


@app.route("/api/unclaimed-aging", methods=["GET"])
def get_aging_reports():
    """Returns reports older than 30 days for moderator disposition review."""
    items = services.get_unclaimed_aging_reports(days_threshold=1)  # 1 day for demo ease
    return jsonify({
        "count": len(items),
        "items": items,
        "policy_note": "Campus policy recommends donating unclaimed non-urgent clothing/items after 30 days."
    })


@app.route("/api/demo/seed", methods=["POST"])
def demo_seed():
    """Re-seeds both databases on demand."""
    count = seed_data.seed_all()
    return jsonify({
        "message": "Demo data successfully re-seeded across MySQL and MongoDB!",
        "mongo_reports_count": count
    })


# ==============================================================================
# Main Runner
# ==============================================================================

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 5050))
    print(f"============================================================")
    print(f"CAMPUS-FIND Server starting at http://127.0.0.1:{port}")
    print(f"============================================================")
    app.run(host="0.0.0.0", port=port, debug=True)
