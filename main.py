import os
import sys
import logging
import asyncio
import traceback
import discord
from discord.ext import commands
from dotenv import load_dotenv

from services.database import Database
import webserver

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("discord.log", encoding="utf-8", mode="w")
    ],
    force=True
)

logger = logging.getLogger("socialbot")

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.reactions = True
intents.guilds = True


class SocialBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="s!",
            intents=intents,
            help_command=None
        )
        self.db = Database(DATABASE_URL)
        self.synced_once = False

    async def setup_hook(self):
        try:
            logger.info("setup_hook gestartet")
            logger.info("Verbinde mit der Datenbank...")
            await self.db.connect()
            logger.info("DB verbunden")

            await self.db.create_tables()
            logger.info("Datenbank-Tabellen gecheckt")

            logger.info("Lade Cogs...")
            await self.load_extension("cogs.accounts")
            await self.load_extension("cogs.posts")
            await self.load_extension("cogs.help")
            logger.info("Cogs geladen")

            for cmd in self.tree.get_commands():
                logger.info(f"LOKALER COMMAND: /{cmd.name}")
                logger.info(f"PARAMETER: {[p.name for p in cmd.parameters]}")

        except Exception:
            logger.exception("FEHLER in setup_hook")
            raise

    async def close(self):
        logger.info("Schließe Bot und Datenbank...")
        try:
            await self.db.close()
        except Exception:
            logger.exception("Fehler beim Schließen der Datenbank")
        await super().close()


bot = SocialBot()


@bot.event
async def on_connect():
    logger.info("Mit Discord verbunden (on_connect)")

@bot.event
async def on_ready():
    logger.info(f"Eingeloggt als {bot.user} (ID: {bot.user.id})")
    logger.info(f"Guilds: {[f'{g.name} ({g.id})' for g in bot.guilds]}")

    if not bot.synced_once:
        synced_total = 0

        for guild in bot.guilds:
            try:
                synced = await bot.tree.sync(guild=guild)
                logger.info(f"{len(synced)} Commands für Guild '{guild.name}' ({guild.id}) synchronisiert")
                synced_total += len(synced)
            except Exception:
                logger.exception(f"Fehler beim Sync für Guild '{guild.name}' ({guild.id})")

        logger.info(f"Guild-Sync abgeschlossen. Insgesamt synchronisierte Commands: {synced_total}")
        bot.synced_once = True


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    if str(payload.emoji) != "❤️":
        return

    await bot.db.like_post(
        message_id=payload.message_id,
        user_id=payload.user_id
    )


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    if str(payload.emoji) != "❤️":
        return

    await bot.db.unlike_post(
        message_id=payload.message_id,
        user_id=payload.user_id
    )


async def main():
    logger.info("Starte den Bot-Prozess...")

    if not TOKEN:
        logger.error("Kein DISCORD_TOKEN gefunden")
        return

    if not DATABASE_URL:
        logger.error("Kein DATABASE_URL gefunden")
        return

    logger.info(f"TOKEN vorhanden: {TOKEN[:8]}...")
    logger.info(f"DATABASE_URL vorhanden: {DATABASE_URL[:30]}...")

    logger.info("Starte Webserver...")
    webserver.keep_alive()

    try:
        logger.info("Versuche Login bei Discord...")
        await bot.start(TOKEN, reconnect=True)
    except KeyboardInterrupt:
        logger.info("Bot wird beendet...")
    except Exception:
        logger.exception("Fehler beim Starten des Bots")
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception:
        traceback.print_exc()
        raise