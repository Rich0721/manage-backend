from enum import StrEnum


class OrderMessage(StrEnum):
    SUCCESS = "OK"
    BAD_REQUEST = "Bad Request"
    PRODUCT_NOT_FOUND = "商品不存在"
    ORDER_NOT_FOUND = "訂單不存在"
    START_DATE_REQUIRED = "請輸入查詢起始日期"
    END_DATE_REQUIRED = "請輸入查詢結束日期"
    DATE_RANGE_TOO_LONG = "查詢日期區間不得超過30天"
    SERVICE_UNAVAILABLE = "Order service unavailable"
