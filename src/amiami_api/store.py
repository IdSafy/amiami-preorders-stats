from abc import ABC
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from loguru import logger
from pydantic import TypeAdapter

from amiami_api.api import OrderInfo, OrderType


class AmiAmiOrdersStore(ABC):
    def get_order(self, order_id: str) -> OrderInfo | None:
        raise NotImplementedError

    def get_orders(self, order_type: OrderType = OrderType.all) -> list[OrderInfo]:
        raise NotImplementedError

    def add_order(self, order: OrderInfo) -> None:
        raise NotImplementedError

    def update_order(self, order_id: str, order: OrderInfo) -> None:
        raise NotImplementedError

    def delete_order(self, order_id: str) -> None:
        raise NotImplementedError

    def clean_up_not_existing_orders(self, existing_orders: list[str]) -> None:
        orders = self.get_orders()
        for order in orders:
            if order.id not in existing_orders:
                self.delete_order(order.id)


@dataclass
class AmiAmiOrdersMemoryStore(AmiAmiOrdersStore):
    _orders: dict[str, OrderInfo] = field(default_factory=dict, init=False)

    def get_order(self, order_id: str) -> OrderInfo | None:
        return self._orders.get(order_id)

    def get_orders(self, order_type: OrderType = OrderType.all) -> list[OrderInfo]:
        all_orders = list(self._orders.values())
        match order_type:
            case OrderType.all:
                return all_orders
            case OrderType.open:
                return [order for order in all_orders if order.is_open()]
            case OrderType.shipped:
                return [order for order in all_orders if not order.is_open()]
            case OrderType.current_month:
                # less or equal because sometime there are delays
                return [order for order in all_orders if order.is_open() and order.scheduled_release <= date.today()]

    def add_order(self, order: OrderInfo) -> None:
        self._orders[order.id] = order

    def update_order(self, order_id: str, order: OrderInfo) -> None:
        self._orders[order_id] = order

    def delete_order(self, order_id: str) -> None:
        if order_id in self._orders:
            del self._orders[order_id]


@dataclass
class AmiAmiOrdersFileStore(AmiAmiOrdersMemoryStore):
    file_path: Path

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        try:
            with open(self.file_path, "rb") as file:
                self._orders = TypeAdapter(dict[str, OrderInfo]).validate_json(file.read())
        except FileNotFoundError:
            logger.warning("File not found")
        except Exception as exception:
            logger.opt(exception=exception).error("Failed to load data from file")

    def _save(self) -> None:
        try:
            with open(self.file_path, "wb") as file:
                file.write(TypeAdapter(dict[str, OrderInfo]).dump_json(self._orders, indent=2))
        except Exception as exception:
            logger.opt(exception=exception).error("Failed to save data to file")

    def add_order(self, order: OrderInfo) -> None:
        super().add_order(order)
        self._save()

    def update_order(self, order_id: str, order: OrderInfo) -> None:
        super().update_order(order_id, order)
        self._save()

    def delete_order(self, order_id: str) -> None:
        super().delete_order(order_id)
        self._save()
