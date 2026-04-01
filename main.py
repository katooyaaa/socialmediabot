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

            await self.db.connect()
            print("DB verbunden", flush=True)

            await self.db.create_tables()
            print("Tabellen geprüft", flush=True)

            print("Lade Cogs...", flush=True)
            await self.load_extension("cogs.accounts")
            await self.load_extension("cogs.posts")
            await self.load_extension("cogs.help")
            print("Cogs geladen", flush=True)

        except Exception:
            print("FEHLER in setup_hook()", flush=True)
            traceback.print_exc()
            raise

    async def close(self):
        try:
            await self.db.close()
        except Exception:
            traceback.print_exc()
        await super().close()


bot = SocialBot()


@bot.event
async def on_ready():
    print(f"Eingeloggt als {bot.user} ({bot.user.id})", flush=True)
    print(f"Guilds: {[f'{g.name} ({g.id})' for g in bot.guilds]}", flush=True)

    if not bot.synced_once:
        total = 0

        for guild in bot.guilds:
            try:
                bot.tree.copy_global_to(guild=guild)
                synced = await bot.tree.sync(guild=guild)

                print(
                    f"{len(synced)} Commands für Guild '{guild.name}' ({guild.id}) synchronisiert.",
                    flush=True
                )
                total += len(synced)

            except Exception:
                print(f"Fehler beim Sync für Guild '{guild.name}' ({guild.id})", flush=True)
                traceback.print_exc()

        print(f"Guild-Sync abgeschlossen. Insgesamt synchronisierte Commands: {total}", flush=True)
        bot.synced_once = True


@bot.command(name="ping")
async def ping(ctx: commands.Context):
    await ctx.send("pong")


@bot.command(name="help")
async def prefix_help(ctx: commands.Context):
    await ctx.send(
        "Slash-Commands: /createaccount, /selectaccount, /createpost, /accounts, /myaccounts, /deleteaccount, /help"
    )


@bot.event
async def on_raw_reaction_add(payload: discord.RawReactionActionEvent):
    if payload.user_id == bot.user.id:
        return

    emoji = str(payload.emoji)

    if emoji == "❤️":
        await bot.db.like_post(
            message_id=payload.message_id,
            user_id=payload.user_id
        )
    elif emoji == "💔":
        await bot.db.dislike_post(
            message_id=payload.message_id,
            user_id=payload.user_id
        )


@bot.event
async def on_raw_reaction_remove(payload: discord.RawReactionActionEvent):
    emoji = str(payload.emoji)

    if emoji == "❤️":
        await bot.db.unlike_post(
            message_id=payload.message_id,
            user_id=payload.user_id
        )
    elif emoji == "💔":
        await bot.db.undislike_post(
            message_id=payload.message_id,
            user_id=payload.user_id
        )


async def main():
    print("Starte den Bot-Prozess...", flush=True)

    if not TOKEN:
        print("FEHLER: Kein DISCORD_TOKEN gefunden", flush=True)
        return

    if not DATABASE_URL:
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
        print("Fehler beim Starten des Bots:", flush=True)
        traceback.print_exc()
    finally:
        if not bot.is_closed():
            await bot.close()


if __name__ == "__main__":
    asyncio.run(main())