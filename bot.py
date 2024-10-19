import asyncio
import logging
import asyncpg
import discord
import wavelink

from discord.ext import commands

from config import CONFIG


cogs = {
    "cogs.music"
}

class Bot(commands.Bot):
    def __init__(self) -> None:
        intents: discord.Intents = discord.Intents.default()
        intents.message_content = True

        discord.utils.setup_logging(level=logging.INFO)
        super().__init__(command_prefix=".ko", intents=intents)


    async def setup_hook(self) -> None:
        for cog in cogs:
            try:
                await self.load_extension(cog)
            except Exception as e:
                print(f"{type(e).__name__} : {e}")

        nodes = [wavelink.Node(uri=CONFIG["LL_HOST"], password=CONFIG["LL_PASS"])]

        await wavelink.Pool.connect(nodes=nodes, client=self, cache_capacity=100)

        self.db: asyncpg.pool.Pool = await asyncpg.create_pool(user=CONFIG["DB_USER"], database=CONFIG["DB_DATABASE"], host="127.0.0.1")

    async def on_wavelink_track_start(self, payload: wavelink.TrackStartEventPayload) -> None:
        player: wavelink.Player | None = payload.player
        if not player:
            # Handle edge cases...
            return

        original: wavelink.Playable | None = payload.original
        track: wavelink.Playable = payload.track

        embed: discord.Embed = discord.Embed(title="Now Playing")
        embed.description = f"**{track.title}** by `{track.author}`"

        if track.artwork:
            embed.set_image(url=track.artwork)

        if original and original.recommended:
            embed.description += f"\n\n`This track was recommended via {track.source}`"

        if track.album.name:
            embed.add_field(name="Album", value=track.album.name)

        await player.home.send(embed=embed)

bot = Bot()

@bot.command(name="sync")
async def slash_sync(ctx: commands.Context) -> None:
    cmds = await bot.tree.sync()

    await ctx.send("success")

@bot.command(name="ping")
async def ping(ctx: commands.Context) -> None:
    await asyncio.sleep(5)
    await ctx.send(ctx.author.mention)


async def main() -> None:
    async with bot:
        await bot.start(CONFIG["BOT_TOKEN"])


asyncio.run(main())
