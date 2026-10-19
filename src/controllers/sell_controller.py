from typing import Annotated, Any

from fastapi import APIRouter, Header, Query, Response

from src.constants.order import OrderMessage
from src.constants.user import AuthStatus
from src.controllers.dependencies import SellServiceDependency
from src.controllers.user_controller import build_envelope
from src.controllers.user_controller import error_responses
from src.controllers.user_controller import synchronize_authorization_headers
from src.models.schemas.authorization import AuthorizationObject
from src.models.schemas.order import GetOrdersResponse
from src.models.schemas.order import SellOrderRequest
from src.models.schemas.order import SellOrderResponse


router = APIRouter(prefix="/sellController", tags=["Sell Product"])
UidHeader = Annotated[str | None, Header(alias="Uid")]
AuthorizationHeader = Annotated[str | None, Header(alias="Authorization")]


def result_envelope(result: Any) -> dict[str, Any]:
    return build_envelope(
        status=AuthStatus.SUCCESS,
        message=OrderMessage.SUCCESS,
        info=result.info,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )


@router.post(
    "/sellProduct",
    response_model=SellOrderResponse,
    responses=error_responses(400, 401, 404, 503),
)
async def sell_product(
    payload: SellOrderRequest,
    response: Response,
    uid: UidHeader,
    service: SellServiceDependency,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    result = await service.sell(
        AuthorizationObject(uid=uid, authorization=authorization),
        payload.body.info,
    )
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=OrderMessage.SUCCESS,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
    return result_envelope(result)


@router.get(
    "/getOrder",
    response_model=GetOrdersResponse,
    responses=error_responses(400, 401, 404, 503),
)
async def get_order(
    response: Response,
    uid: UidHeader,
    service: SellServiceDependency,
    order_id: Annotated[str, Query(alias="orderId")],
    start_date: Annotated[str | None, Query(alias="startDate")] = None,
    end_date: Annotated[str | None, Query(alias="endDate")] = None,
    authorization: AuthorizationHeader = None,
) -> dict[str, Any]:
    result = await service.get_order(
        AuthorizationObject(uid=uid, authorization=authorization),
        order_id,
        start_date,
        end_date,
    )
    synchronize_authorization_headers(
        response,
        status=AuthStatus.SUCCESS,
        message=OrderMessage.SUCCESS,
        uid=result.context.uid,
        authorization=result.context.authorization,
    )
    return result_envelope(result)
