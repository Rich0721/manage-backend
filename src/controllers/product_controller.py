from typing import Annotated, Any

from fastapi import APIRouter, File, Header, Query, Response, UploadFile

from src.constants.product import ProductMessage
from src.constants.user import AuthStatus
from src.controllers.dependencies import ProductServiceDependency
from src.controllers.user_controller import build_envelope
from src.controllers.user_controller import build_http_authorization_headers
from src.controllers.user_controller import error_responses
from src.controllers.user_controller import synchronize_authorization_headers
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.product import AddProductRequest
from src.models.schemas.product import AddProductResponse
from src.models.schemas.product import DownloadProductRequest
from src.models.schemas.product import DeleteProductRequest
from src.models.schemas.product import ProductListResponse
from src.models.schemas.product import UpdateProductRequest
from src.services.product_errors import ProductBatchError


router = APIRouter(prefix="/productController", tags=["Product Manager"])
EXCEL_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

UidHeader = Annotated[str, Header(alias="Uid")]
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


def excel_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    responses = error_responses(*status_codes)
    responses[200]["content"] = {
        EXCEL_MEDIA_TYPE: {
            "schema": {"type": "string", "format": "binary"},
        },
    }
    return responses


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
    result = await service.add(
        header_auth(uid, authorization),
        payload.body.info,
    )
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=ProductMessage.SUCCESS,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
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
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=ProductMessage.SUCCESS,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
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
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=ProductMessage.SUCCESS,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
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
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=ProductMessage.SUCCESS,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
    return result_envelope(result)


@router.post(
    "/batchProducts",
    response_model=ProductListResponse,
    responses=error_responses(400, 401, 404, 422, 500, 503),
)
async def batch_products(
    response: Response,
    uid: UidHeader,
    service: ProductServiceDependency,
    file: UploadFile | None = File(default=None),
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    if file is None:
        raise ProductBatchError("檔案格式不正確，請上傳Excel檔案")
    result = await service.batch_products(
        header_auth(uid, authorization),
        file.filename or "",
        await file.read(),
    )
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=ProductMessage.SUCCESS,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
    return result_envelope(result)


@router.get(
    "/downloadTemplate",
    response_class=Response,
    responses=excel_responses(401, 422, 500, 503),
)
async def download_template(
    uid: UidHeader,
    service: ProductServiceDependency,
    authorization: AuthorizationHeader = None,
) -> Response:
    result = await service.download_template(header_auth(uid, authorization))
    headers = build_http_authorization_headers(
        status=AuthStatus.SUCCESS,
        message="OK",
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
    headers["Content-Disposition"] = (
        f'attachment; filename="{result.filename}"'
    )
    return Response(
        content=result.content,
        media_type=EXCEL_MEDIA_TYPE,
        headers=headers,
    )


@router.post(
    "/downloadProductData",
    response_class=Response,
    responses=excel_responses(400, 401, 404, 422, 500, 503),
)
async def download_product_data(
    payload: DownloadProductRequest,
    uid: UidHeader,
    service: ProductServiceDependency,
    authorization: AuthorizationHeader = None,
) -> Response:
    result = await service.download_product_data(
        header_auth(uid, authorization),
        payload.body.info,
    )
    headers = build_http_authorization_headers(
        status=AuthStatus.SUCCESS,
        message="OK",
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
    headers["Content-Disposition"] = (
        f'attachment; filename="{result.filename}"'
    )
    return Response(
        content=result.content,
        media_type=EXCEL_MEDIA_TYPE,
        headers=headers,
    )
