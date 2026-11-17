-- ==============================================================================
-- CAMPUS-FIND: Smart Lost & Found Management System
-- Relational MySQL Schema (MySQL 8.0+ compatible / opens in MySQL Workbench)
-- ==============================================================================

CREATE DATABASE IF NOT EXISTS campus_find_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE campus_find_db;

-- -----------------------------------------------------------------------------
-- Table 1: users (Students, Campus Staff, Moderators, and System Admins)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_uuid VARCHAR(64) NOT NULL UNIQUE,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    role ENUM('student', 'moderator', 'admin') NOT NULL DEFAULT 'student',
    department VARCHAR(100) DEFAULT 'General Campus',
    phone_masked VARCHAR(20) DEFAULT '***-***-0000',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_user_role (role),
    INDEX idx_user_uuid (user_uuid)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Table 2: claims (Student claims submitted on found or lost items)
-- Stores immutable snapshot of report state at time of claim creation.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS claims (
    id INT AUTO_INCREMENT PRIMARY KEY,
    claim_uuid VARCHAR(64) NOT NULL UNIQUE,
    item_uuid VARCHAR(64) NOT NULL,
    claimant_id INT NOT NULL,
    claim_status ENUM('pending_review', 'approved', 'rejected', 'cancelled') NOT NULL DEFAULT 'pending_review',
    private_verification_text TEXT NOT NULL,
    snapshot_item_title VARCHAR(255) NOT NULL,
    snapshot_report_type VARCHAR(20) NOT NULL,
    snapshot_location_zone VARCHAR(100) NOT NULL,
    reviewer_notes TEXT NULL,
    reviewed_by INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_claim_user FOREIGN KEY (claimant_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_claim_reviewer FOREIGN KEY (reviewed_by) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_claim_item (item_uuid),
    INDEX idx_claim_status (claim_status)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Table 3: match_suggestions (AI/Heuristic match pairs between lost & found)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS match_suggestions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lost_item_uuid VARCHAR(64) NOT NULL,
    found_item_uuid VARCHAR(64) NOT NULL,
    confidence_score DECIMAL(4, 2) NOT NULL,
    explanation TEXT NOT NULL,
    match_status ENUM('suggested', 'verified', 'dismissed') NOT NULL DEFAULT 'suggested',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_match_pair UNIQUE (lost_item_uuid, found_item_uuid),
    INDEX idx_lost_item (lost_item_uuid),
    INDEX idx_found_item (found_item_uuid)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Table 4: notifications (In-app notifications for students and staff)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    notification_type ENUM('match_found', 'claim_update', 'handoff_ready', 'urgency_alert', 'moderation') NOT NULL,
    reference_uuid VARCHAR(64) NULL,
    is_read BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_notification_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_unread (user_id, is_read)
) ENGINE=InnoDB;

-- -----------------------------------------------------------------------------
-- Table 5: handoffs (One-time secure return verification tokens & logs)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS handoffs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    handoff_code VARCHAR(20) NOT NULL UNIQUE,
    claim_id INT NOT NULL,
    item_uuid VARCHAR(64) NOT NULL,
    pickup_location VARCHAR(150) NOT NULL DEFAULT 'Student Center Lost & Found Desk (Room 102)',
    scheduled_window VARCHAR(100) NOT NULL DEFAULT 'Weekdays 9:00 AM - 5:00 PM',
    status ENUM('scheduled', 'completed', 'expired') NOT NULL DEFAULT 'scheduled',
    completed_at TIMESTAMP NULL,
    moderator_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_handoff_claim FOREIGN KEY (claim_id) REFERENCES claims(id) ON DELETE CASCADE,
    CONSTRAINT fk_handoff_moderator FOREIGN KEY (moderator_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_handoff_code (handoff_code),
    INDEX idx_handoff_item (item_uuid)
) ENGINE=InnoDB;
