# CAMPUS-FIND: Architecture & Database Schema Documentation

## 1. System Architecture Overview

CAMPUS-FIND uses a **hybrid polyglot persistence architecture**:
- **MongoDB** acts as the flexible document store for varied, semi-structured item reports with nested attributes.
- **MySQL** acts as the transactional relational store for user identities, private claims, match pairs, audit snapshots, notifications, and safe return handoff tokens.
- The two distinct database engines are bridged using a shared, immutable identifier: `item_uuid`.

```
+-----------------------------------------------------------------------------------+
|                           CLIENT LAYER (Single Page App)                          |
|                       index.html (Modern CSS Grid + ES6 JS)                       |
+-----------------------------------------------------------------------------------+
                                          |
                                HTTP / REST JSON
                                          v
+-----------------------------------------------------------------------------------+
|                        BACKEND APPLICATION LAYER (Flask)                         |
|                                                                                   |
|   +-------------------+  +-----------------------+  +-------------------------+   |
|   |  app.py (Routes)  |  |  services.py (Logic)  |  |  Local AI Match Engine  |   |
|   +-------------------+  +-----------------------+  +-------------------------+   |
|            |                                                    |                 |
|            +-------------------------+--------------------------+                 |
|                                      |                                            |
|                  +-------------------+-------------------+                        |
|                  |                                       |                        |
|                  v                                       v                        |
|        +-------------------+                   +-------------------+              |
|        |    db_mongo.py    |                   |    db_mysql.py    |              |
|        +-------------------+                   +-------------------+              |
+------------------|---------------------------------------|------------------------+
                   |                                       |
                   v                                       v
+-------------------------------------+ +-------------------------------------------+
|      DOCUMENT DATA STORE (MongoDB)  | |       RELATIONAL DATA STORE (MySQL)       |
|                                     | |                                           |
| Collection: item_reports            | | Tables:                                   |
| - item_uuid (Shared Bridge Key)     | | - users (Students, Moderators, Admins)    |
| - report_type ("lost" | "found")    | | - claims (Ownership Claims & Snapshots)   |
| - category, title, description      | | - match_suggestions (AI Pair Scores)      |
| - nested_attributes:                | | - notifications (Student Alerts)          |
|     { color, brand, condition... }  | | - handoffs (One-Time Pickup Codes)        |
| - location:                         | |                                           |
|     { campus_zone, building... }    | | ACID Transactions, Strict Foreign Keys,   |
| - urgency_info:                     | | and Relational JOIN Queries               |
|     { is_urgent, reason... }        | |                                           |
+-------------------------------------+ +-------------------------------------------+
                   ^                                       ^
                   +================= item_uuid ============+
                               (Shared Identifier Bridge)
```

---

## 2. Relational MySQL Schema (Entity-Relationship Diagram)

```mermaid
erDiagram
    users ||--o{ claims : "submits (as claimant)"
    users ||--o{ claims : "reviews (as moderator)"
    users ||--o{ notifications : "receives"
    users ||--o{ handoffs : "verifies (as moderator)"
    claims ||--o| handoffs : "generates return token"
    
    users {
        int id PK
        string user_uuid UK
        string username UK
        string email UK
        string password_hash
        string full_name
        string role "student | moderator | admin"
        string department
        string phone_masked
        timestamp created_at
    }

    claims {
        int id PK
        string claim_uuid UK
        string item_uuid "Shared Bridge to MongoDB"
        int claimant_id FK
        string claim_status "pending_review | approved | rejected | cancelled"
        text private_verification_text "Confidential Secret"
        string snapshot_item_title "Immutable Audit Snapshot"
        string snapshot_report_type
        string snapshot_location_zone
        text reviewer_notes
        int reviewed_by FK
        timestamp created_at
        timestamp updated_at
    }

    match_suggestions {
        int id PK
        string lost_item_uuid "Links to MongoDB"
        string found_item_uuid "Links to MongoDB"
        decimal confidence_score "0.00 to 1.00"
        text explanation "Natural Language Reason"
        string match_status "suggested | verified | dismissed"
        timestamp created_at
    }

    notifications {
        int id PK
        int user_id FK
        string title
        text message
        string notification_type "match_found | claim_update | handoff_ready"
        string reference_uuid
        boolean is_read
        timestamp created_at
    }

    handoffs {
        int id PK
        string handoff_code UK "e.g. CF-7A9B2C"
        int claim_id FK
        string item_uuid "Shared Bridge to MongoDB"
        string pickup_location
        string scheduled_window
        string status "scheduled | completed | expired"
        timestamp completed_at
        int moderator_id FK
        timestamp created_at
    }
```

