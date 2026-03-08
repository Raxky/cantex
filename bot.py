import os
import asyncio
from decimal import Decimal

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from cantex_sdk import CantexSDK, OperatorKeySigner, IntentTradingKeySigner

TELEGRAM_TOKEN = os.environ["8788392180:AAGFWNp_BYB1sl6z2sYDmjGBQLhHVpgDmQc"]

operator = OperatorKeySigner.from_hex(os.environ["CANTEX_OPERATOR_KEY"])
intent = IntentTradingKeySigner.from_hex(os.environ["CANTEX_TRADING_KEY"])


async def get_balance():

    async with CantexSDK(operator, intent) as sdk:

        await sdk.authenticate()
        info = await sdk.get_account_info()

        balances = []

        for token in info.tokens:
            balances.append(
                f"{token.instrument_symbol}: {token.unlocked_amount}"
            )

        return "\n".join(balances)


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text("Checking balance...")

    try:

        b = await get_balance()

        await update.message.reply_text(b)

    except Exception as e:

        await update.message.reply_text(f"Error: {e}")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "Cantex Bot Ready\n\nCommands:\n/balance"
    )


def main():

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))

    app.run_polling()


if __name__ == "__main__":
    main()
