CREATE SEQUENCE seq_tb_orders_id
    START WITH 1
    INCREMENT BY 1
    MINVALUE 1
    MAXVALUE 9999999999
    NO CYCLE;

CREATE TABLE tb_orders (
    id VARCHAR(10) NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    total_discount NUMERIC(10, 2) NOT NULL,
    created_uid VARCHAR(256) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    CONSTRAINT pk_tb_orders PRIMARY KEY (id),
    CONSTRAINT ck_tb_orders_id_format CHECK (id ~ '^[0-9]{10}$'),
    CONSTRAINT fk_tb_orders_created_uid
        FOREIGN KEY (created_uid) REFERENCES tb_users (uid)
);

COMMENT ON TABLE tb_orders IS 'Completed sales orders';
COMMENT ON COLUMN tb_orders.id IS 'Zero-padded 10-digit order identifier';
COMMENT ON COLUMN tb_orders.total_amount IS 'Order total amount before discount';
COMMENT ON COLUMN tb_orders.total_discount IS 'Order total after discount';
COMMENT ON COLUMN tb_orders.created_uid IS 'UID of the order creator';
COMMENT ON COLUMN tb_orders.created_at IS 'UTC order creation timestamp';
