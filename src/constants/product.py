from enum import StrEnum


class ProductMessage(StrEnum):
    SUCCESS = "OK"
    LABEL_NOT_FOUND = "Product label does not exist"
    NOT_FOUND = "Not Found"
    CONFLICT = "Conflict"
    UNAUTHORIZED = "Unauthorized"
    CACHE_UNAVAILABLE = "Product cache unavailable"


class ProductCacheKey(StrEnum):
    PRODUCTS = "products:info"
    LABELS = "product:labels"
