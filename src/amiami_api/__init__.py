import logging
from datetime import date, datetime

import requests
from pydantic import BaseModel, TypeAdapter, validator


def amiami_month_date_validate(value: str) -> date:
    if value == "This Month":
        return date.today().replace(day=1)
    last_token = value.split(" ")[-1]
    if last_token.find("/") != -1:
        return datetime.strptime(last_token, "%Y/%m")
    elif last_token.find("-") != -1 and len(last_token) == 10:
        return datetime.strptime(last_token, "%Y-%m-%d")
    else:
        return datetime.strptime(last_token, "%b-%Y")


class ApiOrder(BaseModel):
    d_no: str
    d_status: str
    mypage_lock_flg: int
    order_date: datetime
    scheduled_release: date
    subtotal: int

    @validator("scheduled_release", pre=True)
    def parse_scheduled_release(cls, value: str):
        return amiami_month_date_validate(value)

    @validator("d_status")
    def parse_d_status(cls, value: str):
        return value.rstrip()


class OrderWithItems(ApiOrder):
    items: list["ApiItem"]


class ApiItem(BaseModel):
    ds_no: str
    scode: str
    sname: str
    thumb_url: str  # "/images/product/thumb300/242/FIGURE-168653.jpg",
    thumb_alt: str  # "FIGURE-168653.jpg",
    thumb_title: (
        str  # "Date A Live V Kurumi Tokisaki Wa-Bunny 1/7 Scale Figure[FURYU]",
    )
    thumb_agelimit: int
    releasedate: date
    price: int
    amount: int
    stock_flg: int
    # max_cartin_count: None,
    # stock: None,
    # mixed_gcode: null,
    # mixed_message: null

    @validator("releasedate", pre=True)
    def parse_releasedate(cls, value: str):
        return amiami_month_date_validate(value)

    @property
    def page_link(self) -> str:
        return f"https://www.amiami.com/eng/detail?scode={self.scode}"


class ApiOrderInfo(BaseModel):
    d_no: str
    d_status: str
    scheduled_release: date
    total: int
    subtotal: int
    items: list[ApiItem]

    @validator("scheduled_release", pre=True)
    def parse_scheduled_release(cls, value: str):
        return amiami_month_date_validate(value)

    @validator("d_status")
    def parse_d_status(cls, value: str):
        return value.rstrip()

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


class AmiAmiApi:
    api_root_url: str = "https://api-secure.amiami.com/api/v1.0"
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

    def login(self, login: str, password: str) -> bool:
        login_data = {
            "lang": "eng",
            "email": login,
            "password": password,
            "c_ransu": None,
        }

        response = self.session.post(
            url=f"{self.api_root_url}/login",
            headers=self._get_headers(),
            data=login_data,
        )
        if response.json()["RSuccess"]:
            self.login_data = response.json()
            logging.info("Login successfull")
            return True

        try:
            error_message = response.json()["RMessage"]
        except:
            error_message = response.status_code
        logging.info(f"Login failed: {error_message}")
        return False

    def get_orders(self) -> list[ApiOrder]:
        params: dict[str, str | int] = {
            "status_ids": "1,2,5,6,7,10,999",
            "search_key": "id",
            "pagemax": 20,
            "lang": "eng",
        }
        response = requests.get(
            f"{self.api_root_url}/orders",
            headers=self._get_headers(),
            params=params,
        )
        orders = TypeAdapter(list[ApiOrder]).validate_python(response.json()["orders"])
        return orders

    def get_order_info(self, order_number: str) -> ApiOrderInfo:
        response = requests.get(
            f"{self.api_root_url}/orders/detail",
            headers=self._get_headers(),
            params={
                "d_no": order_number,
                "lang": "eng",
            },
        )
        order_info = TypeAdapter(ApiOrderInfo).validate_python(response.json()["order"])
        return order_info

    def get_orders_info(self) -> list[ApiOrderInfo]:
        orders = self.get_orders()
        logging.info(f"Got {len(orders)} orders")
        orders_info: list[ApiOrderInfo] = []
        for order in orders:
            order_info = self.get_order_info(order.d_no)
            orders_info.append(order_info)
            logging.info(f"Got order {order.d_no} info")
        return orders_info
