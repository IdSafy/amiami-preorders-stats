import logging
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Literal, TypeVar, cast

import aiohttp
from loguru import logger
from pydantic import BaseModel, TypeAdapter, ValidationInfo, field_validator

from amiami_api import utils

AMIAMI_STORE_BASE_URL = "https://www.amiami.com/"
AMIAMI_ACCOUNT_BASE_URL = "https://secure.amiami.com/"
AMIAMI_API_BASE_URL = "https://api-secure.amiami.com/api/v1.0/"


def amiami_month_date_validate(value: str | datetime | date) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value == "This Month":
        return date.today().replace(day=1)
    if value == "Before Last Month":
        today = date.today()
        before_last_month_month = (((today.month - 1) - 2) % 12) + 1
        before_last_month_year = today.year
        if before_last_month_month > today.month:
            before_last_month_year = today.year - 1
        return today.replace(day=1, month=before_last_month_month, year=before_last_month_year)
    last_token = value.split(" ")[-1]
    if last_token.find("/") != -1:
        return datetime.strptime(last_token, "%Y/%m")
    elif last_token.find("-") != -1 and len(last_token) == 10:
        return datetime.strptime(last_token, "%Y-%m-%d")
    else:
        return datetime.strptime(last_token, "%b-%Y")


class OrderCommon(BaseModel):
    d_no: str
    d_status: str
    scheduled_release: date
    subtotal: int

    @field_validator("scheduled_release", mode="before")
    def parse_scheduled_release(cls, value: str | datetime | date, info: ValidationInfo) -> date:
        return amiami_month_date_validate(value)

    @field_validator("d_status")
    def parse_d_status(cls, value: str, info: ValidationInfo) -> str:
        return value.rstrip()

    @property
    def is_open(self) -> bool:
        return self.d_status.lower() not in ["shipped", "cancelled"]


class ApiOrder(OrderCommon):
    scheduled_release: date
    mypage_lock_flg: int


class OrderWithItems(ApiOrder):
    items: list["ApiItem"]


class ApiItem(BaseModel):
    ds_no: str
    scode: str
    sname: str
    thumb_url: str  # "/images/product/thumb300/242/FIGURE-168653.jpg",
    thumb_alt: str  # "FIGURE-168653.jpg",
    thumb_title: (str)  # "Date A Live V Kurumi Tokisaki Wa-Bunny 1/7 Scale Figure[FURYU]",
    thumb_agelimit: int
    releasedate: date
    price: int
    amount: int
    stock_flg: int
    # max_cartin_count: None,
    # stock: None,
    # mixed_gcode: null,
    # mixed_message: null

    @field_validator("releasedate", mode="before")
    def parse_releasedate(cls, value: str | datetime | date) -> date:
        return amiami_month_date_validate(value)

    @property
    def page_link(self) -> str:
        return urllib.parse.urljoin(AMIAMI_STORE_BASE_URL, f"eng/detail?scode={self.scode}")


class ApiOrderInfo(OrderCommon):
    scheduled_release: date
    items: list[ApiItem]

    @property
    def page_link(self) -> str:
        return urllib.parse.urljoin(AMIAMI_ACCOUNT_BASE_URL, f"eng/bill/2?d_no={self.d_no}")


ItemType = TypeVar("ItemType")


class SearchResult(BaseModel):
    total_results: int


class BaseApiResponse(BaseModel):
    RSuccess: bool
    RValue: None | Any
    RMessage: Literal["OK"]
    search_result: SearchResult


class ApiOrdersResponse(BaseApiResponse):
    orders: list[ApiOrder]


class ApiOrderInfoResponse(BaseApiResponse):
    order: ApiOrderInfo


class OrderType(str, Enum):
    all = "str"
    open = "open"
    shipped = "shipped"
    current_month = "current_month"


MethodType = TypeVar("MethodType", bound=Callable)


def ensure_login_decorator(func: MethodType) -> MethodType:
    @wraps(func)
    async def wrapper(self: "AmiAmiApi", *args, **kwargs):
        if self._login_data is None:
            await self._login()
        try:
            return await func(self, *args, **kwargs)
        except Exception:
            logger.warning("Request failed, try re-login")
            await self._login()
            return await func(self, *args, **kwargs)

    return cast(MethodType, wrapper)


@dataclass
class AmiAmiApi:
    username: str
    password: str
    api_root_url: str = AMIAMI_API_BASE_URL
    _session: aiohttp.ClientSession = field(init=False)
    _login_data: dict | None = field(default=None, init=False)

    def __post_init__(self):
        self._session = aiohttp.ClientSession(
            headers={
                "X-User-Key": "amiami_dev",
            },
        )

    @staticmethod
    def _get_status_ids_from_order_type(order_type: OrderType) -> str:
        return {
            OrderType.all: "1,2,3,4,5,6,7,10,999",
            OrderType.open: "1,2,5,6,7,10,999",
            OrderType.shipped: "3,4",
            OrderType.current_month: "1,2,5,6,7,10,999",  # same as open
        }[order_type]

    async def _login(self) -> bool:
        login_request_data = {
            "lang": "eng",
            "email": self.username,
            "password": self.password,
            "c_ransu": None,
        }

        response = await self._session.post(
            url=urllib.parse.urljoin(self.api_root_url, "login"),
            data=login_request_data,
        )
        try:
            json_response = await response.json()
            assert isinstance(json_response, dict)
            if json_response.get("RSuccess", False):
                self._login_data = await response.json()
                logging.info("Login successfull")
                assert self._login_data is not None
                self._session.headers.update(
                    {
                        "X-Authorization": f"bearer {self._login_data['login']['token']}",
                    }
                )
                return True

            error_message = (await response.json())["RMessage"]
        except Exception:
            error_message = response.status
        logging.error(f"Login failed: {error_message}")
        return False

    @ensure_login_decorator
    async def get_orders(self, order_type: OrderType = OrderType.all) -> list[ApiOrder]:
        orders: list[ApiOrder] = []
        params: dict[str, str | int] = {
            "status_ids": self._get_status_ids_from_order_type(order_type),
            "search_key": "id",
            "pagemax": 20,
            "lang": "eng",
            "pagecnt": 1,
        }
        while True:
            response = await self._session.get(
                url=urllib.parse.urljoin(self.api_root_url, "orders"),
                params=params,
            )
            api_orders_response = TypeAdapter(ApiOrdersResponse).validate_python(await response.json())
            orders += api_orders_response.orders
            if len(orders) == api_orders_response.search_result.total_results:
                break
            assert isinstance(params["pagecnt"], int)
            params["pagecnt"] += 1
        if order_type == OrderType.current_month:
            first_day_of_next_month = utils.first_day_of_next_month()
            orders = [order for order in orders if order.scheduled_release < first_day_of_next_month]
        return orders

    @ensure_login_decorator
    async def get_order_info(self, order_number: str) -> ApiOrderInfo:
        response = await self._session.get(
            url=urllib.parse.urljoin(self.api_root_url, "orders/detail"),
            params={
                "d_no": order_number,
                "lang": "eng",
            },
        )
        api_order_info = TypeAdapter(ApiOrderInfoResponse).validate_python(await response.json())
        return api_order_info.order
