from datetime import datetime
from decimal import Decimal
from typing import Annotated, Generic, TypeVar

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    RootModel,
    StringConstraints,
    field_serializer,
    field_validator,
)

InfoT = TypeVar("InfoT")
ProductId = Annotated[str, StringConstraints(pattern=r"^\d{13}$")]
Money = Annotated[Decimal, Field(max_digits=10, decimal_places=2)]


class ProductBody(BaseModel, Generic[InfoT]):
    model_config = ConfigDict(extra="forbid")

    info: InfoT


class ProductEnvelope(BaseModel, Generic[InfoT]):
    model_config = ConfigDict(extra="forbid")

    headers: dict[str, str] = Field(default_factory=dict)
    body: ProductBody[InfoT]


class ProductWriteInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=255)
    label_names: str = Field(min_length=1)
    cost: Money
    price: Money

    @field_validator("label_names")
    @classmethod
    def validate_label_names(cls, value: str) -> str:
        names = [name.strip() for name in value.split(",")]
        if not all(names):
            raise ValueError("label_names must contain non-empty label names")
        return value


class ProductCreateInfo(ProductWriteInfo):
    pass


class ProductUpdateInfo(ProductWriteInfo):
    id: ProductId


class ProductDeleteInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: ProductId


class ProductCreateResponseInfo(BaseModel):
    id: ProductId
    name: str
    label_names: str
    cost: Decimal
    price: Decimal
    @field_serializer("cost", "price", when_used="json")
    def serialize_money(self, value: Decimal) -> float:
        return float(value)


class ProductResponseInfo(ProductCreateResponseInfo):
    delete_flag: bool
    updated_user: str
    updated_at: datetime


class ProductListResponseInfo(RootModel[list[ProductResponseInfo]]):
    pass


AddProductRequest = ProductEnvelope[ProductCreateInfo]
UpdateProductRequest = ProductEnvelope[ProductUpdateInfo]
DeleteProductRequest = ProductEnvelope[ProductDeleteInfo]
AddProductResponse = ProductEnvelope[ProductCreateResponseInfo]
ProductListResponse = ProductEnvelope[ProductListResponseInfo]
