import os
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
            print("setup_hook gestartet", flush=True)
            webserver.STATUS["setup_hook_started"] = True

            print("Verbinde mit der Datenbank...", flush=True)
            await self.db.connect()
            webserver.STATUS["db_connected"] = True
            print("DB verbunden", flush=True)

            await self.db.create_tables()
            webserver.STATUS["tables_created"] = True
            print("Tabellen geprüft", flush=True)

            print("Lade Cogs...", flush=True)
            await self.load_extension("cogs.accounts")
            await self.load_extension("cogs.posts")
            await self.load_extension("cogs.help")
            webserver.STATUS["cogs_loaded"] = True
            print("Cogs geladen", flush=True)

            for cmd in self.tree.get_commands():
                print(f"LOKALER COMMAND: /{cmd.name}", flush=True)
                print(f"PARAMETER: {[p.name for p in cmd.parameters]}", flush=True)

        except Exception:
            webserver.STATUS["last_error"] = traceback.format_exc()
            print("FEHLER in setup_hook()", flush=True)
            traceback.print_exc()
            raise

    async def close(self):
        try:
            await self.db.close()
        except Exception:
            webserver.STATUS["last_error"] = traceback.format_exc()
            traceback.print_exc()
        await super().close()


bot = SocialBot()


@bot.event
async def on_ready():
    print(f"Eingeloggt als {bot.user} (ID: {bot.user.id})", flush=True)

    webserver.STATUS["discord_ready"] = True
    webserver.STATUS["guilds"] = [f"{g.name} ({g.id})" for g in bot.guilds]

    print(f"Guilds: {webserver.STATUS['guilds']}", flush=True)

    if not bot.synced_once:
        for guild in bot.guilds:
            try:
                synced = await bot.tree.sync(guild=guild)
                print(f"{len(synced)} Commands für Guild '{guild.name}' ({guild.id}) synchronisiert.", flush=True)
            except Exception:
                webserver.STATUS["last_error"] = traceback.format_exc()
                print(f"Fehler beim Sync für Guild '{guild.name}' ({guild.id})", flush=True)
                traceback.print_exc()

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
    print("Starte den Bot-Prozess...", flush=True)

    webserver.STATUS["main_started"] = True
    webserver.STATUS["token_present"] = bool(TOKEN)
    webserver.STATUS["database_url_present"] = bool(DATABASE_URL)

    if not TOKEN:
        webserver.STATUS["last_error"] = "Kein DISCORD_TOKEN gefunden"
        print("FEHLER: Kein DISCORD_TOKEN gefunden", flush=True)
        return

    if not DATABASE_URL:
        webserver.STATUS["last_error"] = "Kein DATABASE_URL gefunden"
        print("FEHLER: Kein DATABASE_URL gefunden", flush=True)
        return

    print("Starte Webserver...", flush=True)
    webserver.keep_alive()

    try:
        print("Versuche Login bei Discord...", flush=True)
        await bot.start(TOKEN, reconnect=True)
    except KeyboardInterrupt:
        print("Bot wird beendet...", flush=True)
    except Exception:
        webserver.STATUS["last_error"] = traceback.format_exc()
        print("Fehler beim Starten des Bots:", flush=True)
        traceback.print_exc()
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())