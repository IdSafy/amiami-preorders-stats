import re
from pathlib import Path
from typing import AsyncGenerator

import pytest
from aioresponses import aioresponses
from fastapi.testclient import TestClient
from yarl import URL

from amiami_api.api import (
    ApiItem,
    ApiOrder,
    ApiOrderInfo,
    ApiOrderInfoResponse,
    ApiOrdersResponse,
    SearchResult,
)
from amiami_api.di import DIContainer
from amiami_api.web import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def di_container(tmp_path: Path) -> DIContainer:
    di_container = DIContainer()
    di_container.config.update({"username": "test", "password": "test", "store_file_path": tmp_path / "orders.json"})
    return di_container


@pytest.fixture
def test_amiami_api_response_data() -> dict:
    pre_order_1_order_info = ApiOrderInfo(
        d_no="test",
        d_status="pre-order",
        scheduled_release="May-2025",
        subtotal=10000,
        items=[
            ApiItem(
                ds_no="test",
                scode="test",
                sname="test",
                thumb_url="test",
                thumb_alt="test",
                thumb_title="test",
                thumb_agelimit=0,
                releasedate="May-2025",
                price=10000,
                amount=1,
                stock_flg=1,
            )
        ],
    )
    pre_order_1_order = ApiOrder(
        d_no=pre_order_1_order_info.d_no,
        d_status=pre_order_1_order_info.d_status,
        scheduled_release=pre_order_1_order_info.scheduled_release,
        subtotal=pre_order_1_order_info.subtotal,
        mypage_lock_flg=0,
    )
    return {
        "login": {"RSuccess": True, "login": {"token": "test"}},
        "orders": {
            "simple": ApiOrdersResponse(
                RSuccess=True,
                RValue=None,
                RMessage="OK",
                search_result=SearchResult(total_results=1),
                orders=[pre_order_1_order],
            )
        },
        "orders_info": {
            "pre_order_1": ApiOrderInfoResponse(
                RSuccess=True,
                RValue=None,
                RMessage="OK",
                search_result=SearchResult(total_results=1),
                order=pre_order_1_order_info,
            )
        },
    }


@pytest.fixture
async def mock_response() -> AsyncGenerator[aioresponses, None]:
    with aioresponses() as mocker:
        yield mocker


async def test_get_orders(client: TestClient, test_amiami_api_response_data: dict, di_container: DIContainer, mock_response: aioresponses) -> None:
    api = di_container.api()
    mock_response.post(url=f"{api.api_root_url}login", payload=test_amiami_api_response_data["login"])
    mock_response.get(
        url=re.compile(f"{api.api_root_url}orders.*"),
        payload=test_amiami_api_response_data["orders"]["simple"].model_dump(mode="json"),
    )

    orders = client.get("/api/orders/", params={"order_type": "open"})

    assert mock_response.requests.get(("POST", URL(f"{api.api_root_url}login"))) is not None

    assert orders.status_code == 200
    assert orders.json() == test_amiami_api_response_data["orders"]["simple"].model_dump(mode="json")["orders"]


async def test_get_order(client: TestClient, test_amiami_api_response_data: dict, di_container: DIContainer, mock_response: aioresponses) -> None:
    api = di_container.api()
    mock_response.post(url=f"{api.api_root_url}login", payload=test_amiami_api_response_data["login"])
    mock_response.get(
        url=re.compile(f"{api.api_root_url}orders/detail.*"),
        payload=test_amiami_api_response_data["orders_info"]["pre_order_1"].model_dump(mode="json"),
    )

    order = client.get("/api/orders/test/", params={"save_mode": "save"})

    assert mock_response.requests.get(("POST", URL(f"{api.api_root_url}login"))) is not None

    assert order.status_code == 200, order.text
    assert order.json() == test_amiami_api_response_data["orders_info"]["pre_order_1"].model_dump(mode="json")["order"]

    assert len(di_container.store().get_orders()) == 1
    saved_order = di_container.store().get_order("test")
    assert saved_order is not None
    assert saved_order.d_no == "test"


async def test_get_items(client: TestClient, test_amiami_api_response_data: dict, di_container: DIContainer, mock_response: aioresponses) -> None:
    api = di_container.api()
    mock_response.post(url=f"{api.api_root_url}login", payload=test_amiami_api_response_data["login"])
    mock_response.get(
        url=re.compile(f"{api.api_root_url}orders.*"),
        payload=test_amiami_api_response_data["orders"]["simple"].model_dump(mode="json"),
    )
    mock_response.get(
        url=re.compile(f"{api.api_root_url}orders/detail.*"),
        payload=test_amiami_api_response_data["orders_info"]["pre_order_1"].model_dump(mode="json"),
    )

    items = client.get("/api/items/")

    assert mock_response.requests.get(("POST", URL(f"{api.api_root_url}login"))) is not None

    assert items.status_code == 200
    assert items.json() == test_amiami_api_response_data["orders_info"]["pre_order_1"].model_dump(mode="json")["order"]["items"]

    assert len(di_container.store().get_orders()) == 1
    saved_order = di_container.store().get_order("test")
    assert saved_order is not None
    assert saved_order.d_no == "test"
