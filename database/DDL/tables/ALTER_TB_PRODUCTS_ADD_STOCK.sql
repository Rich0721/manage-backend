ALTER TABLE tb_products
    ADD COLUMN IF NOT EXISTS stock INTEGER;

UPDATE tb_products
   SET stock = 0
 WHERE stock IS NULL;

ALTER TABLE tb_products
    ALTER COLUMN stock SET DEFAULT 0,
    ALTER COLUMN stock SET NOT NULL;

COMMENT ON COLUMN tb_products.stock IS 'Product stock quantity';
