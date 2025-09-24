-- Vulnleap Webapp Initial Database Schema

-- Users table
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    user_type ENUM('normal', 'admin', 'superadmin') NOT NULL DEFAULT 'normal',
    mfa_secret VARCHAR(32),
    mfa_enabled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);

-- Mortgage quotes table
CREATE TABLE mortgage_quotes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    property_value DECIMAL(15,2) NOT NULL,
    credit_score INT NOT NULL,
    down_payment DECIMAL(15,2) NOT NULL,
    ssn_number VARCHAR(50) NOT NULL,
    loan_amount DECIMAL(15,2) NOT NULL,
    interest_rate DECIMAL(5,2) NOT NULL,
    term_years INT NOT NULL,
    monthly_payment DECIMAL(10,2) NOT NULL,
    total_interest DECIMAL(15,2) NOT NULL,
    status ENUM('quote', 'in_progress', 'active', 'paid_off', 'cancelled') NOT NULL DEFAULT 'quote',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Active mortgages table
CREATE TABLE active_mortgages (
    id INT PRIMARY KEY AUTO_INCREMENT,
    quote_id INT NOT NULL,
    user_id INT NOT NULL,
    current_balance DECIMAL(15,2) NOT NULL,
    payment_account_number VARCHAR(50),
    payment_routing_number VARCHAR(50),
    next_payment_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (quote_id) REFERENCES mortgage_quotes(id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Payment history table
CREATE TABLE mortgage_payments (
    id INT PRIMARY KEY AUTO_INCREMENT,
    mortgage_id INT NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    payment_date TIMESTAMP NOT NULL,
    status ENUM('pending', 'completed', 'failed') NOT NULL,
    transaction_id VARCHAR(100),
    FOREIGN KEY (mortgage_id) REFERENCES active_mortgages(id)
);

-- System settings table
CREATE TABLE system_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(50) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    last_modified_by INT,
    last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (last_modified_by) REFERENCES users(id)
);

-- Audit log table
CREATE TABLE audit_logs (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id INT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
); 

-- Sessions table
CREATE TABLE sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT NOT NULL,
    session_token VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);

-- Org Level Settings
CREATE TABLE org_level_settings (
    id INT PRIMARY KEY AUTO_INCREMENT,
    setting_key VARCHAR(50) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    last_modified_by INT,
    last_modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (last_modified_by) REFERENCES users(id)
);
