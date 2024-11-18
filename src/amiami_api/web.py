from enum import Enum

from dependency_injector.wiring import Provide, inject
from fastapi import APIRouter, Depends, FastAPI

from amiami_api.api import AmiAmiApi, ApiItem, ApiOrder, ApiOrderInfo, OrderType
from amiami_api.config import Config
from amiami_api.di import DIContainer
from amiami_api.store import AmiAmiOrdersStore

api_router = APIRouter(prefix="/api", tags=["api_root"])


class SaveMode(str, Enum):
    save = "save"
    no_save = "no_save"


@api_router.get("/orders/")
@inject
async def get_orders(order_type: OrderType = OrderType.open, api: AmiAmiApi = Depends(Provide[DIContainer.api])) -> list[ApiOrder]:
    orders = await api.get_orders(order_type=order_type)
    return orders


@api_router.get("/orders/{order_id}/")
@inject
async def get_order(
    order_id: str,
    save_mode: SaveMode = SaveMode.save,
    api: AmiAmiApi = Depends(Provide[DIContainer.api]),
    store: AmiAmiOrdersStore = Depends(Provide[DIContainer.store]),
) -> ApiOrderInfo:
    order_info = await api.get_order_info(order_id)
    if save_mode == SaveMode.save:
        store.update_order(order_id, order_info)
    return order_info


@api_router.get("/items/")
@inject
async def get_items(
    save_mode: SaveMode = SaveMode.save,
    order_type: OrderType = OrderType.open,
    api: AmiAmiApi = Depends(Provide[DIContainer.api]),
    store: AmiAmiOrdersStore = Depends(Provide[DIContainer.store]),
) -> list[ApiItem]:
    items = []
    orders = await api.get_orders(order_type=order_type)
    for order in orders:
        order_info = await api.get_order_info(order.d_no)
        if save_mode == SaveMode.save:
            store.update_order(order.d_no, order_info)
        items.extend(order_info.items)
    return items


def create_app() -> FastAPI:
    container = DIContainer()
    container.config.from_dict(Config().model_dump())

    app = FastAPI()
    app.include_router(api_router)
    return app


app = create_app()
