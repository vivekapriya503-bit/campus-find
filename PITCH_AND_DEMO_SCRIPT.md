# CAMPUS-FIND: Pitch & Presentation Demo Script

---

## 1. Hackathon Elevator Pitch (90 Seconds)

> **"Judges, every semester thousands of students lose critical belongings on campus — dorm keys before an exam, prescription glasses, laptops with semester research, and student ID cards.**
>
> Today, lost and found is fragmented across disconnected WhatsApp chats, library desks, and social media posts. Worse yet, posting photos of lost items publicly allows fraudulent claims.
>
> Meet **CAMPUS-FIND** — the Smart Lost & Found Management System built with a powerful hybrid DBMS architecture. 
> 
> We combine **MongoDB** to handle the dynamic, semi-structured nature of lost items with flexible nested attributes and campus location zones, and **MySQL** to enforce strict relational integrity, immutable snapshots, and multi-row ACID transactions for ownership verification and safe returns.
>
> With our local AI heuristic matching engine, students get instant suggestions explaining *why* an item matches, while our private claim verification and one-time 6-character handoff tokens ensure items are safely returned to their rightful owners without exposing private student contact info.
>
> CAMPUS-FIND: Fast, smart, and secure campus recovery."

---

## 2. Live Demo Script (3 to 5 Minutes)

### Step 1: Open the Dashboard (30 Seconds)
- **Action:** Open `http://127.0.0.1:5050` in the browser.
- **Narrator:**
  *"Notice our modern, responsive dashboard. At the very top, you can see our live DBMS status bar showing both MongoDB and MySQL connected and operational.*
  *Students can browse active reports across the campus, filter by category, or use the 'Found Near Me' campus zone selector to check their current location, such as the Central Library or South Residence."*

### Step 2: Demonstrating AI Match Engine & Explanations (60 Seconds)
- **Action:** Find the card for *"Apple iPad Air Space Gray with Stylus"* (Lost) and click **"View & Matches"**.
- **Narrator:**
  *"When a student opens an item, our local transparent NLP match engine evaluates counterpart reports.*
  *Here, it found a 97% match with a found iPad reported in the Central Library.*
  *Notice the transparent explanation: 'Matching category Electronics; Same campus zone Central Library; Matching brand Apple; Incident dates within 24 hours.' We never claim absolute certainty — we label them clearly as suggestions to protect users."*

### Step 3: Demonstrating Private Claim & Security Boundary (60 Seconds)
- **Action:** Click **"Claim This Item"** on the found iPad report.
- **Narrator:**
  *"Notice our privacy boundary: We never show private identifying marks publicly. Instead, the claimant must provide their secret proof — for example: 'A small V-shaped scratch near the charging port and a photo of a golden retriever on the lockscreen.'*
  *When we submit this claim, an immutable snapshot of the report title, type, and zone is written to MySQL alongside the secret. Even if the original report in MongoDB is edited later, our legal audit record is preserved."*

### Step 4: Moderator Desk & MySQL ACID Transaction (60 Seconds)
- **Action:** Click **"Moderator Desk"** in the top navigation.
- **Narrator:**
  *"Here in the Moderator Desk, campus safety officers see claims joined with student registration info using a relational MySQL JOIN.*
  *When Officer Jenkins clicks 'Approve', a multi-row ACID transaction executes in MySQL:*
  *1. The claim status updates to 'approved'.*
  *2. A secure, one-time handoff token (e.g. CF-7A9B2C) is inserted.*
  *3. A student notification is dispatched.*
  *4. And MongoDB updates the report status to 'claimed'.*
  *If any step in the transaction fails, everything rolls back automatically."*

### Step 5: Safe Desk Pickup (30 Seconds)
- **Action:** Enter the handoff token `CF-7A9B2C` in the 'Safe Desk Return' box and click **"Confirm Physical Return"**.
- **Narrator:**
  *"At the student desk, the student presents their student ID and one-time token. The officer verifies the token, the handoff is marked 'completed' in MySQL, and the item is finalized as 'returned' in MongoDB.*
  *Zero private contact numbers shared, zero fraud, 100% accountable."*

---

## 3. Anticipated Judge Q&A

**Q1: Why did you use two databases instead of just MySQL?**
> *"Lost items are naturally polymorphic documents — headphones, coats, dorm keys, and textbooks share almost no attributes. MongoDB allows students to store flexible nested attributes (`nested_attributes.color`, `location.campus_zone`) without rigid schema migrations or sparse columns. Meanwhile, MySQL provides ACID transactions and foreign keys for audit trails, claims, and safe handoff tokens. We use the best tool for each domain."*

**Q2: How do the two databases stay in sync?**
> *"They are bridged by a shared, immutable `item_uuid`. In our services layer, state transitions follow an orchestrated workflow: relational claims and handoffs in MySQL drive lifecycle changes that update the item document status in MongoDB. We also implement audit snapshots in MySQL so later document changes do not alter claim history."*

**Q3: Does the AI feature require an expensive OpenAI or Gemini API key?**
> *"No! We built a transparent local heuristic matching engine using tokenization, Jaccard text similarity, category taxonomy weighting, and spatio-temporal proximity. It runs 100% locally with zero latency, zero cost, and zero student data leakage to third-party AI APIs."*
