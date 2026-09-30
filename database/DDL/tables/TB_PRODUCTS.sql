CREATE TABLE tb_products (
    id VARCHAR(13) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    label_ids TEXT NOT NULL,
    cost NUMERIC(10, 2) NOT NULL,
    price NUMERIC(10, 2) NOT NULL,
    delete_flag BOOLEAN NOT NULL DEFAULT FALSE,
    created_uid VARCHAR(255) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    updated_uid VARCHAR(255) NOT NULL,
    updated_at TIMESTAMP NOT NULL
);

COMMENT ON TABLE tb_products IS 'Product records';
COMMENT ON COLUMN tb_products.id IS '13-digit Unix timestamp product ID';
COMMENT ON COLUMN tb_products.name IS 'Product name';
COMMENT ON COLUMN tb_products.label_ids IS 'Comma-separated label IDs';
COMMENT ON COLUMN tb_products.cost IS 'Product cost';
COMMENT ON COLUMN tb_products.price IS 'Product price';
COMMENT ON COLUMN tb_products.delete_flag IS 'Soft-delete flag';
COMMENT ON COLUMN tb_products.created_uid IS 'Creator UID';
COMMENT ON COLUMN tb_products.created_at IS 'UTC creation timestamp';
COMMENT ON COLUMN tb_products.updated_uid IS 'Last updater UID';
COMMENT ON COLUMN tb_products.updated_at IS 'UTC last-update timestamp';
