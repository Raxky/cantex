import os
import asyncio
from decimal import Decimal

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

from _sdk import CantexSDK, OperatorKeySigner, IntentTradingKeySigner


# =========================
# CONFIG
# =========================

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
OWNER_ID = int(os.environ["OWNER_ID"])

BASE_URL = os.getenv(
    "CANTEX_BASE_URL",
    "https://api.cantex.io"
)

operator = OperatorKeySigner.from_hex(os.environ["CANTEX_OPERATOR_KEY"])
intent = IntentTradingKeySigner.from_hex(os.environ["CANTEX_TRADING_KEY"])

autoswap_task = None


# =========================
# OWNER CHECK
# =========================

def is_owner(update: Update):

    return (
        update.effective_user.id == OWNER_ID
        and update.effective_chat.type == "private"
    )


# =========================
# START
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        return

    text = """
🤖 Cantex Volume Bot

Commands:

/balance
/autoswap
/stop
"""

    await update.message.reply_text(text)


# =========================
# BALANCE
# =========================

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        return

    await update.message.reply_text("Checking balance...")

    try:

        async with CantexSDK(operator, intent, base_url=BASE_URL) as sdk:

            await sdk.authenticate()
            info = await sdk.get_account_info()

            text = ""

            for token in info.tokens:

                text += f"{token.instrument_symbol}: {token.unlocked_amount}\n"

            await update.message.reply_text(text)

    except Exception as e:

        await update.message.reply_text(f"Error: {e}")


# =========================
# AUTOSWAP COMMAND
# =========================

async def autoswap(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        return

    context.user_data["waiting_amount"] = True

    await update.message.reply_text(
        "Masukkan jumlah CC yang ingin di swap\nContoh:\n0.1"
    )


# =========================
# MESSAGE HANDLER
# =========================

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        return

    global autoswap_task

    # INPUT AMOUNT
    if context.user_data.get("waiting_amount"):

        try:

            amount = Decimal(update.message.text)

            context.user_data["swap_amount"] = amount
            context.user_data["waiting_amount"] = False
            context.user_data["waiting_interval"] = True

            await update.message.reply_text(
                "Masukkan interval swap (detik)\nContoh:\n60"
            )

        except:

            await update.message.reply_text("Masukkan angka yang benar.")

        return


    # INPUT INTERVAL
    if context.user_data.get("waiting_interval"):

        try:

            interval = int(update.message.text)
            amount = context.user_data["swap_amount"]

            context.user_data["waiting_interval"] = False

            if autoswap_task:

                await update.message.reply_text("Autoswap sudah berjalan.")
                return

            autoswap_task = asyncio.create_task(
                swap_loop(amount, interval, update.effective_chat.id, context.application)
            )

            await update.message.reply_text(
                f"""
Autoswap dimulai

Amount CC : {amount}
Interval  : {interval} detik
"""
            )

        except:

            await update.message.reply_text("Masukkan angka interval yang benar.")


# =========================
# SWAP LOOP
# =========================

async def swap_loop(amount, interval, chat_id, app):

    direction = True

    while True:

        try:

            async with CantexSDK(operator, intent, base_url=BASE_URL) as sdk:

                await sdk.authenticate()

                # =========================
                # CC → USDCx
                # =========================

                if direction:

                    sell = "CC"
                    buy = "USDCx"
                    sell_amount = Decimal(amount)

                # =========================
                # USDCx → CC
                # =========================

                else:

                    info = await sdk.get_account_info()

                    usdc_balance = Decimal("0")

                    for token in info.tokens:

                        if token.instrument_symbol == "USDCx":

                            usdc_balance = Decimal(token.unlocked_amount)

                    if usdc_balance == 0:

                        await app.bot.send_message(
                            chat_id,
                            "Saldo USDCx kosong"
                        )

                        await asyncio.sleep(interval)
                        continue

                    sell = "USDCx"
                    buy = "CC"
                    sell_amount = usdc_balance


                # =========================
                # EXECUTE SWAP
                # =========================

                await sdk.swap(

                    sell_amount=sell_amount,
                    sell_instrument=sell,
                    buy_instrument=buy

                )

                await app.bot.send_message(

                    chat_id,

                    f"""
Swap berhasil

{sell} → {buy}
Amount : {sell_amount}
"""
                )

                direction = not direction


        except Exception as e:

            await app.bot.send_message(chat_id, f"Swap Error: {e}")


        await asyncio.sleep(interval)


# =========================
# STOP
# =========================

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    if not is_owner(update):
        return

    global autoswap_task

    if autoswap_task:

        autoswap_task.cancel()
        autoswap_task = None

        await update.message.reply_text("Autoswap dihentikan.")

    else:

        await update.message.reply_text("Autoswap tidak berjalan.")


# =========================
# MAIN
# =========================

def main():

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("autoswap", autoswap))
    app.add_handler(CommandHandler("stop", stop))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler)
    )

    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
