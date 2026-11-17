-- ==============================================================================
-- CAMPUS-FIND Sample Seed Data (MySQL)
-- Fictional records for demonstration and presentation testing
-- ==============================================================================

USE campus_find_db;

-- Clear previous test data in proper order (respecting foreign keys)
SET FOREIGN_KEY_CHECKS = 0;
TRUNCATE TABLE handoffs;
TRUNCATE TABLE notifications;
TRUNCATE TABLE match_suggestions;
TRUNCATE TABLE claims;
TRUNCATE TABLE users;
SET FOREIGN_KEY_CHECKS = 1;

-- -----------------------------------------------------------------------------
-- Seed Users (Passwords are pre-hashed using Werkzeug scrypt/pbkdf2: demo123)
-- -----------------------------------------------------------------------------
INSERT INTO users (id, user_uuid, username, email, password_hash, full_name, role, department, phone_masked) VALUES
(1, 'usr-student-001', 'maya_lin', 'maya.lin@campus.edu', 'pbkdf2:sha256:260000$demo$hashforseedaccountsonly', 'Maya Lin', 'student', 'Computer Science', '***-***-4921'),
(2, 'usr-student-002', 'alex_chen', 'alex.chen@campus.edu', 'pbkdf2:sha256:260000$demo$hashforseedaccountsonly', 'Alex Chen', 'student', 'Mechanical Eng', '***-***-8832'),
(3, 'usr-mod-001', 'sarah_safety', 'safety.office@campus.edu', 'pbkdf2:sha256:260000$demo$hashforseedaccountsonly', 'Officer Sarah Jenkins', 'moderator', 'Campus Safety & Desk', '***-***-1100'),
(4, 'usr-admin-001', 'dean_affairs', 'affairs.admin@campus.edu', 'pbkdf2:sha256:260000$demo$hashforseedaccountsonly', 'Dr. Evelyn Reed', 'admin', 'Dean of Students Office', '***-***-9999');

-- -----------------------------------------------------------------------------
-- Seed Claims (Linked to MongoDB item_uuids)
-- -----------------------------------------------------------------------------
INSERT INTO claims (id, claim_uuid, item_uuid, claimant_id, claim_status, private_verification_text, snapshot_item_title, snapshot_report_type, snapshot_location_zone, reviewer_notes, reviewed_by, created_at) VALUES
(1, 'clm-8821a', 'cf-item-001', 1, 'approved', 'Scratch shaped like letter V near charging port; lockscreen has a golden retriever puppy.', 'Space Gray iPad Air 5th Gen', 'found', 'Central Library', 'Verified in person with student ID card. Screen wallpaper matches description.', 3, NOW() - INTERVAL 2 DAY),
(2, 'clm-9943b', 'cf-item-003', 2, 'pending_review', 'Has a red silicone key fob with the logo of North High Track & Field 2022.', 'Dorm Room Brass Keys with Lanyard', 'found', 'South Residence', NULL, NULL, NOW() - INTERVAL 4 HOUR);

-- -----------------------------------------------------------------------------
-- Seed Match Suggestions (AI / Heuristic Match engine outputs)
-- -----------------------------------------------------------------------------
INSERT INTO match_suggestions (id, lost_item_uuid, found_item_uuid, confidence_score, explanation, match_status, created_at) VALUES
(1, 'cf-item-002', 'cf-item-001', 0.92, 'Same category (Electronics), matching brand (Apple), matching color (Space Gray), and reported near Central Library within 14 hours.', 'suggested', NOW() - INTERVAL 1 DAY),
(2, 'cf-item-004', 'cf-item-003', 0.88, 'Matching category (Keys & Bags), building proximity (South Residence Hall B), and incident timestamp matches within 6 hours.', 'suggested', NOW() - INTERVAL 3 HOUR);

-- -----------------------------------------------------------------------------
-- Seed Notifications
-- -----------------------------------------------------------------------------
INSERT INTO notifications (id, user_id, title, message, notification_type, reference_uuid, is_read, created_at) VALUES
(1, 1, 'Claim Approved & Return Ready', 'Your claim for "Space Gray iPad Air 5th Gen" was verified by Officer Jenkins. One-time handoff code: CF-7A9B2C.', 'handoff_ready', 'clm-8821a', FALSE, NOW() - INTERVAL 1 DAY),
(2, 2, 'Promising Match Found', 'A found report matching your lost dorm keys was logged in South Residence. Check possible matches!', 'match_found', 'cf-item-004', FALSE, NOW() - INTERVAL 3 HOUR),
(3, 3, 'Urgent Item Review Needed', 'An urgent item (Prescription Glasses needed for exams) was reported in Science Complex.', 'urgency_alert', 'cf-item-005', FALSE, NOW() - INTERVAL 1 HOUR);

-- -----------------------------------------------------------------------------
-- Seed Handoffs (Safe Hand-off with one-time 6-character token)
-- -----------------------------------------------------------------------------
INSERT INTO handoffs (id, handoff_code, claim_id, item_uuid, pickup_location, scheduled_window, status, completed_at, moderator_id, created_at) VALUES
(1, 'CF-7A9B2C', 1, 'cf-item-001', 'Student Center Lost & Found Desk (Room 102)', 'Mon-Fri 9:00 AM - 5:00 PM', 'completed', NOW() - INTERVAL 4 HOUR, 3, NOW() - INTERVAL 1 DAY),
(2, 'CF-3D8E1F', 2, 'cf-item-003', 'South Quad Security Station (Bldg C Lobby)', 'Available 24/7 with Student ID', 'scheduled', NULL, 3, NOW() - INTERVAL 1 HOUR);
