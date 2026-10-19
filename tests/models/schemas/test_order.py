from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.models.schemas.order import SellOrderInfo
from src.models.schemas.order import SellOrderRequest
from src.models.schemas.order import SellOrderResponseInfo


def valid_request() -> dict[str, object]:
    return {
        "headers": {},
        "body": {
            "info": {
                "totalAmount": 800,
                "totalDiscount": 700,
                "orderItems": [
                    {
                        "productId": "1790705105001",
                        "quantity": 2,
                        "price": 150,
                        "discount": 150,
                    },
                    {
                        "productId": "1790705105002",
                        "quantity": 2,
                        "price": 250,
                        "discount": 200,
                    },
                ],
            },
        },
    }


def test_sell_order_schema_accepts_distinct_items_and_records_totals() -> None:
    request = SellOrderRequest.model_validate(valid_request())

    assert request.body.info.total_amount == Decimal("800")
    assert request.body.info.total_discount == Decimal("700")
    assert len(request.body.info.order_items) == 2


@pytest.mark.parametrize(
    "items",
    [
        [],
        [
            {
                "productId": "1790705105001",
                "quantity": 1,
                "price": 1,
                "discount": 1,
            },
            {
                "productId": "1790705105001",
                "quantity": 2,
                "price": 1,
                "discount": 1,
            },
        ],
    ],
)
def test_sell_order_rejects_empty_or_duplicate_items(
    items: list[dict[str, object]],
) -> None:
    payload = valid_request()
    body = payload["body"]
    assert isinstance(body, dict)
    info = body["info"]
    assert isinstance(info, dict)
    info["orderItems"] = items

    with pytest.raises(ValidationError):
        SellOrderRequest.model_validate(payload)


def test_sell_order_does_not_recalculate_discount_totals() -> None:
    info = SellOrderInfo.model_validate(
        {
            "totalAmount": 1200,
            "totalDiscount": 1,
            "orderItems": [
                {
                    "productId": "1790705105001",
                    "quantity": 1,
                    "price": 1200,
                    "discount": 900,
                },
            ],
        }
    )

    assert info.total_discount == Decimal("1")


def test_order_response_serializes_money_as_json_numbers() -> None:
    response = SellOrderResponseInfo.model_validate(
        {
            "orderId": "0000000001",
            "totalAmount": Decimal("10.25"),
            "totalDiscount": Decimal("9.25"),
            "orderItems": [
                {
                    "productId": "1790705105001",
                    "quantity": 1,
                    "price": Decimal("10.25"),
                    "discount": Decimal("9.25"),
                },
            ],
        }
    )

    dumped = response.model_dump(by_alias=True, mode="json")
    assert dumped["totalAmount"] == 10.25
    assert dumped["orderItems"][0]["discount"] == 9.25
