import json
import logging
from collections import defaultdict
from datetime import date
from functools import reduce
from os import environ

import click
<<<<<<< HEAD
=======
from dotenv import load_dotenv
>>>>>>> 8b77f19 (feat: add external creds load)
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

    orders_by_month: dict[date, list[amiami_api.ApiOrderInfo]] = defaultdict(list)
    for order in orders:
        orders_by_month[order.scheduled_release].append(order)

    print("By month stats:")
    for month, month_orders in sorted(orders_by_month.items(), key=lambda i: i[0]):
        cost = reduce(lambda a, b: a + b.total, month_orders, 0)
        n_items = reduce(lambda a, b: a + len(b.items), month_orders, 0)
        print(
            f"{month}: {n_items:4}, cost: {cost:>9.2f} yen or {cost * 0.0066:>7.2f} usd"
        )

    print("------\n\n")

    total_cost = 0
    print("Detailed stats:")
    for month, month_orders in sorted(orders_by_month.items(), key=lambda i: i[0]):
        for order in month_orders:
            for item in order.items:
                print(
                    f"{month}:{item.ds_no}:{order.d_no}:{item.price:>9.2f} yen:{item.price * 0.0066:>7.2f} usd: {item.sname}"
                )
                total_cost += item.price
        print("------")

    print("\n")
    print(f"Summary cost: {total_cost:>9.2f} yen or {total_cost * 0.0066:>7.2f} usd ")


@click.group()
def cli():
    pass


cli.add_command(update)
cli.add_command(stats)

if __name__ == "__main__":
    cli()
