from unittest.mock import AsyncMock
from urllib.parse import unquote

from fastapi.testclient import TestClient
import pytest

from src.constants.product import ProductMessage
from src.constants.user import AuthStatus
from src.controllers.dependencies import get_product_service
from src.main import create_app
from src.models.schemas.product import ProductCreateResponseInfo
from src.models.schemas.product import ProductListResponseInfo
from src.models.schemas.product import ProductResponseInfo
from src.services.authorization_service import AuthorizationContext
from src.services.product_service import ProtectedProductResult
from src.services.product_errors import ProductCacheUnavailableError
from src.services.product_errors import ProductConflictError
from src.services.product_errors import ProductLabelNotFoundError
from src.services.product_errors import ProductNotFoundError
from src.services.product_errors import ProductPermissionError
from src.constants.user import UserMessage


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


def test_add_product_uses_headers_without_body_auth() -> None:
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
    assert response.headers["Status"] == AuthStatus.SUCCESS
    assert unquote(response.headers["Message"]) == ProductMessage.SUCCESS
    assert response.headers["Uid"] == "header-user"
    assert response.headers["Authorization"] == "Bearer renewed"
    auth = service.add.await_args.args[0]
    assert auth.uid == "header-user"
    assert auth.authorization == "Bearer request"
    assert response.json()["header"] == {
        "Status": AuthStatus.SUCCESS,
        "Message": ProductMessage.SUCCESS,
        "Uid": "header-user",
        "Authorization": "Bearer renewed",
    }
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


def test_add_product_does_not_use_json_header_as_authorization() -> None:
    service = AsyncMock()
    payload = {
        "header": {
            "Uid": "json-user",
            "Authorization": "Bearer json-token",
        },
        "body": {
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
            json=payload,
        )

    assert response.status_code == 422
    service.add.assert_not_awaited()


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
            assert response.headers["Status"] == AuthStatus.SUCCESS
            assert unquote(response.headers["Message"]) == (
                ProductMessage.SUCCESS
            )
            assert response.json()["body"]["info"][0]["id"] == (
                "1790705105001"
            )


@pytest.mark.parametrize(
    (
        "method",
        "url",
        "payload",
        "service_method",
        "error",
        "status",
        "auth_status",
        "message",
    ),
    [
        (
            "post",
            "/productController/addProduct",
            {
                "body": {
                    "info": {
                        "name": "Product",
                        "label_names": "label1",
                        "cost": 100,
                        "price": 150,
                    },
                },
            },
            "add",
            ProductLabelNotFoundError(),
            400,
            AuthStatus.SUCCESS,
            ProductMessage.LABEL_NOT_FOUND,
        ),
        (
            "get",
            "/productController/getProducts?productId=ALL",
            None,
            "get",
            ProductPermissionError(),
            401,
            AuthStatus.UNAUTHORIZED,
            ProductMessage.UNAUTHORIZED,
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
            "update",
            ProductNotFoundError(),
            404,
            AuthStatus.SUCCESS,
            ProductMessage.NOT_FOUND,
        ),
        (
            "post",
            "/productController/addProduct",
            {
                "body": {
                    "info": {
                        "name": "Product",
                        "label_names": "label1",
                        "cost": 100,
                        "price": 150,
                    },
                },
            },
            "add",
            ProductConflictError(),
            409,
            AuthStatus.SUCCESS,
            ProductMessage.CONFLICT,
        ),
        (
            "delete",
            "/productController/deleteProduct",
            {"body": {"info": {"id": "1790705105001"}}},
            "delete",
            ProductCacheUnavailableError(),
            503,
            AuthStatus.SUCCESS,
            ProductMessage.CACHE_UNAVAILABLE,
        ),
        (
            "get",
            "/productController/getProducts?productId=ALL",
            None,
            "get",
            RuntimeError(),
            500,
            AuthStatus.FAILED,
            UserMessage.INTERNAL_ERROR,
        ),
    ],
)
def test_product_routes_map_service_errors_to_standard_envelopes(
    method: str,
    url: str,
    payload: dict[str, object] | None,
    service_method: str,
    error: Exception,
    status: int,
    auth_status: AuthStatus,
    message: str,
) -> None:
    service = AsyncMock()
    getattr(service, service_method).side_effect = error

    with make_client(service) as client:
        response = client.request(
            method,
            url,
            headers={"uid": "header-user"},
            json=payload,
        )

    assert response.status_code == status
    assert response.headers["Status"] == auth_status
    assert unquote(response.headers["Message"]) == message
    assert response.headers.get("Uid") is None
    assert response.headers.get("Authorization") is None
    assert response.json()["header"] == {
        "Status": auth_status,
        "Message": message,
    }
    assert response.json()["body"] == {
        "info": {},
    }
