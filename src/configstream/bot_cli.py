import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import httpx

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants - Should ideally be loaded from env or config
METADATA_URL = "https://farnam.github.io/ConfigStream/files/metadata.json"
BASE_URL = "https://farnam.github.io/ConfigStream/files"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "Hello! I am the ConfigStream Bot. 🚀\n"
            "Use /stats to see pipeline status.\n"
            "Use /get <COUNTRY_CODE> to get a proxy (e.g., /get US).\n"
            "Use /sub for subscription links."
        )


async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(METADATA_URL)
            if resp.status_code == 200:
                data = resp.json()
                msg = (
                    f"📊 *Pipeline Stats*\n"
                    f"Active Proxies: `{data.get('working', '?')}`\n"
                    f"Total Tested: `{data.get('total', '?')}`\n"
                    f"Last Updated: `{data.get('generated_at', '?')}`"
                )
            else:
                msg = "⚠️ Could not fetch stats."
        except Exception as e:
            msg = f"⚠️ Error fetching stats: {str(e)}"

    if update.message:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


async def get_proxy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return

    if not context.args:
        await update.message.reply_text(
            "⚠️ Please specify a country code. Usage: `/get US`",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    country = context.args[0].upper()
    url = f"{BASE_URL}/by_country/{country.lower()}.json"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(url)
            if resp.status_code == 200:
                proxies = resp.json()
                if proxies:
                    # Select a random proxy
                    import random

                    proxy = random.choice(proxies)
                    # Prefer returning a link/URI if available, else the full JSON
                    proxy_str = proxy.get("link") or str(proxy)

                    # Escape for Markdown? simple backticks usually work
                    await update.message.reply_text(
                        f"🌍 *Proxy for {country}*\n```\n{proxy_str}\n```",
                        parse_mode=ParseMode.MARKDOWN,
                    )
                else:
                    await update.message.reply_text(
                        f"❌ No proxies found for {country}."
                    )
            else:
                await update.message.reply_text(
                    f"❌ Country {country} not available or invalid."
                )
        except Exception as e:
            await update.message.reply_text(f"⚠️ Error: {str(e)}")


async def sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🔗 *Subscription Links*\n"
        f"Clash: `{BASE_URL}/clash.yaml`\n"
        f"SingBox: `{BASE_URL}/singbox.json`\n"
        f"Base64: `{BASE_URL}/vpn_subscription_base64.txt`"
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)


def run_bot(token: str):
    """Run the bot polling loop."""
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("get", get_proxy))
    application.add_handler(CommandHandler("sub", sub))

    print("🤖 Bot is starting polling...")
    application.run_polling()
