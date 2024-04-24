import json
import logging
import re
import sys
from collections import defaultdict
from datetime import date
from functools import reduce, wraps
from os import environ
from typing import TextIO

import click
from dotenv import load_dotenv
from print_color import print
from pydantic import TypeAdapter
from pydantic.json import pydantic_encoder

import amiami_api

logging.basicConfig(level=logging.INFO)

load_dotenv()


def link(uri: str, label: str | None = None) -> str:
    if label is None:
        label = uri
    parameters = ""

    # OSC 8 ; params ; URI ST <name> OSC 8 ;; ST
    escape_mask = "\033]8;{};{}\033\\{}\033]8;;\033\\"

    return escape_mask.format(parameters, uri, label)


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

    @wraps(print)
    def _print(*args, **kwargs):
        kwargs.setdefault("file", stream)
        kwargs.setdefault("end", "")
        print(*args, **kwargs)

    _print("By month stats:\n")
    for month, month_orders in sorted(orders_by_month.items(), key=lambda i: i[0]):
        cost = reduce(lambda a, b: a + b.total, month_orders, 0)
        n_items = reduce(lambda a, b: a + len(b.items), month_orders, 0)
        month_str = month.strftime("%Y-%m")
        _print(f"{month_str};{n_items:2} items;{cost:>9.2f}¥ /{cost * 0.0066:>7.2f}$\n")
    _print("------\n------\n\n")

    all_items: list[amiami_api.ApiItem] = []
    _print("Detailed stats:\n")
    order_color_cycle = [
        "blue",
        "purple",
        "yellow",
        "red",
        "magenta",
        "cyan",
    ]
    previous_item_order = None
    previous_month = None
    order_color_index = -1
    month_color_index = 2
    for month, month_orders in sorted(orders_by_month.items(), key=lambda i: i[0]):
        for order in month_orders:
            for item in order.items:
                in_stock_text, in_stock_text_color = (
                    ("in stock", "green")
                    if item.stock_flg == item.amount
                    else ("not in stock", "white")
                )

                if previous_item_order != order.d_no:
                    order_color_index = (order_color_index + 1) % len(order_color_cycle)
                    previous_item_order = order.d_no
                order_color = order_color_cycle[order_color_index]

                month_str = month.strftime("%Y-%m")
                if previous_month != month_str:
                    month_color_index = (month_color_index + 1) % len(order_color_cycle)
                    previous_month = month_str
                month_color = order_color_cycle[month_color_index]

                _print(f"{month_str};", color=month_color)
                _print(" order ")
                _print(f"{link(order.page_link, order.d_no)}; ", color=order_color)
                _print(f"{in_stock_text:>12};", color=in_stock_text_color)
                _print(
                    f"{item.price:>9.2f}¥ /{item.price * 0.0066:>7.2f}$; {link(item.page_link, item.sname)}\n"
                )
                all_items.append(item)
    _print("------\n")
    _print("------\n\n")

    print("Categories:", file=stream)
    total_cost = reduce(lambda a, b: a + b.price, all_items, 0)
    total_n_items = len(all_items)
    categories = classify_items(all_items)
    for category, items in sorted(categories.items(), key=lambda t: t[0]):
        _print(f"{category}: {len(items)}\n")
    _print("------\n------\n\n")

    _print(f"Total items: {total_n_items}\n")
    _print(f"Summary cost: {total_cost:>9.2f}¥ / {total_cost * 0.0066:>7.2f}$\n")


@click.command()
@click.option("-f", "filename", default="preorders.json")
def update(filename: str):
    login = environ.get("AMIAMI_LOGIN")
    if login is None:
        logging.error("AMIAMI_LOGIN env must be set")
        return
    password = environ.get("AMIAMI_PASSWORD")
    if password is None:
        logging.error("AMIAMI_PASSWORD env must be set")
        return

    orders = get_orders(login, password)
    with open(filename, "w") as file:
        json.dump(orders, file, default=pydantic_encoder)


@click.command()
@click.option("-f", "filename", default="preorders.json")
def stats(filename: str):
    try:
        with open(filename, "r") as file:
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
