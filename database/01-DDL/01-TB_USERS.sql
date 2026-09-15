CREATE TABLE IF NOT EXISTS TB_USERS (
    uid VARCHAR(64) PRIMARY KEY,
    email VARCHAR(320) NOT NULL UNIQUE,
    user_name VARCHAR(255) NOT NULL,
    password VARCHAR(64) NOT NULL,
    permission VARCHAR(20) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT tb_users_permission_check
        CHECK (permission IN ('admin', 'manager', 'user'))
);

CREATE OR REPLACE FUNCTION update_tb_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tb_users_updated_at_trigger ON TB_USERS;

CREATE TRIGGER tb_users_updated_at_trigger
BEFORE UPDATE ON TB_USERS
FOR EACH ROW
EXECUTE FUNCTION update_tb_users_updated_at();