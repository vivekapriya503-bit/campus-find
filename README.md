# CAMPUS-FIND — Smart Lost & Found Management System

> **A modern hybrid DBMS web application built for universities, powered by Python Flask, MySQL, MongoDB, and a single responsive frontend.**

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Feature Breakdown (Core vs. Stretch)](#feature-breakdown-core-vs-stretch)
4. [MacBook Setup & Run Instructions](#macbook-setup--run-instructions)
5. [Database Architecture & Hybrid Design](#database-architecture--hybrid-design)
6. [Running the Automated Verification Suite](#running-the-automated-verification-suite)
7. [Running the Jupyter DBMS Walkthrough Notebook](#running-the-jupyter-dbms-walkthrough-notebook)
8. [Troubleshooting Guide for macOS](#troubleshooting-guide-for-macos)

---

## Project Overview

Students often lose ID cards, books, wallets, keys, and electronics across campus. Finding them is chaotic because campuses lack a unified, trustworthy system. 

**CAMPUS-FIND** solves this problem by providing:
- A responsive, single-page web portal for reporting lost and found items.
- A **hybrid DBMS** using **MongoDB** for flexible item reports with nested attributes and **MySQL** for relational integrity, claims, and atomic handoff transactions.
- A local AI match engine that suggests and explains possible matches without paid API keys.
- Private claim verification that protects identifying marks from public listings.
- Supervised safe handoffs with one-time 6-character return tokens.

---

## Technology Stack

- **Backend:** Python 3.9+ with **Flask** (serving the frontend and REST APIs).
- **Relational Database:** **MySQL 8.0+** (stores `users`, `claims`, `match_suggestions`, `notifications`, `handoffs`).
- **Document Database:** **MongoDB 6.0+** (stores `item_reports` with nested attributes and locations).
- **Frontend:** A single `index.html` file with embedded CSS in one `<style>` block and JavaScript in one `<script>` block. No npm, webpack, or frontend frameworks required.
- **Python Libraries:** `pymysql`, `pymongo`, `python-dotenv`, `werkzeug`, `mongomock`.

---

## Feature Breakdown (Core vs. Stretch)

### Core Features (Essential for Project Submission)
- [x] **Lost & Found Reports:** Submit item name, category, description, date, campus zone, and photo.
- [x] **Search & Multi-Filter:** Search by text keyword, category, status, and campus zone.
- [x] **Possible Matches:** Automatic comparison of lost and found items using transparent local logic.
- [x] **AI Match Explanations:** Clear natural-language explanations (e.g. *"Same category, matching brand, reported near Central Library within 24 hours"*).
- [x] **Duplicate & Spam Checks:** Warns users if a newly submitted report is suspiciously similar to an existing one.
- [x] **Private Claim Verification:** Claimants submit a hidden distinguishing mark (scratch, sticker, serial) kept confidential for moderator review.
- [x] **Student Notifications:** Alerts for match suggestions, claim updates, and ready handoffs.
- [x] **Item Lifecycle Tracking:** Clear statuses: `open`, `possible_match`, `claimed`, `returned`, `closed`.
- [x] **Safe Handoff Workflow:** Desk-verified return using secure 6-character pickup tokens (`CF-XXXXXX`).
- [x] **Relational MySQL Schema:** 5 tables with primary keys, foreign keys, constraints, and audit snapshots.
- [x] **MongoDB Nested Collection:** Documents with nested location, nested attributes, and urgency subdocuments.
- [x] **MySQL Relational JOIN:** Multi-table JOIN combining claims, claimants, reviewers, and handoff tokens.
- [x] **MongoDB Nested Query:** Demonstrates querying `location.campus_zone` and `nested_attributes.color`.
- [x] **MySQL ACID Transaction:** Atomic multi-row transaction for claim approval with rollback protection.

### Distinctive Stretch Features (Clearly Marked)
- [x] ⭐ **Campus Location Map ("Found Near Me"):** Interactive zone cards showing approximate active item counts per campus building/zone without tracking precise private GPS.
- [x] ⭐ **Urgency & Perishability Alerts:** Mark items as time-sensitive (e.g., dorm keys needed for lecture, prescription glasses, exam notes).
- [x] ⭐ **Unclaimed-Item Aging Reminders:** Moderator review alert for items older than 30 days to facilitate campus policy donations.
- [x] ⭐ **Desk Handoff Token Redemption Tool:** Live token validation tool for campus safety officers at the pickup window.
- [x] ⭐ **Auto-Resilience Development Engine:** Seamless fallback allows the full application, tests, and Jupyter notebook to run immediately on a MacBook even before external database servers are started.

---

## MacBook Setup & Run Instructions

Follow these easy steps to run the complete project on any macOS machine.

### Step 1: Open Terminal and Navigate to the Project
```bash
cd /Users/apple/.gemini/antigravity/scratch/campus-find
```

### Step 2: Set Up Python Virtual Environment
```bash
# Create virtual environment (if not already created)
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install required packages
pip install -r requirements.txt
```

### Step 3: Configure Environment Variables
A sample `.env` file is already provided. You can inspect or edit it:
```bash
cp .env.example .env
```
Default configuration:
```ini
FLASK_PORT=5050
SECRET_KEY=campus-find-local-dev-secret-key-92847

MYSQL_HOST=127.0.0.1
MYSQL_PORT=3306
MYSQL_USER=campus_user
MYSQL_PASSWORD=campus_password_placeholder
MYSQL_DATABASE=campus_find_db

MONGO_URI=mongodb://127.0.0.1:27017
MONGO_DB_NAME=campus_find_mongo

# Resilience Mode: 'auto' allows instant demonstration out-of-the-box
RESILIENCE_MODE=auto
```

---

### Step 4: (Optional) Starting Local MySQL and MongoDB on macOS

> **Note:** Thanks to the built-in **Auto-Resilience Mode**, you can run and test the full website immediately without starting external database servers! If you want to connect to real live MySQL and MongoDB servers on your Mac, use Homebrew:

#### To install and start MySQL with Homebrew:
```bash
# Install MySQL
brew install mysql

# Start MySQL service
brew services start mysql

# Load the CAMPUS-FIND schema into MySQL (or open schema.sql in MySQL Workbench)
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql
```

#### To install and start MongoDB with Homebrew:
```bash
# Install MongoDB Community Edition
brew tap mongodb/brew
brew install mongodb-community

# Start MongoDB service
brew services start mongodb-community

# Load collection indexes
mongosh < database/mongo_setup.js
```

---

### Step 5: Seed the Databases
Run the seeder script to populate both databases with rich sample data:
```bash
./venv/bin/python seed_data.py
```
*Output will confirm inserted items in MongoDB and seeded users, claims, match pairs, and handoff tokens in MySQL.*

---

### Step 6: Start the Web Application
Start the Flask server:
```bash
./venv/bin/python app.py
```

Open your web browser (Safari, Chrome, or Firefox) and visit:
👉 **[http://127.0.0.1:5050](http://127.0.0.1:5050)**

*(Note: We use port `5050` because macOS Monterey/Ventura/Sonoma reserves port `5000` for Apple AirPlay Receiver).*

---

## Running the Automated Verification Suite

To verify all DBMS requirements in one command:
```bash
./venv/bin/python test_suite.py
```

This test suite automatically verifies:
1. **MongoDB Nested Field Queries** (`location.campus_zone`, `nested_attributes.color`, `urgency_info.is_urgent`).
2. **MySQL Multi-Table Relational JOIN** (joining `claims`, `users`, and `handoffs`).
3. **MySQL Multi-Row ACID Transaction** (updating claim, generating handoff token, and dispatching notification within a single transaction).
4. **Transaction Rollback Protection** (ensuring failed queries cleanly rollback).
5. **AI Heuristic Match Engine** (scoring and explanation generation).
6. **Duplicate & Spam Warning Detection**.
7. **End-to-End Flask REST API Endpoints**.

---

## Running the Jupyter DBMS Walkthrough Notebook

We provide a self-contained, beginner-friendly notebook: `dbms_walkthrough.ipynb`.

To run it:
```bash
# Start Jupyter
jupyter notebook dbms_walkthrough.ipynb
```
*(Or open `dbms_walkthrough.ipynb` directly in Visual Studio Code or Google Colab).*

The notebook guides you cell-by-cell through:
- Independent database handshakes.
- Executing and viewing nested MongoDB queries.
- Executing and viewing the MySQL relational JOIN.
- Executing the atomic multi-row transaction and testing rollback.
- Combining MongoDB documents with MySQL relations using `item_uuid`.

---

## Deploying to GitHub

This repository is already initialized with clean `.gitignore` rules (excluding `.env`, `venv/`, and temporary database files). Follow these quick steps to push your project to GitHub:

### Step 1: Create a New GitHub Repository
1. Log in to [GitHub](https://github.com/) in your browser.
2. Click the **`+`** icon in the top right corner and select **New repository** (or go to [github.com/new](https://github.com/new)).
3. Repository name: `campus-find`
4. Description: `CAMPUS-FIND — Smart Lost & Found Management System (Flask + MySQL + MongoDB)`
5. Visibility: **Public** or **Private**.
6. **Do NOT** check "Add a README file" or ".gitignore" (these already exist locally).
7. Click **Create repository**.

### Step 2: Push Your Local Repository to GitHub
In your Mac Terminal:
```bash
cd /Users/apple/.gemini/antigravity/scratch/campus-find

# Link your local repo to GitHub (replace YOUR_USERNAME with your GitHub handle):
git remote add origin https://github.com/YOUR_USERNAME/campus-find.git

# Set default branch to main:
git branch -M main

# Push all files and history to GitHub:
git push -u origin main
```

*(Note: When prompted for password in terminal, use a [GitHub Personal Access Token](https://github.com/settings/tokens) with `repo` scope, or SSH keys).*

---

## Deploying to Cloud Hosting (Optional)
If you want to host CAMPUS-FIND live on the internet:
- **Render / Railway:** Connect your GitHub repo, set the build command to `pip install -r requirements.txt` and the start command to `python app.py` (or `gunicorn app:app`). Add environment variables from `.env.example`.
- **PythonAnywhere:** Upload files or `git clone`, create a virtualenv, and point the WSGI configuration to `app.py`.

---

## Troubleshooting Guide for macOS

- **Port 5000 already in use:** macOS uses port 5000 for Apple AirPlay Receiver. CAMPUS-FIND defaults to port **5050** to avoid conflicts. You can change `FLASK_PORT` in `.env` if desired.
- **Python hashlib scrypt error on macOS:** macOS built-in Python 3.9 does not include OpenSSL scrypt. CAMPUS-FIND uses `pbkdf2:sha256` which runs natively on every Mac without external compilation.
- **MySQL Connection Refused:** Ensure MySQL is started (`brew services start mysql`), or keep `RESILIENCE_MODE=auto` in `.env` to let the auto-resilience engine handle the demonstration.
- **MongoDB Connection Refused:** Ensure MongoDB is started (`brew services start mongodb-community`), or keep `RESILIENCE_MODE=auto` in `.env`.
