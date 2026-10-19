from unittest.mock import AsyncMock
from urllib.parse import unquote

from fastapi.testclient import TestClient
import pytest

from src.constants.user import AuthStatus
from src.controllers.dependencies import get_sell_service
from src.main import create_app
from src.models.po.order import OrderResult
from src.models.po.order import OrderItemResult
from src.models.schemas.order import GetOrdersResponseInfo
from src.services.authorization_service import AuthorizationContext
from src.services.order_errors import OrderNotFoundError
from src.services.order_errors import OrderBadRequestError
from src.services.order_errors import SoldProductNotFoundError
from src.services.sell_service import ProtectedOrderResult


class TestSettings:
    REDIS_TTL = 300
    SECRET_KEY = "s" * 64
    DEBUG = True


class FakeManager:
    def __init__(self, value: object) -> None:
        self.value = value

    async def __aenter__(self) -> object:
        return self.value

    async def __aexit__(self, *args: object) -> None:
        return None


def make_client(service: AsyncMock) -> TestClient:
    app = create_app(
        settings_factory=TestSettings,
        database_manager_factory=lambda settings: FakeManager(object()),
        redis_manager_factory=lambda settings: FakeManager(object()),
    )
    app.dependency_overrides[get_sell_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def test_sell_product_returns_order_envelope_and_auth_headers() -> None:
    service = AsyncMock()
    service.sell.return_value = ProtectedOrderResult(
        context=AuthorizationContext("seller", "token", False),
        info={
            "orderId": "0000000001",
            "totalAmount": 20,
            "totalDiscount": 15,
            "orderItems": [],
        },
    )
    payload = {
        "headers": {},
        "body": {
            "info": {
                "totalAmount": 20,
                "totalDiscount": 15,
                "orderItems": [
                    {
                        "productId": "1790705105001",
                        "quantity": 1,
                        "price": 20,
                        "discount": 15,
                    },
                ],
            },
        },
    }

    with make_client(service) as client:
        response = client.post(
            "/sellController/sellProduct",
            headers={"Uid": "seller", "Authorization": "token"},
            json=payload,
        )

    assert response.status_code == 200
    assert response.headers["Status"] == AuthStatus.SUCCESS
    assert response.headers["Uid"] == "seller"
    service.sell.assert_awaited_once()


def test_sell_validation_errors_are_400_and_existing_api_remains_422() -> None:
    service = AsyncMock()
    with make_client(service) as client:
        order_response = client.post(
            "/sellController/sellProduct",
            headers={"Uid": "seller"},
            json={"body": {"info": {"totalAmount": -1}}},
        )
        product_response = client.get(
            "/productController/getProducts?productId=invalid",
            headers={"Uid": "seller"},
        )

    assert order_response.status_code == 400
    assert unquote(order_response.headers["Message"]) == "Bad Request"
    assert product_response.status_code == 422
    service.sell.assert_not_awaited()


def test_get_order_not_found_returns_404_envelope() -> None:
    service = AsyncMock()
    service.get_order.side_effect = OrderNotFoundError

    with make_client(service) as client:
        response = client.get(
            "/sellController/getOrder?orderId=0000000001",
            headers={"Uid": "seller"},
        )

    assert response.status_code == 404
    assert unquote(response.headers["Message"]) == "訂單不存在"


def test_get_order_invalid_id_returns_400() -> None:
    service = AsyncMock()
    service.get_order.side_effect = OrderBadRequestError

    with make_client(service) as client:
        response = client.get(
            "/sellController/getOrder",
            headers={"Uid": "seller"},
            params={"orderId": "１２３４５６７８９０"},
        )

    assert response.status_code == 400


def test_missing_product_returns_400() -> None:
    service = AsyncMock()
    service.sell.side_effect = SoldProductNotFoundError
    payload = {
        "headers": {},
        "body": {
            "info": {
                "totalAmount": 20,
                "totalDiscount": 15,
                "orderItems": [
                    {
                        "productId": "1790705105001",
                        "quantity": 1,
                        "price": 20,
                        "discount": 15,
                    },
                ],
            },
        },
    }

    with make_client(service) as client:
        response = client.post(
            "/sellController/sellProduct",
            headers={"Uid": "seller"},
            json=payload,
        )

    assert response.status_code == 400
    assert unquote(response.headers["Message"]) == "商品不存在"
