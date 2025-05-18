from contextlib import asynccontextmanager
from typing import AsyncGenerator

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from amiami_api.api import Item, OrderInfo, OrderType
from amiami_api.config import Config
from amiami_api.di import DIContainer
from amiami_api.service import AmiamiService

api_router = APIRouter(prefix="/api", tags=["api_root"])


@api_router.get("/orders/")
@inject
async def get_orders(
    order_type: OrderType = OrderType.open,
    service: AmiamiService = Depends(Provide[DIContainer.service]),
) -> list[OrderInfo]:
    return await service.get_orders(order_type)


@api_router.get("/orders/{order_id}/")
@inject
async def get_order(
    order_id: str,
    service: AmiamiService = Depends(Provide[DIContainer.service]),
) -> OrderInfo:
    order = await service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@api_router.get("/items/")
@inject
async def get_items(
    service: AmiamiService = Depends(Provide[DIContainer.service]),
) -> list[Item]:
    items: list[Item] = []
    orders = await service.get_orders(OrderType.all)
    for order in orders:
        items.extend(order.items)
    return items


@api_router.post("/orders/update/")
@inject
async def update_orders(
    order_type: OrderType = OrderType.open,
    service: AmiamiService = Depends(Provide[DIContainer.service]),
) -> list[OrderInfo]:
    return await service.update_orders(order_type)


def create_app() -> FastAPI:
    container = DIContainer()
    container.config.from_dict(Config().model_dump())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        bot = container.telegram_bot()
        async with bot:
            await bot.start()
            assert bot.updater is not None
            await bot.updater.start_polling()
            yield
            await bot.stop()

    app = FastAPI(lifespan=lifespan)
    app.include_router(api_router)

    statics = StaticFiles(directory="frontend/dist/", html=True)
    app.mount("/", statics, name="static")
    return app


app = create_app()
