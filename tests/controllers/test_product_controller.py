from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.controllers.dependencies import get_product_service
from src.main import create_app
from src.models.schemas.product import ProductCreateResponseInfo
from src.models.schemas.product import ProductListResponseInfo
from src.models.schemas.product import ProductResponseInfo
from src.services.authorization_service import AuthorizationContext
from src.services.product_service import ProtectedProductResult


class TestSettings(object):
    REDIS_TTL = 300
    SECRET_KEY = "s" * 64
    DEBUG = True


class FakeManager(object):
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
    app.dependency_overrides[get_product_service] = lambda: service
    return TestClient(app, raise_server_exceptions=False)


def test_add_product_uses_headers_and_ignores_body_auth() -> None:
    service = AsyncMock()
    service.add.return_value = ProtectedProductResult(
        context=AuthorizationContext("header-user", "Bearer renewed", False),
        info=ProductCreateResponseInfo(
            id="1790705105001",
            name="Product",
            label_names="label1",
            cost=100,
            price=150,
        ),
    )
    payload = {
        "body": {
            "auth": {"uid": "body-user", "authorization": "body-token"},
            "info": {
                "name": "Product",
                "label_names": "label1",
                "cost": 100,
                "price": 150,
            },
        },
    }

    with make_client(service) as client:
        response = client.post(
            "/productController/addProduct",
            headers={"uid": "header-user", "Authorization": "Bearer request"},
            json=payload,
        )

    assert response.status_code == 200
    assert response.headers["Authorization"] == "Bearer renewed"
    auth = service.add.await_args.args[0]
    assert auth.uid == "header-user"
    assert auth.authorization == "Bearer request"
    assert response.json()["body"]["info"] == {
        "id": "1790705105001",
        "name": "Product",
        "label_names": "label1",
        "cost": 100.0,
        "price": 150.0,
    }


def test_get_products_rejects_invalid_product_id_before_service() -> None:
    service = AsyncMock()

    with make_client(service) as client:
        response = client.get(
            "/productController/getProducts?productId=invalid",
            headers={"uid": "header-user"},
        )

    assert response.status_code == 422
    service.get.assert_not_awaited()


def test_get_update_and_delete_routes_return_product_lists() -> None:
    service = AsyncMock()
    result = ProtectedProductResult(
        context=AuthorizationContext("header-user", "Bearer renewed", False),
        info=ProductListResponseInfo(
            [
                ProductResponseInfo(
                    id="1790705105001",
                    name="Product",
                    label_names="label1",
                    cost=100,
                    price=150,
                    delete_flag=False,
                    updated_user="header-user",
                    updated_at="2026-01-01T00:00:00",
                ),
            ],
        ),
    )
    service.get.return_value = result
    service.update.return_value = result
    service.delete.return_value = result
    requests = [
        (
            "get",
            "/productController/getProducts?productId=ALL",
            None,
        ),
        (
            "put",
            "/productController/updateProduct",
            {
                "body": {
                    "info": {
                        "id": "1790705105001",
                        "name": "Product",
                        "label_names": "label1",
                        "cost": 100,
                        "price": 150,
                    },
                },
            },
        ),
        (
            "delete",
            "/productController/deleteProduct",
            {"body": {"info": {"id": "1790705105001"}}},
        ),
    ]

    with make_client(service) as client:
        for method, url, payload in requests:
            response = client.request(
                method,
                url,
                headers={"uid": "header-user"},
                json=payload,
            )
            assert response.status_code == 200
            assert response.json()["body"]["info"][0]["id"] == (
                "1790705105001"
            )
