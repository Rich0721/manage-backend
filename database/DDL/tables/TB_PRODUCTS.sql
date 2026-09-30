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

COMMENT ON TABLE tb_products IS '產品資料';
COMMENT ON COLUMN tb_products.id IS '產品識別碼（Unix 毫秒時間戳）';
COMMENT ON COLUMN tb_products.name IS '產品名稱';
COMMENT ON COLUMN tb_products.label_ids IS '逗號分隔的標籤識別碼';
COMMENT ON COLUMN tb_products.cost IS '成本';
COMMENT ON COLUMN tb_products.price IS '售價';
COMMENT ON COLUMN tb_products.delete_flag IS '軟刪除旗標';
COMMENT ON COLUMN tb_products.created_uid IS '建立者 UID';
COMMENT ON COLUMN tb_products.created_at IS '建立時間';
COMMENT ON COLUMN tb_products.updated_uid IS '最後更新者 UID';
COMMENT ON COLUMN tb_products.updated_at IS '最後更新時間';
