# SQL Standard

這是一個 SQL 標準的說明文件。

## Table Naming Convention

1. 表頭皆已`tb_`開頭。
   例如：`tb_user_account`、`tb_order_detail`
2. 表名應使用小寫字母，單詞之間使用下劃線分隔。
   例如：`tb_user_account`、`tb_order_detail`
3. 表名應使用複數形式。
   例如：`tb_users`、`tb_orders`
4. 避免使用保留字作為表名。
5. 表名應具有描述性，能清楚表達表的用途。
6. 需使用comments對表進行描述。
   例如：`COMMENT '用戶帳號表'`
7. 檔案命名以TABLE NAME命名，使用大寫字母，單詞之間使用下劃線分隔。
   例如：`TB_USER_ACCOUNT.sql`、`TB_ORDER_DETAIL.sql`

## Column Naming Convention

1. 列名應使用小寫字母，單詞之間使用下劃線分隔。
   例如：`user_id`、`order_date`
2. 主鍵列應命名為`id`。
   例如：`id`
3. 外鍵列應以參照的表名加上`_id`結尾。
   例如：`user_id`、`order_id`
4. 避免使用保留字作為列名。
5. 列名應具有描述性，能清楚表達列的用途。
6. 需使用comments對列進行描述。
   例如：`COMMENT '用戶ID'`

## Index Naming Convention

1. 索引名應以`idx_`開頭，後接表名和列名。
   例如：`idx_user_account_user_id`、`idx_order_detail_order_id`
2. 索引名應使用小寫字母，單詞之間使用下劃線分隔。
3. 避免使用保留字作為索引名。
4. 索引名應具有描述性，能清楚表達索引的用途。
5. 需判斷idx有效性，避免過渡建立無用索引。
6. 同一張表建立多個索引時，應避免重複索引，且需要生成在同一個檔案中。
7. 檔案命名以TABLE NAME命名，使用大寫字母，單詞之間使用下劃線分隔。
   例如：`TB_USER_ACCOUNT.sql`、`TB_ORDER_DETAIL.sql`

## Timesheet

1. 時間列應使用小寫字母，單詞之間使用下劃線分隔。
   例如：`created_at`、`updated_at`
2. 時間列應使用`DATETIME`或`TIMESTAMP`類型。
3. 時間列應具有描述性，能清楚表達列的用途。
4. 需使用comments對時間列進行描述。
   例如：`COMMENT '創建時間'`
5. 由`insert`或`update`進行生成或更新，請勿使用`DEFAULT`。

## Database Architecture
```text
project/
├── database/
│   ├── DDL/
│   |    ├── tables/
│   |    └── indexes/
│   └── DML/
├── src/
└── tests/
```

資料庫Table應遵循上述的命名規範，並且每個Table應對應一個DDL檔案，存放於`database/DDL/tables/`目錄下。每個索引應對應一個索引檔案，存放於`database/DDL/indexes/`目錄下。
DML僅以初始資料填充為主，存放於`database/DML/`目錄下。