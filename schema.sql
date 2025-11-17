-- CropAI MySQL schema
-- Import this file in phpMyAdmin (Import tab) or paste in the SQL tab

-- Create database and use it
CREATE DATABASE IF NOT EXISTS cropai
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
USE cropai;

-- Reports table (matches SQLAlchemy model in api/models.py)
CREATE TABLE IF NOT EXISTS reports (
  id INT AUTO_INCREMENT PRIMARY KEY,
  filename VARCHAR(255) NULL,
  disease VARCHAR(255) NOT NULL,
  confidence DOUBLE NOT NULL,
  severity VARCHAR(50) NOT NULL,
  recommendations TEXT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_reports_created_at (created_at)
);

-- Feedback table (matches SQLAlchemy model in api/models.py)


CREATE TABLE IF NOT EXISTS users (
  id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(50) NOT NULL DEFAULT 'user',
  is_active TINYINT(1) NOT NULL DEFAULT 1,
  last_login_at DATETIME NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_users_email (email),
  INDEX idx_users_created_at (created_at)
);
