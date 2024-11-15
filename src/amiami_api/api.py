import logging
import urllib.parse
from datetime import date, datetime
from enum import Enum
from typing import Any, Literal, TypeVar

import requests
from pydantic import BaseModel, TypeAdapter, ValidationInfo, field_validator

AMIAMI_STORE_BASE_URL = "https://www.amiami.com/"
AMIAMI_ACCOUNT_BASE_URL = "https://secure.amiami.com/"
AMIAMI_API_BASE_URL = "https://api-secure.amiami.com/api/v1.0/"


def amiami_month_date_validate(value: str) -> date:
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
    def parse_scheduled_release(cls, value: str, info: ValidationInfo) -> date:
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
    def parse_releasedate(cls, value: str):
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

    # "d_no": "226318854",
    #         "order_type": 1,
    #         "status": {
    #             "id": 6,
    #             "name": "New order\n"
    #         },
    #         "order_date": "2024-04-10T12:18:14.780634",
    #         "scheduled_release": "Feb-2025",
    #         "d_status": "New order\n",
    #         "settlement_continuable": false,
    #         "convinience_settlement_continuable": false,
    #         "mypage_lock_flg": 0,
    #         "payment_method": {
    #             "id": 1,
    #             "name": "Credit card"
    #         },
    #         "payment_method_before": {
    #             "id": null,
    #             "name": null
    #         },
    #         "shipping_method": {
    #             "id": 17,
    #             "name": "Air Small Packet (Registered)"
    #         },
    #         "shipping_address_type": 1,
    #         "shipping_address": {
    #             "lname": "*",
    #             "fname": "*",
    #             "country": {
    #                 "id": "398",
    #                 "name": "*",
    #                 "gst_tax_rate": 0
    #             },
    #             "zip": null,
    #             "state": null,
    #             "city": "*",
    #             "address": "*",
    #             "taddress": null,
    #             "tel": "*"
    #         },
    #         "send_time": {
    #             "id": null,
    #             "name": null
    #         },
    #         "send_day": {
    #             "id": null,
    #             "name": null
    #         },
    #         "send_date": null,
    #         "sendno": null,
    #         "shipdate": null,
    #         "shipping_date": null,
    #         "subtotal": 25850,
    #         "carriage": null,
    #         "discount_carriage": 0,
    #         "adj": 0,
    #         "yahoo_p_service": 0,
    #         "rakuten_p_service": 0,
    #         "gst_cost": 0,
    #         "gst_enable": 0,
    #         "point_earned": 259,
    #         "point_input": 0,
    #         "total": 25850,
    #         "selectable_shipping_methods": [],
    #         "items": [
    #             {
    #                 "ds_no": "226318854_0",
    #                 "scode": "FIGURE-168653",
    #                 "sname": "Date A Live V Kurumi Tokisaki Wa-Bunny 1/7 Scale Figure(Pre-order)",
    #                 "thumb_url": "/images/product/thumb300/242/FIGURE-168653.jpg",
    #                 "thumb_alt": "FIGURE-168653.jpg",
    #                 "thumb_title": "Date A Live V Kurumi Tokisaki Wa-Bunny 1/7 Scale Figure[FURYU]",
    #                 "thumb_agelimit": 0,
    #                 "releasedate": "Feb-2025",
    #                 "price": 25850,
    #                 "amount": 1,
    #                 "stock_flg": 0,
    #                 "max_cartin_count": null,
    #                 "stock": null,
    #                 "mixed_gcode": null,
    #                 "mixed_message": null
    #             }
    #         ]
    #     }


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


class OrderType(str, Enum):
    all = "str"
    open = "open"
    shipped = "shipped"


class AmiAmiApi:
    api_root_url: str = AMIAMI_API_BASE_URL
    session: requests.Session
    login_data: dict | None = None

    def __init__(self) -> None:
        self.session = requests.Session()

    def _get_headers(self) -> dict[str, str]:
        headers = {
            "X-User-Key": "amiami_dev",
        }
        if self.login_data is not None:
            headers.update(
                {
                    "X-Authorization": f"bearer {self.login_data['login']['token']}",
                }
            )
        return headers

    @staticmethod
    def _get_status_ids_from_order_type(order_type: OrderType) -> str:
        return {
            OrderType.all: "1,2,3,4,5,6,7,10,999",
            OrderType.open: "1,2,5,6,7,10,999",
            OrderType.shipped: "3,4",
        }[order_type]

    def login(self, login: str, password: str) -> bool:
        login_data = {
            "lang": "eng",
            "email": login,
            "password": password,
            "c_ransu": None,
        }
        response = self.session.post(
            url=urllib.parse.urljoin(self.api_root_url, "login"),
            headers=self._get_headers(),
            data=login_data,
        )
        try:
            json_response = response.json()
            assert isinstance(json_response, dict)
            if json_response.get("RSuccess", False):
                self.login_data = response.json()
                logging.info("Login successfull")
                return True

            error_message = response.json()["RMessage"]
        except Exception:
            error_message = response.status_code
        logging.info(f"Login failed: {error_message}")
        return False

    def get_orders(self, order_type: OrderType = OrderType.all) -> list[ApiOrder]:
        all_orders: list[ApiOrder] = []
        params: dict[str, str | int] = {
            "status_ids": self._get_status_ids_from_order_type(order_type),
            "search_key": "id",
            "pagemax": 20,
            "lang": "eng",
            "pagecnt": 1,
        }
        while True:
            response = requests.get(
                url=urllib.parse.urljoin(self.api_root_url, "orders"),
                headers=self._get_headers(),
                params=params,
            )
            response_object = TypeAdapter(ApiOrdersResponse).validate_python(response.json())
            all_orders += response_object.orders
            if len(all_orders) == response_object.search_result.total_results:
                break
            assert isinstance(params["pagecnt"], int)
            params["pagecnt"] += 1
        return all_orders

    def get_order_info(self, order_number: str) -> ApiOrderInfo:
        response = requests.get(
            url=urllib.parse.urljoin(self.api_root_url, "orders/detail"),
            headers=self._get_headers(),
            params={
                "d_no": order_number,
                "lang": "eng",
            },
        )
        order_info = TypeAdapter(ApiOrderInfo).validate_python(response.json()["order"])
        return order_info
