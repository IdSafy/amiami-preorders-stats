import json
import logging
import re
import sys
from collections import defaultdict
from datetime import date
from functools import reduce
from os import environ
from typing import TextIO

import click
from dotenv import load_dotenv
from pydantic import TypeAdapter
from pydantic.json import pydantic_encoder

import amiami_api

logging.basicConfig(level=logging.INFO)

load_dotenv()


def get_orders(login: str, password: str) -> list[amiami_api.ApiOrderInfo]:
    api = amiami_api.AmiAmiApi()

    login_status = api.login(login=login, password=password)
    if not login_status:
        logging.warning("Canceling updating preorders")

    orders = api.get_orders_info()
    return orders


def classify_items(
    items: list[amiami_api.ApiItem],
) -> dict[str, list[amiami_api.ApiItem]]:
    categories_buckets: dict[str, list[amiami_api.ApiItem]] = defaultdict(list)
    for item in items:
        if item.sname.lower().find("nendoroid") != -1:
            categories_buckets["nendoroid"].append(item)
            continue
        scale_match = re.search(r"\d\/\d", item.sname)
        if scale_match is not None:
            categories_buckets[f"{scale_match.group()} scale"].append(item)
            continue
        categories_buckets["other"].append(item)
        continue
    return categories_buckets


def print_stats(stream: TextIO, orders: list[amiami_api.ApiOrderInfo]) -> None:
    orders_by_month: dict[date, list[amiami_api.ApiOrderInfo]] = defaultdict(list)
    for order in orders:
        orders_by_month[order.scheduled_release].append(order)

    print("By month stats:", file=stream)
    for month, month_orders in sorted(orders_by_month.items(), key=lambda i: i[0]):
        cost = reduce(lambda a, b: a + b.total, month_orders, 0)
        n_items = reduce(lambda a, b: a + len(b.items), month_orders, 0)
        print(
            f"{month};{n_items:2} items;{cost:>9.2f} yen;{cost * 0.0066:>7.2f} usd",
            file=stream,
        )

    print("------\n\n", file=stream)

    all_items: list[amiami_api.ApiItem] = []
    print("Detailed stats:", file=stream)
    for month, month_orders in sorted(orders_by_month.items(), key=lambda i: i[0]):
        for order in month_orders:
            for item in order.items:
                in_stock_text = (
                    "in stock" if item.stock_flg == item.amount else "not in stock"
                )
                print(
                    f"{month}; order {order.d_no}: {in_stock_text:>12};{item.price:>9.2f} yen;{item.price * 0.0066:>7.2f} usd; {item.sname}",
                    file=stream,
                )
                all_items.append(item)
        print("------", file=stream)

    total_cost = reduce(lambda a, b: a + b.price, all_items, 0)
    total_n_items = len(all_items)

    print("\n", file=stream)
    print("Categories:", file=stream)
    categories = classify_items(all_items)
    for category, items in sorted(categories.items(), key=lambda t: t[0]):
        print(f"{category}: {len(items)}", file=stream)
    print("------", file=stream)

    print("\n", file=stream)
    print(f"Total items: {total_n_items}", file=stream)
    print(
        f"Summary cost: {total_cost:>9.2f} yen or {total_cost * 0.0066:>7.2f} usd ",
        file=stream,
    )


@click.command()
@click.option("-f", "file", default="preorders.json")
def update(file: str):
    login = environ.get("AMIAMI_LOGIN")
    if login is None:
        logging.error("AMIAMI_LOGIN env must be set")
        return
    password = environ.get("AMIAMI_PASSWORD")
    if login is None:
        logging.error("AMIAMI_PASSWORD env must be set")
        return

    orders = get_orders(login, password)
    with open(file, "w") as file:
        json.dump(orders, file, default=pydantic_encoder)


@click.command()
@click.option("-f", "file", default="preorders.json")
def stats(file: str):
    try:
        with open(file, "r") as file:
            orders = TypeAdapter(list[amiami_api.ApiOrderInfo]).validate_json(
                file.read()
            )
    except:
        logging.error("Failed to read file")

    print_stats(sys.stdout, orders)


@click.group()
def cli():
    pass


cli.add_command(update)
cli.add_command(stats)

if __name__ == "__main__":
    cli()
