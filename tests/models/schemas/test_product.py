from decimal import Decimal

import pytest
from pydantic import ValidationError

from src.models.schemas.product import AddProductRequest
from src.models.schemas.product import ProductCreateResponseInfo


def test_product_request_preserves_body_auth_but_validates_info() -> None:
    request = AddProductRequest(
        body={
            "auth": {"uid": "untrusted"},
            "info": {
                "name": "Product",
                "label_names": " label1 , LABEL2 ",
                "cost": "100.00",
                "price": "150.00",
            },
        },
    )

    assert request.body.auth.uid == "untrusted"
    assert request.body.info.cost == Decimal("100.00")


@pytest.mark.parametrize("label_names", ["", " ", "one,,two", "one, "])
def test_empty_label_name_segment_is_rejected(label_names: str) -> None:
    with pytest.raises(ValidationError):
        AddProductRequest(
            body={
                "info": {
                    "name": "Product",
                    "label_names": label_names,
                    "cost": 100,
                    "price": 150,
                },
            },
        )


def test_product_response_serializes_money_as_json_number() -> None:
    response = ProductCreateResponseInfo(
        id="1790705105001",
        name="Product",
        label_names="label1,label2",
        cost=Decimal("100.00"),
        price=Decimal("150.00"),
    )

    assert response.model_dump(mode="json")["cost"] == 100.0

