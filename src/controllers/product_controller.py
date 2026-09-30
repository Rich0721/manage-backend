from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Response

from src.constants.product import ProductMessage
from src.constants.user import AuthStatus
from src.controllers.dependencies import ProductServiceDependency
from src.controllers.user_controller import build_envelope
from src.controllers.user_controller import error_responses
from src.controllers.user_controller import synchronize_authorization_header
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.product import AddProductRequest
from src.models.schemas.product import AddProductResponse
from src.models.schemas.product import DeleteProductRequest
from src.models.schemas.product import ProductListResponse
from src.models.schemas.product import UpdateProductRequest


router = APIRouter(prefix="/productController", tags=["Product Manager"])

UidHeader = Annotated[str, Header(alias="uid")]
AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]
ProductIdQuery = Annotated[
    str,
    Query(alias="productId", pattern=r"^(?:[Aa][Ll][Ll]|[0-9]{13})$"),
]


def header_auth(uid: str, authorization: str | None) -> AuthorizationObject:
    return AuthorizationObject(uid=uid, authorization=authorization)


def result_envelope(result: Any) -> dict[str, Any]:
    return build_envelope(
        status=AuthStatus.SUCCESS,
        message=ProductMessage.SUCCESS,
        info=result.info,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )


@router.post(
    "/addProduct",
    response_model=AddProductResponse,
    responses=error_responses(400, 401, 409, 422, 500, 503),
)
async def add_product(
    payload: AddProductRequest,
    response: Response,
    uid: UidHeader,
    service: ProductServiceDependency,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    result = await service.add(header_auth(uid, authorization), payload.body.info)
    synchronize_authorization_header(response, result.context.authorization)
    return result_envelope(result)


@router.get(
    "/getProducts",
    response_model=ProductListResponse,
    responses=error_responses(401, 404, 422, 500, 503),
)
async def get_products(
    product_id: ProductIdQuery,
    response: Response,
    uid: UidHeader,
    service: ProductServiceDependency,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    result = await service.get(header_auth(uid, authorization), product_id)
    synchronize_authorization_header(response, result.context.authorization)
    return result_envelope(result)


@router.put(
    "/updateProduct",
    response_model=ProductListResponse,
    responses=error_responses(400, 401, 404, 422, 500, 503),
)
async def update_product(
    payload: UpdateProductRequest,
    response: Response,
    uid: UidHeader,
    service: ProductServiceDependency,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    result = await service.update(
        header_auth(uid, authorization),
        payload.body.info,
    )
    synchronize_authorization_header(response, result.context.authorization)
    return result_envelope(result)


@router.delete(
    "/deleteProduct",
    response_model=ProductListResponse,
    responses=error_responses(401, 404, 422, 500, 503),
)
async def delete_product(
    payload: DeleteProductRequest,
    response: Response,
    uid: UidHeader,
    service: ProductServiceDependency,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    result = await service.delete(
        header_auth(uid, authorization),
        payload.body.info,
    )
    synchronize_authorization_header(response, result.context.authorization)
    return result_envelope(result)
