from typing import Annotated

from fastapi import Depends
from fastapi import Request

from src.repositories.session_repository import SessionRepository
from src.repositories.product_cache_repository import ProductCacheRepository
from src.repositories.product_repository import ProductRepository
from src.repositories.user_repository import UserRepository
from src.services.authorization_service import AuthorizationService
from src.services.user_service import UserService
from src.services.product_service import ProductService


def get_user_service(request: Request) -> UserService:
    settings = request.app.state.settings
    sessions = SessionRepository(
        request.app.state.redis_client,
        settings.REDIS_TTL,
    )
    users = UserRepository(request.app.state.database_pool)
    authorization = AuthorizationService(settings, sessions)
    return UserService(settings, users, sessions, authorization)


UserServiceDependency = Annotated[UserService, Depends(get_user_service)]


def get_product_service(request: Request) -> ProductService:
    settings = request.app.state.settings
    users = UserRepository(request.app.state.database_pool)
    products = ProductRepository(request.app.state.database_pool)
    cache = ProductCacheRepository(request.app.state.redis_client)
    sessions = SessionRepository(request.app.state.redis_client, settings.REDIS_TTL)
    authorization = AuthorizationService(settings, sessions)
    return ProductService(settings, products, cache, users, authorization)


ProductServiceDependency = Annotated[
    ProductService,
    Depends(get_product_service),
]
