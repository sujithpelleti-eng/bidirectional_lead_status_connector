-- Create the provider_integration schema if it doesn't exist
CREATE SCHEMA IF NOT EXISTS provider_integration;

-- Table to store system configurations
CREATE TABLE IF NOT EXISTS provider_integration.system_configuration (
    system_config_id SERIAL PRIMARY KEY,
    system_name VARCHAR(255) NOT NULL,  -- e.g., 'Yardi', 'Salesforce'
    system_type VARCHAR(255) NOT NULL,  -- e.g., 'SOAP', 'REST'
    partner_id VARCHAR(255) NOT NULL,
    partner_name VARCHAR(255) NOT NULL,
    file_type VARCHAR(255) NOT NULL,
    config JSONB NOT NULL,
    s3_bucket_name VARCHAR(255) NOT NULL,
    credentials_secret_id VARCHAR(255) NOT NULL, -- Reference to AWS Secrets Manager
    schedule VARCHAR(255) DEFAULT 'Daily EOD' NOT NULL,
    is_active BOOLEAN DEFAULT true NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store run history
CREATE TABLE IF NOT EXISTS provider_integration.run_history (
    run_id SERIAL PRIMARY KEY,
    execution_id UUID NOT NULL,
    total_configs_executed INT,   -- Total number of configurations processed in this execution
    successful_configs INT DEFAULT 0,
    failed_configs INT DEFAULT 0,
    status VARCHAR(50) NOT NULL,  -- success or failure
    details TEXT,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store run history detail
CREATE TABLE IF NOT EXISTS provider_integration.run_history_detail (
    run_detail_id SERIAL PRIMARY KEY,
    run_id INT NOT NULL,
    execution_id UUID NOT NULL,
    system_config_id INT NOT NULL,
    system_name VARCHAR(255),
    partner_name VARCHAR(255),
    step VARCHAR(50) NOT NULL,
    status VARCHAR(50) NOT NULL,  -- success or failure
    s3_location VARCHAR(250),
    records_fetched INT DEFAULT 0,
    records_success INT DEFAULT 0,
    records_error INT DEFAULT 0,
    start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    end_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Queue table for asynchronous processing
CREATE TABLE IF NOT EXISTS provider_integration.status_update_queue (
    execution_id UUID NOT NULL,
    status_update_id SERIAL PRIMARY KEY,
    lead_id VARCHAR(255) NOT NULL,
    status VARCHAR(50) NOT NULL,
    sub_status VARCHAR(50),
    notes TEXT,
    provider VARCHAR(255),
    attempts INT DEFAULT 0,
    last_attempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    status_to_post BOOLEAN DEFAULT false,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

