
-- Table to store system configurations
-- drop table provider_integration.system_configuration;
CREATE TABLE provider_integration.system_configuration (
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
    is_active BOOLEAN DEFAULT  true not null,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store run history
CREATE TABLE run_history (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Table to store run history
CREATE TABLE run_history_detail (
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);


-- Table to store error details
-- CREATE TABLE error_log (
--     error_id SERIAL PRIMARY KEY,
--     run_id INT REFERENCES run_history(run_id),
--     system_id INT REFERENCES system_configuration(system_id),
--     error_message TEXT NOT NULL,
--     step VARCHAR(255) NOT NULL,
--     occurred_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
-- );

-- Queue table for asynchronous processing
CREATE TABLE provider_integration.status_update_queue (
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


-- Insert statement for Yardi system with detailed config JSON
INSERT INTO provider_integration.system_configuration 
    (system_name, system_type, partner_name, config, s3_bucket_name, credentials_secret_id, schedule, is_active)
VALUES 
    (
        'Yardi', 
        'SOAP', 
        'Caring Dev 1', 
        '{
        "api_url": "https://www.yardipcv.com/8223tp7s7snr/WebServices/ItfSeniorResidentData.asmx",
        "credentials": {
            "username": "caringws",
            "password": "W!tLUk22oMZJEXb",
            "license": "MIIBEAYJKwYBBAGCN1gDoIIBATCB/gYKKwYBBAGCN1gDAaCB7zCB7AIDAgABAgJoAQICAIAEAAQQ/zrUM5V4Qr2KBVWEc5edvQSByGh5TyWjIKGTM+lVzCjVodDBj+t6QaGH/Sm+Rg4dq8hF6VyrBtoHAR2DUFTAAuVNws/mRdtWozYBDQ6FgDbnpsLJ+jcEpv+FYYtZWWRS0lpkH9DUxMN4OSvGB98kQwzBlKVeSWRGlxJZhG6YAvCbHudnl25BeDFjFKuzq3rov+yKGpYpCEdIKxbn+Pl7sTd1GrpKg8Rf5G1zjkbAiiTNybK0iI+KV6xv08ZX5YkTpm938cmnYgFYCo3OKO5TA2pIjpGeWg2qNgbc",
            "ServerName": "afqoml_senior_itf",
            "Database": "afqoml_senior_itf",
            "InterfaceEntity": "Caring.com",
            "YardiPropertyId": "c1233"
        },
        "base_url": "https://www.yardipcv.com/8223tp7s7snr/WebServices/ItfSeniorResidentData.asmx",
        "namespace": "http://tempuri.org/YSI.Senior.SeniorInterface.WebServices/ItfSeniorResidentData"
	    }'::jsonb,
        'yardi-bucket', 
        'YardiCredentials1',
        'Daily EOD',
        true
    );

-- Additional Yardi system configuration with different credentials
INSERT INTO provider_integration.system_configuration 
    (system_name, system_type, partner_name, config, s3_bucket_name, credentials_secret_id, schedule, is_active)
VALUES 
    (
        'Yardi', 
        'SOAP', 
        'Caring Dev 2', 
        '{
        "api_url": "https://www.yardipcv.com/8223tp7s7snr/WebServices/ItfSeniorResidentData.asmx",
        "credentials": {
            "username": "caringws",
            "password": "W!tLUk22oMZJEXb",
            "license": "MIIBEAYJKwYBBAGCN1gDoIIBATCB/gYKKwYBBAGCN1gDAaCB7zCB7AIDAgABAgJoAQICAIAEAAQQ/zrUM5V4Qr2KBVWEc5edvQSByGh5TyWjIKGTM+lVzCjVodDBj+t6QaGH/Sm+Rg4dq8hF6VyrBtoHAR2DUFTAAuVNws/mRdtWozYBDQ6FgDbnpsLJ+jcEpv+FYYtZWWRS0lpkH9DUxMN4OSvGB98kQwzBlKVeSWRGlxJZhG6YAvCbHudnl25BeDFjFKuzq3rov+yKGpYpCEdIKxbn+Pl7sTd1GrpKg8Rf5G1zjkbAiiTNybK0iI+KV6xv08ZX5YkTpm938cmnYgFYCo3OKO5TA2pIjpGeWg2qNgbc",
            "ServerName": "afqoml_senior_itf",
            "Database": "afqoml_senior_itf",
            "InterfaceEntity": "Caring.com",
            "YardiPropertyId": "c1233"
        },
        "base_url": "https://www.yardipcv.com/8223tp7s7snr/WebServices/ItfSeniorResidentData.asmx",
        "namespace": "http://tempuri.org/YSI.Senior.SeniorInterface.WebServices/ItfSeniorResidentData"
	    }'::jsonb,
        'yardi-bucket', 
        'YardiCredentials2',
        'Daily EOD',
        true
    );
