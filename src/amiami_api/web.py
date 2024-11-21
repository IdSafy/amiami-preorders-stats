import asyncio

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from loguru import logger

from amiami_api.api import AmiAmiApi, Item, Order, OrderInfo, OrderType
from amiami_api.config import Config
from amiami_api.di import DIContainer
from amiami_api.store import AmiAmiOrdersStore

api_router = APIRouter(prefix="/api", tags=["api_root"])


@api_router.get("/orders/")
@inject
async def get_orders(
    order_type: OrderType = OrderType.open,
    store: AmiAmiOrdersStore = Depends(Provide[DIContainer.store]),
) -> list[OrderInfo]:
    return store.get_orders(order_type)


@api_router.get("/orders/{order_id}/")
@inject
async def get_order(
    order_id: str,
    store: AmiAmiOrdersStore = Depends(Provide[DIContainer.store]),
) -> OrderInfo:
    order = store.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")
    return order


@api_router.get("/items/")
@inject
async def get_items(
    store: AmiAmiOrdersStore = Depends(Provide[DIContainer.store]),
) -> list[Item]:
    items = []
    orders = store.get_orders()
    for order in orders:
        items.extend(order.items)
    return items


@api_router.post("/orders/update/")
@inject
async def update_orders(
    order_type: OrderType = OrderType.open,
    store: AmiAmiOrdersStore = Depends(Provide[DIContainer.store]),
    api: AmiAmiApi = Depends(Provide[DIContainer.api]),
) -> list[OrderInfo]:
    orders = await api.get_orders(order_type)
    semaphore = asyncio.Semaphore(3)

    async def fetch_order_info(order: Order) -> OrderInfo:
        async with semaphore:
            logger.info(f"Fetching order info for order {order.id}")
            return await api.get_order_info(order.id)

    fetch_order_info_tasks = [fetch_order_info(order) for order in orders]
    orders_info = await asyncio.gather(*fetch_order_info_tasks, return_exceptions=True)
    for order_info in orders_info:
        if isinstance(order_info, BaseException):
            logger.opt(exception=order_info).error("Error while fetching order info")
            continue
        store.update_order(order_info.id, order_info)
    return store.get_orders(order_type)


def create_app() -> FastAPI:
    container = DIContainer()
    container.config.from_dict(Config().model_dump())

    app = FastAPI()
    app.include_router(api_router)

    statics = StaticFiles(directory="frontend/dist/", html=True)

    app.mount("/", statics, name="static")
    return app


app = create_app()
