from abc import ABC
from dataclasses import dataclass, field
from pathlib import Path

from loguru import logger
from pydantic import TypeAdapter

from amiami_api.api import ApiOrderInfo


class AmiAmiOrdersStore(ABC):
    def get_order(self, order_id: str) -> ApiOrderInfo | None:
        raise NotImplementedError

    def get_orders(self) -> list[ApiOrderInfo]:
        raise NotImplementedError

    def add_order(self, order: ApiOrderInfo) -> None:
        raise NotImplementedError

    def update_order(self, order_id: str, order: ApiOrderInfo) -> None:
        raise NotImplementedError

    def delete_order(self, order_id: str) -> None:
        raise NotImplementedError


@dataclass
class AmiAmiOrdersMemoryStore(AmiAmiOrdersStore):
    _orders: dict[str, ApiOrderInfo] = field(default_factory=dict, init=False)

    def get_order(self, order_id: str) -> ApiOrderInfo | None:
        return self._orders.get(order_id)

    def get_orders(self) -> list[ApiOrderInfo]:
        return list(self._orders.values())

    def add_order(self, order: ApiOrderInfo) -> None:
        self._orders[order.d_no] = order

    def update_order(self, order_id: str, order: ApiOrderInfo) -> None:
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
                self._orders = TypeAdapter(dict[str, ApiOrderInfo]).validate_json(file.read())
        except FileNotFoundError:
            logger.warning("File not found")
        except Exception as exception:
            logger.opt(exception=exception).error("Failed to load data from file")

    def _save(self) -> None:
        try:
            with open(self.file_path, "wb") as file:
                file.write(TypeAdapter(dict[str, ApiOrderInfo]).dump_json(self._orders, indent=2))
        except Exception as exception:
            logger.opt(exception=exception).error("Failed to save data to file")

    def add_order(self, order: ApiOrderInfo) -> None:
        super().add_order(order)
        self._save()

    def update_order(self, order_id: str, order: ApiOrderInfo) -> None:
        super().update_order(order_id, order)
        self._save()

    def delete_order(self, order_id: str) -> None:
        super().delete_order(order_id)
        self._save()
