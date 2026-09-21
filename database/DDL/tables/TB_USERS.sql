CREATE TABLE tb_users (
    uid VARCHAR(256) NOT NULL,
    email VARCHAR(256) NOT NULL,
    user_name VARCHAR(256) NOT NULL,
    password VARCHAR(64) NOT NULL,
    permission VARCHAR(256) NOT NULL DEFAULT 'user',
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    CONSTRAINT pk_tb_users PRIMARY KEY (uid),
    CONSTRAINT uk_tb_users_email UNIQUE (email),
    CONSTRAINT ck_tb_users_password_hex
        CHECK (password ~ '^[0-9A-Fa-f]{64}$'),
    CONSTRAINT ck_tb_users_permission
        CHECK (permission IN ('admin', 'manager', 'user'))
);

COMMENT ON TABLE tb_users IS 'Application user accounts and permissions';
COMMENT ON COLUMN tb_users.uid IS 'SHA-256 hash of the lowercase email';
COMMENT ON COLUMN tb_users.email IS 'Lowercase unique email address';
COMMENT ON COLUMN tb_users.user_name IS 'User display name';
COMMENT ON COLUMN tb_users.password IS 'Frontend-encrypted password value';
COMMENT ON COLUMN tb_users.permission IS 'Application role';
COMMENT ON COLUMN tb_users.created_at IS 'UTC creation timestamp';
COMMENT ON COLUMN tb_users.updated_at IS 'UTC last-update timestamp';
