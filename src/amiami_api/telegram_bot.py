from typing import Any, Iterable

import telegramify_markdown
from dependency_injector.wiring import Provide, inject
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, ExtBot, JobQueue

from amiami_api.api import OrderInfo, OrderType
from amiami_api.fx_rates import FxRatesService
from amiami_api.service import AmiamiService

@inject
def format_order(order: OrderInfo, jpy_to_usd_rate: float) -> str:
    order_status_emoji = "" if order.is_open else "✅"  # type: ignore[truthy-function]
    order_price_usd = order.price * jpy_to_usd_rate
    title = (
        f"Order [{order.id}]({order.page_link}): "
        f"{order_status_emoji}, {order.scheduled_release.strftime('%b %Y')}, {order.price}¥/{order_price_usd:.2f}$, {len(order.items)} items:"
    )
    items = ""
    for item in order.items:
        item_status_emoji = "✅" if item.in_stock_flag > 0 else "❌"
        item_price_usd = item.price * jpy_to_usd_rate
        items += f"\n- [{item.id}]({item.page_link}): {item_status_emoji}, {item.name}, {item.price}¥/{item_price_usd:.2f}$"

    return f"{title}{items}"


async def format_orders(orders: Iterable[OrderInfo], fx_rates_service: FxRatesService = Provide["fx_rates_service"]) -> str:
    sorted_orders = sorted(orders, key=lambda o: o.scheduled_release)
    jpy_to_usd_rate = await fx_rates_service.get_jpy_to_usd_rate()
    return "\n---\n\n".join([format_order(o, jpy_to_usd_rate) for o in sorted_orders])


@inject
async def update_open(update: Update, context: ContextTypes.DEFAULT_TYPE, service: AmiamiService = Provide["service"]) -> None:
    assert update.message is not None
    await update.message.reply_text("Updating open orders...")
    await service.update_orders(order_type=OrderType.open)
    await update.message.reply_text("Open orders updated.")


@inject
async def full_update(update: Update, context: ContextTypes.DEFAULT_TYPE, service: AmiamiService = Provide["service"]) -> None:
    assert update.message is not None
    await update.message.reply_text("Full update (all orders)...")
    orders = await service.update_orders(order_type=OrderType.all)
    await update.message.reply_text(f"All orders updated: {len(orders)} orders found.")


@inject
async def show_current_orders(update: Update, context: ContextTypes.DEFAULT_TYPE, service: AmiamiService = Provide["service"]):
    assert update.message is not None
    orders = await service.get_current_orders()
    if not orders:
        await update.message.reply_text("No current orders.")
        return
    message = "# Current orders\n\n" + await format_orders(orders)
    await update.message.reply_markdown_v2(telegramify_markdown.markdownify(message))


@inject
async def show_open(update: Update, context: ContextTypes.DEFAULT_TYPE, service: AmiamiService = Provide["service"]):
    assert update.message is not None
    orders = await service.get_orders(order_type=OrderType.open)
    if not orders:
        await update.message.reply_text("No open orders.")
        return
    message = "# Open orders\n\n" + await format_orders(orders)
    await update.message.reply_markdown_v2(telegramify_markdown.markdownify(message))


@inject
async def update_and_show_current(update: Update, context: ContextTypes.DEFAULT_TYPE, service: AmiamiService = Provide["service"]):
    assert update.message is not None
    await update.message.reply_text("Updating and showing current month orders...")
    await service.update_orders(order_type=OrderType.current_month)
    orders = await service.get_current_orders()
    if not orders:
        await update.message.reply_text("No current orders.")
        return
    message = "# Current orders\n\n" + await format_orders(orders)
    await update.message.reply_markdown_v2(telegramify_markdown.markdownify(message))


async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    assert update.message is not None
    text = (
        "Available commands:\n"
        "- /start - Start the bot\n"
        "- /update - Update open orders\n"
        "- /update_full - Full update (all orders)\n"
        "- /show_current - Show current month orders\n"
        "- /show_open - Show open orders\n"
        "- /update_and_show_current - Update and show current month orders\n"
    )
    await update.message.reply_markdown_v2(telegramify_markdown.markdownify(text))


@inject
async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    white_list: list[str] = Provide["config.telegram_bot_white_list"],
):
    assert update.message is not None
    user = update.effective_user
    assert user is not None
    allowed = False
    if str(user.id) in white_list or user.username in white_list:
        allowed = True
    if not allowed:
        await update.message.reply_text(
            text="You are not allowed to use this bot. Please contact the administrator.",
        )
        return
    await update.message.reply_text(
        text="Hello! Now I'm running!",
    )


def create_bot(
    token: str,
) -> Application[ExtBot[None], ContextTypes.DEFAULT_TYPE, dict[Any, Any], dict[Any, Any], dict[Any, Any], JobQueue[ContextTypes.DEFAULT_TYPE]]:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("update", update_open))
    application.add_handler(CommandHandler("update_full", full_update))
    application.add_handler(CommandHandler("show_current", show_current_orders))
    application.add_handler(CommandHandler("show_open", show_open))
    application.add_handler(CommandHandler("update_and_show_current", update_and_show_current))
    application.add_handler(CommandHandler("help", help))
    return application
