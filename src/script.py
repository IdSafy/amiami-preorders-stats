import logging
from collections import defaultdict
from datetime import date
from functools import reduce

from pydantic import TypeAdapter

import amiami_api

logging.basicConfig(level=logging.INFO)


def get_preorder_items() -> list[amiami_api.ApiOrderInfo]:
    api = amiami_api.AmiAmiApi()

    api.login(login="*", password="*")

    orders = api.get_orders()
    logging.info(f"Got {len(orders)} orders")

    items: list[amiami_api.ApiOrderInfo] = []
    for order in orders:
        order_info = api.get_order_info(order.d_no)
        logging.info(f"Got order {order.d_no} info")
        items += order_info.items


# items = get_preorder_items()
# with open("preorders.json", "w") as file:
#     json.dump(items, file, default=pydantic_encoder)

with open("preorders.json", "r") as file:
    items = TypeAdapter(list[amiami_api.ApiItem]).validate_json(file.read())

items_by_month: dict[date, list[amiami_api.ApiItem]] = defaultdict(list)
for item in items:
    items_by_month[item.releasedate].append(item)

for month, items in sorted(items_by_month.items(), key=lambda i: i[0]):
    cost = reduce(lambda a, b: a + b.price, items, 0)
    print(
        f"{month}: {len(items):4}, cost: {cost:>10.2f} yen or {cost * 0.0066:>10.2f} usd"
    )

# pprint(items_by_month)