---

## 3. MongoDB Document Structure (`item_reports` Collection)

Each document in MongoDB stores the flexible metadata of an item report, supporting nested structures without rigid SQL schema migrations:

```json
{
  "_id": "ObjectId('673412ab9c7e012345678901')",
  "item_uuid": "cf-item-001",
  "report_type": "found",
  "title": "Space Gray iPad Air 5th Gen",
  "category": "Electronics",
  "status": "claimed",
  "description": "Found on wooden study table near back windows with screen protector.",
  "nested_attributes": {
    "color": "Space Gray",
    "brand": "Apple",
    "model": "iPad Air (5th Generation)",
    "distinguishing_mark": "Scratch shaped like letter V near charging port",
    "condition": "Good"
  },
  "location": {
    "campus_zone": "Central Library",
    "building": "Main Campus Library",
    "floor": "3rd Floor",
    "room_or_area": "North Study Stacks Table #14"
  },
  "urgency_info": {
    "is_urgent": false,
    "urgency_reason": "Secured in Central Library Safe",
    "is_perishable": false
  },
  "dates": {
    "incident_date": "2026-11-10",
    "reported_at": "2026-11-10T14:30:00Z"
  },
  "reporter": {
    "user_uuid": "usr-student-002",
    "display_name": "Alex Chen",
    "role": "student"
  },
  "private_secret_hint": "Please name the wallpaper image or the unique mark near the port.",
  "photo_meta": {
    "has_photo": true,
    "image_url": "https://images.unsplash.com/photo-1544244015-0df4b3ffc6b0?w=600"
  }
}
```

---

## 4. Multi-Row Atomic Transaction & Safe Handoff Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Student as Claimant (Student)
    actor Mod as Moderator (Campus Safety)
    participant Flask as Flask API Server
    participant MySQL as Relational MySQL
    participant Mongo as Document MongoDB

    Student->>Flask: POST /api/claims (item_uuid, private_verification_text)
    Flask->>Mongo: Fetch item snapshot (title, type, zone)
    Flask->>MySQL: INSERT INTO claims (status='pending_review', snapshot_*, secret)
    Flask-->>Student: Claim Submitted (Pending Moderator Review)

    Mod->>Flask: GET /api/claims (View Review Queue)
    Flask->>MySQL: SELECT * FROM claims c INNER JOIN users u LEFT JOIN handoffs h (MySQL JOIN)
    Flask-->>Mod: Claims Queue with Claimant Details

    Mod->>Flask: POST /api/claims/{id}/review (action='approve')
    Note over Flask,MySQL: BEGIN MySQL TRANSACTION (ACID)
    Flask->>MySQL: 1. UPDATE claims SET claim_status = 'approved', reviewed_by = mod_id
    Flask->>MySQL: 2. INSERT INTO handoffs (handoff_code='CF-7A9B2C', claim_id, item_uuid)
    Flask->>MySQL: 3. INSERT INTO notifications (user_id, 'Claim Approved: Handoff Code CF-7A9B2C')
    Note over Flask,MySQL: COMMIT TRANSACTION
    Flask->>Mongo: Update item status to 'claimed'
    Flask-->>Mod: Approval confirmed & Handoff Code issued

    Student->>Mod: Presents Student ID & One-Time Token (CF-7A9B2C) at Desk
    Mod->>Flask: POST /api/handoffs/verify (code='CF-7A9B2C')
    Flask->>MySQL: UPDATE handoffs SET status = 'completed', completed_at = NOW()
    Flask->>Mongo: UPDATE item_reports SET status = 'returned'
    Flask-->>Mod: Handoff Confirmed! Belonging returned safely.
```
