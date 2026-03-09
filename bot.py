import os
import asyncio
from decimal import Decimal
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from _sdk import CantexSDK, OperatorKeySigner, IntentTradingKeySigner


TOKEN = os.getenv("TELEGRAM_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))

OPERATOR_KEY = os.getenv("OPERATOR_KEY")
TRADING_KEY = os.getenv("TRADING_KEY")
API_KEY = os.getenv("API_KEY")

running = False
sdk = None


def write_secret_file(path, content):
    if not content:
        raise Exception(f"Missing environment variable for {path}")
    with open(path, "w") as f:
        f.write(content)


def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, context)
    return wrapper


async def swap_loop(update: Update):

    global running, sdk

    while running:
        try:

            account = await sdk.get_account_info()

            cc_balance = Decimal("0")
            usdc_balance = Decimal("0")

            for b in account.balances:

                if b.instrument_symbol == "CC":
                    cc_balance = b.unlocked_amount

                if b.instrument_symbol == "USDCx":
                    usdc_balance = b.unlocked_amount

            if cc_balance > Decimal("1"):

                await sdk.swap(
                    sell_amount=cc_balance,
                    sell_instrument="CC",
                    buy_instrument="USDCx"
                )

                await update.message.reply_text(
                    f"Swap CC → USDCx : {cc_balance}"
                )

            elif usdc_balance > Decimal("1"):

                await sdk.swap(
                    sell_amount=usdc_balance,
                    sell_instrument="USDCx",
                    buy_instrument="CC"
                )

                await update.message.reply_text(
                    f"Swap USDCx → CC : {usdc_balance}"
                )

        except Exception as e:

            print("Swap error:", e)

            try:
                await update.message.reply_text(f"Swap Error: {e}")
            except:
                pass

        await asyncio.sleep(10)


@owner_only
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global running

    if running:
        await update.message.reply_text("Bot already running")
        return

    running = True

    await update.message.reply_text("Bot started")

    asyncio.create_task(swap_loop(update))


@owner_only
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):

    global running

    running = False

    await update.message.reply_text("Bot stopped")


async def main():

    global sdk

    if not TOKEN:
        raise Exception("TELEGRAM_TOKEN not set")

    if not OWNER_ID:
        raise Exception("OWNER_ID not set")

    # create temporary secret files
    write_secret_file("operator.pem", OPERATOR_KEY)
    write_secret_file("intent.key", TRADING_KEY)
    write_secret_file("api_key.txt", API_KEY)

    operator = OperatorKeySigner.from_file("operator.pem")
    intent = IntentTradingKeySigner.from_file("intent.key")

    async with CantexSDK(operator, intent) as sdk_instance:

        sdk = sdk_instance

        await sdk.authenticate()

        app = ApplicationBuilder().token(TOKEN).build()

        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("stop", stop))

        print("Bot running...")

        await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
