import json
import logging
from collections import defaultdict
from datetime import date
from functools import reduce

import click
from pydantic import TypeAdapter
from pydantic.json import pydantic_encoder

import amiami_api

logging.basicConfig(level=logging.INFO)


def get_preorder_items() -> list[amiami_api.ApiOrderInfo]:
    api = amiami_api.AmiAmiApi()

    login_status = api.login(login="*", password="*")
    if not login_status:
        logging.warning("Canceling updating preorders")

    orders = api.get_orders()
    logging.info(f"Got {len(orders)} orders")

    items: list[amiami_api.ApiOrderInfo] = []
    for order in orders:
        order_info = api.get_order_info(order.d_no)
        logging.info(f"Got order {order.d_no} info")
        items += order_info.items
    return items


@click.command()
@click.option("-f", "file", default="preorders.json")
def update(file: str):
    items = get_preorder_items()
    with open(file, "w") as file:
        json.dump(items, file, default=pydantic_encoder)


@click.command()
@click.option("-f", "file", default="preorders.json")
def stats(file: str):
    try:
        with open(file, "r") as file:
            items = TypeAdapter(list[amiami_api.ApiItem]).validate_json(file.read())
    except:
        logging.error("Failed to read file")

    items_by_month: dict[date, list[amiami_api.ApiItem]] = defaultdict(list)
    for item in items:
        items_by_month[item.releasedate].append(item)

    print("By month stats:")
    for month, month_items in sorted(items_by_month.items(), key=lambda i: i[0]):
        cost = reduce(lambda a, b: a + b.price, month_items, 0)
        print(
            f"{month}: {len(month_items):4}, cost: {cost:>9.2f} yen or {cost * 0.0066:>7.2f} usd"
        )

    print("------\n\n")

    print("Detailed stats:")
    for month, month_items in sorted(items_by_month.items(), key=lambda i: i[0]):
        # cost = reduce(lambda a, b: a + b.price, month_items, 0)
        for item in month_items:
            print(
                f"{month}:{item.ds_no}:{item.price:>9.2f} yen:{item.price * 0.0066:>7.2f} usd: {item.sname}"
            )
        print("------")

    print("\n")
    cost = reduce(lambda a, b: a + b.price, items, 0)
    print(f"Summary cost: {cost:>9.2f} yen or {cost * 0.0066:>7.2f} usd ")


@click.group()
def cli():
    pass


cli.add_command(update)
cli.add_command(stats)

if __name__ == "__main__":
    cli()
