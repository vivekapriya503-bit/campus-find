# CAMPUS-FIND: Architecture & DBMS Design Document

## 1. Executive Summary & Rationale for Dual Database Choice
CAMPUS-FIND is a hybrid DBMS project designed to manage lost and found property on a university campus. Rather than forcing all application data into a single paradigm, the system adopts **polyglot persistence**:
- **MongoDB (Document Store):** Used for **item reports**. Lost and found belongings have fundamentally polymorphic, semi-structured attributes. An electronic tablet has brand, model, storage size, and operating system; dorm keys have metal type, ring color, and tag engravings; a wallet has texture, card slots, and compartment contents. In MongoDB, these live naturally in flexible nested subdocuments (`nested_attributes`, `location`, `urgency_info`) without requiring complex schema alterations, sparse columns, or Entity-Attribute-Value (EAV) anti-patterns.
- **MySQL (Relational ACID Store):** Used for **identity, audit, workflow, and financial/security transactions**. User accounts, ownership claims, reviewer signatures, student notifications, and one-time safe return handoff tokens require strict foreign-key integrity, relational joins, and multi-row ACID transactions to guarantee that property is never falsely released or double-claimed.

---

## 2. Privacy & Security Architecture
A core flaw of public lost-and-found boards is the exposure of identifying details, allowing opportunistic bad actors to falsely claim expensive items. CAMPUS-FIND enforces strict data boundaries:
1. **Public vs. Private Partitioning:**
   - Public MongoDB queries strip `private_secret_detail` and `private_secret_hash` using projection (`{"_id": 0, "private_secret_detail": 0}`).
   - Public cards show only approximate campus zones (e.g., "Central Library"), general descriptions, and a prompt hint (e.g., "Please describe the unique mark near the port").
2. **Confidential Ownership Claims:**
   - When a claimant files a claim, their secret verification text is written directly into MySQL's `claims` table, accessible only to authenticated campus moderators.
   - Private claim answers and student PII are never fed into the AI matching engine or external APIs.
3. **Safe Return Tokens (No Public Contact Sharing):**
   - Students and finders do not message each other directly. Instead, claims are reviewed by campus safety officers. Upon approval, a cryptographically random 6-character token (e.g. `CF-7A9B2C`) is generated. Handoff occurs at a supervised campus desk (Room 102), verified using the token and campus student ID.

---

## 3. Transactions & Audit Snapshots
### Immutable Report Snapshots
When an item is reported, its description may evolve over time. However, legal liability requires an immutable audit trail of what the item report stated at the exact moment a student claimed ownership.
- When `submit_private_claim()` executes, it reads the current MongoDB document and writes an **immutable snapshot** (`snapshot_item_title`, `snapshot_report_type`, `snapshot_location_zone`) directly into the MySQL `claims` row.
- If a reporter later edits or deletes their MongoDB document, the claim's historical record in MySQL remains uncorrupted.

### Atomic Multi-Row MySQL Transaction
When a moderator approves a claim, three relational operations must succeed together:
1. `UPDATE claims SET claim_status = 'approved', reviewed_by = %s, reviewer_notes = %s WHERE id = %s`
2. `INSERT INTO handoffs (handoff_code, claim_id, item_uuid, pickup_location, scheduled_window, status, moderator_id) VALUES (...)`
3. `INSERT INTO notifications (user_id, title, message, notification_type, reference_uuid) VALUES (...)`

If an error occurs (such as a duplicate handoff token or network disconnect), `db_mysql.execute_transaction()` issues `ROLLBACK`, guaranteeing that a claim is never approved without an accompanying handoff token and notification.

---

## 4. Failure Handling & Consistency Recovery
In a distributed hybrid architecture, what happens if one database becomes unreachable?

| Failure Scenario | Immediate System Behavior | Recovery & Consistency Mechanism |
| :--- | :--- | :--- |
| **MongoDB is Offline** | Public report browsing and new report submissions fail gracefully with a 503 error; existing claims and moderator handoffs in MySQL remain readable. | **Auto-Resilience Mode:** In development/demo, the system falls back to MongoMock in-memory store. In production, writes are buffered in an append-only log queue and replayed to MongoDB upon reconnect. |
| **MySQL is Offline** | Public search and report submissions to MongoDB remain fully functional; claim submissions and handoff approvals pause. | **Auto-Resilience Mode:** In development/demo, SQLite mirror handles relational writes. In production, read replicas serve pending claims while writes queue. |
| **Partial Failure During Cross-DB Write** | MongoDB write succeeds, but MySQL transaction fails. | The application wraps cross-database workflows in a compensating action: if the MySQL write fails, the newly inserted MongoDB report status is rolled back or flagged as `pending_sync`. |

---

## 5. Honest Evaluation: Hybrid vs. Single SQL Database

### Why a Real-World Small Campus Service Might Prefer SQL-Only:
To be completely honest from an engineering standpoint, a small-to-medium lost and found service for a single campus could easily be built using **MySQL alone**:
1. Modern MySQL (version 5.7+ and 8.0+) supports native `JSON` columns, JSON path expressions (`JSON_EXTRACT(attributes, '$.color')`), and functional indexes on JSON fields.
2. Managing a single database eliminates distributed consistency issues, dual connection pooling, two backup policies, and two query syntaxes.
3. A single MySQL instance simplifies deployments and operational monitoring for small university IT teams.

### What MongoDB Contributes to this Project & Assignment:
Despite the viability of an SQL-only approach, MongoDB provides tangible architectural advantages in this assignment:
1. **Document-First Domain Modeling:** Item reports are fundamentally documents. A lost iPhone, a set of brass keys, and a chemistry textbook share almost no specific attributes beyond title and date. Storing them as native documents in MongoDB allows dynamic schema flexibility without ALTER TABLE migrations or schema bloat.
2. **Nested Spatial & Zone Queries:** MongoDB's document structure allows clean subdocument querying (`location.campus_zone`, `location.building`, `location.floor`) with intuitive dot notation and indexing.
3. **Architectural Separation of Concerns:** It demonstrates the enterprise pattern of **Command Query Responsibility Segregation (CQRS)**: high-velocity, flexible public searching is decoupled from the strictly audited relational transactions governing ownership verification and physical property transfer.
