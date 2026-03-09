import asyncio
from decimal import Decimal
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from _sdk import CantexSDK, InstrumentId

TOKEN = "ISI_TOKEN_BOT"
OWNER_ID = 123456789

PRIVATE_KEY = "ISI_PRIVATE_KEY"

sdk = CantexSDK(private_key=PRIVATE_KEY)

running = False


def owner_only(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_user.id != OWNER_ID:
            return
        return await func(update, context)
    return wrapper


async def swap_loop(update: Update):
    global running

    cc = InstrumentId("CC")
    usdc = InstrumentId("USDCx")

    while running:
        try:
            balances = await sdk.get_balances()

            cc_balance = Decimal(balances.get("CC", 0))
            usdc_balance = Decimal(balances.get("USDCx", 0))

            if cc_balance > 1:
                await sdk.swap(
                    sell_amount=cc_balance,
                    sell_instrument="CC",
                    buy_instrument="USDCx"
                )

                await update.message.reply_text(
                    f"Swap CC → USDCx\nAmount: {cc_balance}"
                )

            elif usdc_balance > 1:
                await sdk.swap(
                    sell_amount=usdc_balance,
                    sell_instrument="USDCx",
                    buy_instrument="CC"
                )

                await update.message.reply_text(
                    f"Swap USDCx → CC\nAmount: {usdc_balance}"
                )

        except Exception as e:
            await update.message.reply_text(f"Swap Error: {e}")

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
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stop", stop))

    print("Bot running...")

    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
