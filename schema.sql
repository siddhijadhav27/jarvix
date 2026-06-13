-- User Languages Table
CREATE TABLE IF NOT EXISTS user_languages (
    user_id VARCHAR(255),
    language_code VARCHAR(10),
    confidence_score FLOAT DEFAULT 0,
    message_count INT DEFAULT 0,
    last_used TIMESTAMP,
    PRIMARY KEY (user_id, language_code)
);

-- User Profile Table
CREATE TABLE IF NOT EXISTS user_profile (
    user_id VARCHAR(255) PRIMARY KEY,
    primary_language VARCHAR(10),
    total_messages INT DEFAULT 0,
    last_updated TIMESTAMP
);
