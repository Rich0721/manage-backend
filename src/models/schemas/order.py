from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import RootModel
from pydantic import StringConstraints
from pydantic import field_serializer
from pydantic import field_validator


OrderId = Annotated[str, StringConstraints(pattern=r"^\d{10}$")]
ProductId = Annotated[str, StringConstraints(pattern=r"^\d{13}$")]
Money = Annotated[Decimal, Field(ge=0, max_digits=10, decimal_places=2)]
Quantity = Annotated[int, Field(gt=0, strict=True)]


class OrderBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    info: object


class OrderEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headers: dict[str, str] = Field(default_factory=dict)
    body: OrderBody


class SellOrderItemInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    product_id: ProductId = Field(alias="productId")
    quantity: Quantity
    price: Money
    discount: Money


class SellOrderInfo(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    total_amount: Money = Field(alias="totalAmount")
    total_discount: Money = Field(alias="totalDiscount")
    order_items: list[SellOrderItemInfo] = Field(
        alias="orderItems",
        min_length=1,
    )

    @field_validator("order_items")
    @classmethod
    def validate_unique_products(
        cls,
        items: list[SellOrderItemInfo],
    ) -> list[SellOrderItemInfo]:
        product_ids = [item.product_id for item in items]
        if len(product_ids) != len(set(product_ids)):
            raise ValueError("orderItems must not contain duplicate productId")
        return items


class SellOrderResponseItem(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: ProductId = Field(alias="productId")
    quantity: int
    price: Decimal
    discount: Decimal

    @field_serializer("price", "discount", when_used="json")
    def serialize_money(self, value: Decimal) -> float:
        return float(value)


class SellOrderResponseInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: OrderId = Field(alias="orderId")
    total_amount: Decimal = Field(alias="totalAmount")
    total_discount: Decimal = Field(alias="totalDiscount")
    order_items: list[SellOrderResponseItem] = Field(alias="orderItems")

    @field_serializer("total_amount", "total_discount", when_used="json")
    def serialize_totals(self, value: Decimal) -> float:
        return float(value)


class GetOrderItemInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    product_id: ProductId = Field(alias="productId")
    product_name: str = Field(alias="productName")
    quantity: int
    price: Decimal
    discount: Decimal

    @field_serializer("price", "discount", when_used="json")
    def serialize_money(self, value: Decimal) -> float:
        return float(value)


class GetOrderInfo(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    order_id: OrderId = Field(alias="orderId")
    total_amount: Decimal = Field(alias="totalAmount")
    total_discount: Decimal = Field(alias="totalDiscount")
    created_at: datetime = Field(alias="createdAt")
    created_by: str = Field(alias="createdBy")
    order_items: list[GetOrderItemInfo] = Field(alias="orderItems")

    @field_serializer("total_amount", "total_discount", when_used="json")
    def serialize_totals(self, value: Decimal) -> float:
        return float(value)

    @field_serializer("created_at", when_used="json")
    def serialize_created_at(self, value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M:%S")


class GetOrdersResponseInfo(RootModel[list[GetOrderInfo]]):
    pass


class SellOrderRequest(OrderEnvelope):
    body: "SellOrderBody"


class SellOrderBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    info: SellOrderInfo


class SellOrderResponse(OrderEnvelope):
    body: "SellOrderResponseBody"


class SellOrderResponseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    info: SellOrderResponseInfo


class GetOrdersResponse(OrderEnvelope):
    body: "GetOrdersResponseBody"


class GetOrdersResponseBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    info: GetOrdersResponseInfo
