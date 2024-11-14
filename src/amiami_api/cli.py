import asyncio
import json
import logging
import re
import sys
from datetime import date, timedelta
from functools import reduce, wraps
from itertools import groupby
from os import environ
from typing import TextIO

import click
from dotenv import load_dotenv
from print_color import print
from pydantic import JsonValue, TypeAdapter
from pydantic_core import to_jsonable_python

from amiami_api.api import AmiAmiApi, ApiItem, ApiOrderInfo, OrderType

logging.basicConfig(level=logging.INFO)

load_dotenv()


def link(uri: str, label: str | None = None) -> str:
    if label is None:
        label = uri
    parameters = ""

    # OSC 8 ; params ; URI ST <name> OSC 8 ;; ST
    escape_mask = "\033]8;{};{}\033\\{}\033]8;;\033\\"

    return escape_mask.format(parameters, uri, label)


async def get_order_info(api: AmiAmiApi, d_no: str) -> ApiOrderInfo:
    logging.info(f"Updating order {d_no}")
    order = api.get_order_info(d_no)
    return order


async def get_orders_infos(api: AmiAmiApi, orders_numbers: list[str]) -> list[ApiOrderInfo]:
    tasks = [get_order_info(api, d_no) for d_no in orders_numbers]
    orders_infos = await asyncio.gather(*tasks)
    return orders_infos


def get_new_orders(login: str, password: str, known_orders_infos: list[ApiOrderInfo]) -> list[ApiOrderInfo]:
    api = AmiAmiApi()

    login_status = api.login(login=login, password=password)
    if not login_status:
        logging.warning("Canceling updating orders")

    closed_orders_numbers = [order.d_no for order in known_orders_infos if not order.is_open]
    all_orders = api.get_orders(order_type=OrderType.all)
    up_to_update_orders_numbers = [order.d_no for order in all_orders if order.d_no not in closed_orders_numbers]

    order_info_by_number = {order.d_no: order for order in known_orders_infos if order.d_no not in closed_orders_numbers}

    logging.info(f"Found {len(up_to_update_orders_numbers)} orders to update")
    updated_orders_infos = asyncio.run(get_orders_infos(api, up_to_update_orders_numbers))
    for updated_order_info in updated_orders_infos:
        order_info_by_number[updated_order_info.d_no] = updated_order_info

    return list(order_info_by_number.values())


ItemWithRelatedData = tuple[ApiItem, ApiOrderInfo, dict[str, JsonValue]]
ItemsTable = list[ItemWithRelatedData]


def flatten_items(orders: list[ApiOrderInfo]) -> ItemsTable:
    flat_items: ItemsTable = []
    for order in orders:
        for item in order.items:
            flat_items.append((item, order, {}))
    return flat_items


def classify_item(item: ApiItem) -> str:
    if item.sname.lower().find("nendoroid") != -1:
        return "nendoroid"
    scale_match = re.search(r"\d\/\d", item.sname)
    if scale_match is not None:
        return f"{scale_match.group()} scale"
    return "other"


def classify_items(items: ItemsTable) -> None:
    for item, order, metadata in items:
        metadata["category"] = classify_item(item)


def prepare_items_table(orders: list[ApiOrderInfo]) -> ItemsTable:
    item_table = flatten_items(orders)
    classify_items(item_table)
    return item_table


def print_stats(stream: TextIO, orders: list[ApiOrderInfo]) -> None:
    @wraps(print)
    def _print(*args, **kwargs):
        kwargs.setdefault("file", stream)
        kwargs.setdefault("end", "")
        print(*args, **kwargs)

    orders_by_month = groupby(
        sorted(orders, key=lambda order: order.scheduled_release),
        key=lambda order: order.scheduled_release,
    )
    _print("By month stats:\n")
    for month, month_orders_iterator in orders_by_month:
        month_orders = list(month_orders_iterator)
        cost = reduce(lambda a, b: a + b.subtotal, month_orders, 0)
        n_items = reduce(lambda a, b: a + len(b.items), month_orders, 0)
        month_str = month.strftime("%Y-%m")
        _print(f"{month_str};{n_items:2} items;{cost:>9.2f}¥ /{cost * 0.0066:>7.2f}$\n")
    _print("------\n------\n\n")

    items_table = prepare_items_table(orders)
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
    for item, order, metadata in sorted(items_table, key=lambda pair: (pair[1].scheduled_release, pair[0].price)):
        month = order.scheduled_release

        in_stock_text, in_stock_text_color = ("in stock", "green") if item.stock_flg == item.amount else ("N/A", "white")

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
        _print(f"{in_stock_text:>8};", color=in_stock_text_color)
        _print(f"{item.price:>9.2f}¥ /{item.price * 0.0066:>7.2f}$; {link(item.page_link, item.sname)}\n")
    _print("------\n------\n\n")

    print("Categories:", file=stream)
    items_by_category = groupby(
        sorted(items_table, key=lambda t: t[2].get("category")),  # type: ignore
        key=lambda t: t[2].get("category"),
    )
    for category, items_iterator in items_by_category:
        items = list(items_iterator)
        _print(f"{category}: {len(items)}\n")
    _print("------\n------\n\n")

    total_cost = reduce(lambda a, t: a + t[0].price, items_table, 0)
    total_n_items = len(items_table)
    _print(f"Total items: {total_n_items}\n")
    _print(f"Summary cost: {total_cost:>9.2f}¥ / {total_cost * 0.0066:>7.2f}$\n")


@click.command()
@click.option("-f", "filename", default="preorders.json", help="state file")
@click.option("-a", "--all", "all", is_flag=True, default=False)
def update(all: bool, filename: str):
    login = environ.get("AMIAMI_LOGIN")
    if login is None:
        logging.error("AMIAMI_LOGIN env must be set")
        return
    password = environ.get("AMIAMI_PASSWORD")
    if password is None:
        logging.error("AMIAMI_PASSWORD env must be set")
        return

    if not all:
        try:
            with open(filename, "r") as file:
                known_orders = TypeAdapter(list[ApiOrderInfo]).validate_json(file.read())
        except Exception as exception:
            logging.exception(exception)
            logging.warning(f"File {filename} doesn't exist or corrupted. Soft update will behave as full update")
            known_orders = []
        orders = get_new_orders(login, password, known_orders)
    else:
        orders = get_new_orders(login, password, [])
    with open(filename, "w") as file:
        json.dump(to_jsonable_python(orders), file)


@click.command()
@click.option("-f", "filename", default="preorders.json", help="state file")
@click.option("-a", "--all", "all", default=False, is_flag=True)
def stats(filename: str, all: bool):
    try:
        with open(filename, "r") as file:
            orders = TypeAdapter(list[ApiOrderInfo]).validate_json(file.read())
    except Exception as exception:
        logging.error("Failed to read file", exc_info=exception)

    if all:
        filter_function = None
    else:
        last_month = date.today() - timedelta(weeks=5)

        def filter_function(order: ApiOrderInfo) -> bool:
            return order.scheduled_release > last_month and order.d_status not in ["Shipped"]

    filtered_orders = list(filter(filter_function, orders))
    print_stats(sys.stdout, filtered_orders)


@click.group()
def cli():
    pass


cli.add_command(update)
cli.add_command(stats)

if __name__ == "__main__":
    cli()
