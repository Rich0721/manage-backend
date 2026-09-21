from pathlib import Path


DDL_PATH = Path("database/DDL/tables/TB_USERS.sql")


def test_users_ddl_contains_required_constraints() -> None:
    ddl = DDL_PATH.read_text(encoding="utf-8")

    assert "CREATE TABLE tb_users" in ddl
    assert "CONSTRAINT pk_tb_users PRIMARY KEY (uid)" in ddl
    assert "CONSTRAINT uk_tb_users_email UNIQUE (email)" in ddl
    assert "VARCHAR(64)" in ddl
    assert "CHECK (permission IN ('admin', 'manager', 'user'))" in ddl
    assert "created_at TIMESTAMP NOT NULL" in ddl
    assert "updated_at TIMESTAMP NOT NULL" in ddl
