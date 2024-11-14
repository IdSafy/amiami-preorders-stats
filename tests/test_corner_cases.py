import urllib.parse

import pytest
import responses

from amiami_api.api import AMIAMI_API_BASE_URL, AmiAmiApi


@pytest.fixture
def api() -> AmiAmiApi:
    return AmiAmiApi()


@responses.activate
def test_order_moved(api: AmiAmiApi) -> None:
    mock_response_data = {
        "RValue": None,
        "RSuccess": True,
        "RMessage": "OK",
        "search_result": {
            "total_results": 1,
        },
        "orders": [
            {
                "d_no": "12345678",
                "d_status": "pre-order",
                "scheduled_release": "Jun-2022",
                "subtotal": 100,
                "mypage_lock_flg": 0,
            }
        ],
    }
    responses.add(
        responses.Response(
            method="GET",
            url=urllib.parse.urljoin(AMIAMI_API_BASE_URL, "orders"),
            json=mock_response_data,
        )
    )
    orders = api.get_orders()  # noqa
