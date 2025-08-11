import asyncio
from dataclasses import dataclass
from datetime import datetime

from loguru import logger

from amiami_api.api import AmiAmiApi, Order, OrderInfo, OrderType
from amiami_api.store import AmiAmiOrdersStore


@dataclass
class AmiamiService:
    api: AmiAmiApi
    store: AmiAmiOrdersStore
    update_parallelism: int = 3

    async def get_orders(self, order_type: OrderType) -> list[OrderInfo]:
        return self.store.get_orders(order_type)

    async def get_order(self, order_id: str) -> OrderInfo | None:
        return self.store.get_order(order_id)

    async def get_current_orders(self, include_finished: bool = True) -> list[OrderInfo]:
        orders = self.store.get_orders(OrderType.all)
        now = datetime.now()
        current_month = now.month
        previous_month = current_month - 1 if current_month > 1 else 12
        current_year = now.year

        def filter_func(order: OrderInfo) -> bool:
            if order.status == OrderType.shipped and not include_finished:
                return False
            return order.scheduled_release.month in [current_month, previous_month] and order.scheduled_release.year == current_year

        return list(filter(filter_func, orders))

    async def update_orders(self, order_type: OrderType) -> list[OrderInfo]:
        orders, all_orders = await asyncio.gather(self.api.get_orders(order_type), self.api.get_orders(OrderType.all))
        semaphore = asyncio.Semaphore(self.update_parallelism)

        async def fetch_order_info(order: Order) -> OrderInfo:
            async with semaphore:
                logger.info(f"Fetching order info for order {order.id}")
                return await self.api.get_order_info(order.id)

        fetch_order_info_tasks = [fetch_order_info(order) for order in orders]
        orders_info = await asyncio.gather(*fetch_order_info_tasks, return_exceptions=True)
        for order_info in orders_info:
            if isinstance(order_info, BaseException):
                logger.opt(exception=order_info).error("Error while fetching order info")
                continue
            self.store.update_order(order_info.id, order_info)

        self.store.clean_up_not_existing_orders([order.id for order in all_orders])

        return self.store.get_orders(order_type)
