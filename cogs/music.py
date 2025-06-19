from dataclasses import field
import discord
import wavelink

from typing import Dict, cast, List, Optional
from discord.ext import commands
from discord.ui import Button, View


class ChoiceButton(Button['Choice']):
    def __init__(self, label, choice: int):
        super().__init__(label=label, style=discord.ButtonStyle.blurple)
        self.choice = choice

    async def callback(self, interaction: discord.Interaction):
        if self.view is None:
            return

        view: MusicChoicePicker = self.view
        view.current_choice = self.choice

        await interaction.response.send_message(f"You picked {self.choice + 1}",
                                                ephemeral=True)
        view.stop()
        

class MusicChoicePicker(View):
    def __init__(self, choices):
        super().__init__()
        self.choices = choices
        self.current_choice: int | None = None

        for i, _ in enumerate(choices):
            choice_num = str(i + 1)
            self.add_item(ChoiceButton(choice_num, i))
    
    @discord.ui.button(label="Cancel", row=1, style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message('Cancelling.', ephemeral=True)

        self.stop()


class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.hybrid_command()
    async def skip(self, ctx: commands.Context) -> None:
        """Skip the current song."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.skip(force=True)
        try:
            await ctx.message.add_reaction("\u2705")
        except discord.NotFound:
            await ctx.send("Skipped current song.")
    
    @commands.hybrid_command(name="toggle", aliases=["pause", "resume"])
    async def music_toggle(self, ctx: commands.Context) -> None:
        """Pause or resume the player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.pause(not player.paused)
        try:
            await ctx.message.add_reaction("\u2705")
        except discord.NotFound:
            state = "Paused"
            if not player.paused:
                state = "Resumed"

            await ctx.send(f"{state} current song.")

    @commands.hybrid_command(aliases=["dc"])
    async def disconnect(self, ctx: commands.Context) -> None:
        """Disconnect the player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        await player.disconnect()
        try:
            await ctx.message.add_reaction("\u2705")
        except discord.NotFound:
            await ctx.send(f"Disconnected from the voice channel.")
    
    @commands.hybrid_command()
    async def volume(self, ctx: commands.Context, value: int) -> None:
        """Adjust the volume of the player."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            return

        # 100 is the max volume in the client side 
        max_volume = 100
        if value > max_volume:
            value = max_volume

        # While 50 will be the max for the player.
        bound = value / max_volume
        adjusted_volume = int(bound * 50)

        await player.set_volume(adjusted_volume)
        await ctx.send(f"Adjusted the volume to: `{value}`.")
    
    @commands.hybrid_command()
    async def queue(self, ctx: commands.Context) -> None:
        """Lists the songs currently in the queue."""
        player: wavelink.Player = cast(wavelink.Player, ctx.voice_client)
        if not player:
            await ctx.send("No one is currently playing anything.")
            return
        
        embed = discord.Embed(title="Queue")
        queue_size = len(player.queue)
        queue_limit = 15

        if queue_size <= 15:
            queue_limit = len(player.queue)
        elif queue_size == 0:
            await ctx.send("There is nothing in the queue")
            return

        embed.add_field(name="", value="".join(f"{i + 1}). {player.queue[i].title} - {player.queue[i].author}\n" for i in range(0, queue_limit)))
        await ctx.send(embed=embed)

    @commands.hybrid_command(name="play")
    async def play(self, ctx: commands.Context, *, query: str) -> None:
        """Play a song from the local database"""
        if not ctx.guild:
            return

        player = await self.get_player(ctx)
        if not player:
            return

        result = await self.search_track(ctx, query)
        if not result:
            return
        choice, tracks = result

        if isinstance(tracks, wavelink.Playlist):
            # tracks is a playlist...
            added: int = await player.queue.put_wait(tracks)
            await ctx.send(f"Added the playlist **`{tracks.name}`** ({added} songs) to the queue.")
        else:
            if len(tracks) > 1:
                track: wavelink.Playable = tracks[choice]
            else:
                track: wavelink.Playable = tracks[0]

            await player.queue.put_wait(track)
            await ctx.send(f"Added **`{track.title}`** to the queue.")

        if not player.playing:
            # Play now since we aren't playing anything...
            await player.play(player.queue.get(), volume=30)

        # Optionally delete the invokers message...
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass
    
    @commands.hybrid_group(name="playlist")
    async def playlist(self, ctx: commands.Context) -> None:
        pass

    @playlist.command(name="create")
    async def playlist_create(self, ctx: commands.Context, name: str) -> None:
        """Create a playlist in this server."""
        async with self.bot.db.acquire() as db:
            search_query = """
                SELECT COUNT(playlist_id) FROM playlist 
                    WHERE playlist_name LIKE $1 AND
                    guild_id = $2;
            """

            result = await db.fetchval(search_query, f"{name}", ctx.guild.id)
            if result:
                await ctx.send("A playlist with that name already exists in this guild.",
                                ephemeral=True)
                return
        
            add_query = """
                INSERT INTO playlist (guild_id, user_id, playlist_name)
                    VALUES ($1, $2, $3)
            """
            result = await db.execute(add_query, ctx.guild.id, ctx.author.id, name)
            await ctx.send(f"Playlist `{name}` has been created in this guild.")

    @playlist.command(name="add")
    async def playlist_add(self, ctx: commands.Context, playlist: str, song: str) -> None:
        """Add a song into a specific playlist"""
        async with self.bot.db.acquire() as db:
            search_query = """
                SELECT COUNT(playlist_id) FROM playlist 
                    WHERE playlist_name LIKE $1 AND
                    guild_id = $2;
            """
            playlist_id = await db.fetchval(search_query, f"{playlist}", ctx.guild.id)
            if playlist_id:
                await ctx.send("That playlist does not exist.",
                                ephemeral=True)
                return
            
            track_query = """
                SELECT * FROM tracks
                    WHERE track_name ILIKE $1
            """

            track_id = await db.fetch(track_query, f"%{song}%")
            choice = 0
            add_query = """
                INSERT INTO playlist_tracks (playlist_id, track_id)
                    VALUES ($1, $2)
            """
            if len(track_id) == 1:
                await db.execute(add_query, playlist_id['playlist_id'], track_id[0]['track_id'])
                await ctx.send(f"That song has been added to {playlist}",
                                ephemeral=True)

                return
            elif len(track_id) > 1:
                norm_tracks = self.normalized_tracks(track_id, 5)
                choice = await self.music_choices(ctx, norm_tracks)
                if choice is None:
                    return
                
                await db.execute(add_query, playlist_id['playlist_id'], track_id[choice]['track_id'])
                await ctx.send(f"That song has been added to {playlist}",
                                ephemeral=True)

                return
            
            search_result = await self.search_track(ctx, song)
            if search_result is None:
                return
            
            choice, search = search_result
            new_track_query = """
                INSERT INTO tracks (track_name, track_uri)
                    VALUES ($1, $2)
                RETURNING track_id
            """

            if len(search) == 1:
                choice = 0

            track_id = await db.fetchval(new_track_query,
                                              search[choice].title,
                                              search[choice].uri)
            await db.execute(add_query, playlist_id['playlist_id'], track_id)

            await ctx.send(f"{search[choice]} has been added into the playlist {playlist}.")
    
    @playlist.command(name="album")
    async def playlist_album(self, ctx: commands.Context, album: str) -> None:
        """Play a specifc album in the local library."""
        async with self.bot.db.acquire() as db:
            album_query = """
                SELECT * FROM album
                    WHERE album_name ILIKE $1
                    LIMIT 5;
            """

            albums = await db.fetch(album_query, f"%{album}%")
            choice = 0
            if not albums:
                return
            elif len(albums) > 1:
                embed = discord.Embed(title="Album search results.")
                embed.add_field(name="", value="".join(f"{i + 1}). {album['album_name']}\n" for i, album in enumerate(albums)))
                view = MusicChoicePicker(albums)

                await ctx.send(view=view, embed=embed, ephemeral=True)

                await view.wait()
                if view.current_choice is None:
                    return
                else:
                    choice= view.current_choice
            
            tracks_query = """
                SELECT song_path FROM song
                    WHERE album_id = $1;
            """

            tracks = await db.fetch(tracks_query, albums[choice]["album_id"])

        player = await self.get_player(ctx)
        if not player:
            return
        
        for track in tracks:
            uri = track['song_path']
            result: wavelink.Search = await wavelink.Playable.search(uri, source=None)
            if not result:
                result = await wavelink.Playable.search(uri)

                if not result:
                    yt = wavelink.TrackSource.YouTube
                    result = await wavelink.Playable.search(uri, source=yt)
            
            await player.queue.put_wait(result[0])
        if not player.playing:
            # Play now since we aren't playing anything...
            await player.play(player.queue.get(), volume=30)
            
        await ctx.send(f"{albums[choice]["album_name"]} has been added to the queue.")

    @playlist.command(name="import")
    async def playlist_import(self, ctx: commands.Context) -> None:
        pass

    @playlist.command(name="list")
    async def playlist_list(self, ctx: commands.Context, playlist: str) -> None:
        """List songs in a specific playlist"""
        async with self.bot.db.acquire() as db:
            playlist_query = """
                SELECT playlist_id, playlist_name FROM playlist 
                    WHERE playlist_name LIKE $1 AND
                    guild_id = $2;
            """

            playlist_info = await db.fetchrow(playlist_query, f"{playlist}", ctx.guild.id)
            if not playlist_info:
                await ctx.send("That playlist does not exist.",
                                ephemeral=True)
                return

            tracks_query = """
                SELECT * FROM playlist_tracks 
                    INNER JOIN tracks ON playlist_tracks.track_id=tracks.track_id
                    WHERE playlist_id = $1
            """
            tracks = await db.fetch(tracks_query, playlist_info['playlist_id'])

            embed = discord.Embed(title=playlist_info['playlist_name'])
            if len(tracks) >= 1:
                embed.add_field(name="", value="".join(f"{i + 1}). {track['track_name']}\n" for i, track in enumerate(tracks)))

            await ctx.send(embed=embed)
    
    @playlist.command(name="play")
    async def playlist_play(self, ctx: commands.Context, playlist: str) -> None:
        """Play a playlist"""
        if not ctx.guild:
            return

        player = await self.get_player(ctx)
        if not player:
            return

        async with self.bot.db.acquire() as db:
            playlist_query = """
                SELECT playlist_id, playlist_name FROM playlist 
                    WHERE playlist_name LIKE $1 AND
                    guild_id = $2;
            """

            playlist_info = await db.fetchrow(playlist_query, f"{playlist}", ctx.guild.id)
            if not playlist_info:
                await ctx.send("That playlist does not exist.",
                                ephemeral=True)
                return

            tracks_query = """
                SELECT * FROM playlist_tracks 
                    INNER JOIN tracks ON playlist_tracks.track_id=tracks.track_id
                    WHERE playlist_id = $1
            """
            tracks = await db.fetch(tracks_query, playlist_info['playlist_id'])

            for track in tracks:
                uri = track['track_uri']
                result: wavelink.Search = await wavelink.Playable.search(uri, source=None)
                if not result:
                    result = await wavelink.Playable.search(uri)

                    if not result:
                        yt = wavelink.TrackSource.YouTube
                        result = await wavelink.Playable.search(uri, source=yt)
                
                await player.queue.put_wait(result[0])
            if not player.playing:
                # Play now since we aren't playing anything...
                await player.play(player.queue.get(), volume=30)
            
            await ctx.send(f"{playlist} has been added to the queue.")

    @commands.command(name="clear")
    async def queue_clear(self, ctx: commands.Context) -> None:
        """Clear a playlist"""
        if not ctx.guild:
            return

        player = await self.get_player(ctx)
        if not player:
            return
        
        player.queue.clear()
        await ctx.send("Queue cleared.")

    async def search_track(self, ctx: commands.Context,
                           query: str) -> tuple[int, wavelink.Search] | None:
        choice = 0
        tracks = None
        async with self.bot.db.acquire() as db:
            result = await db.fetch(
                """SELECT song_path, song_name, artist_id FROM song
                        WHERE song_name ILIKE $1""",
                f"%{query}%"
            )

            if len(result) > 1:
                result = await db.fetch(
                    """SELECT song_name, artist_name, song_path FROM song
                        LEFT JOIN artist ON song.artist_id = artist.artist_id
                        WHERE song_name ILIKE $1 LIMIT 5""",
                    f"%{query}%"
                )
                choice = await self.music_choices(ctx, result)

                if choice is None:
                    return None

                result = result[choice]['song_path']
                tracks: wavelink.Search = await wavelink.Playable.search(result,
                                                                        source=None)
            elif len(result) == 1:
                result = result[0]['song_path']
                tracks: wavelink.Search = await wavelink.Playable.search(result,
                                                                        source=None)
            else:
                # Search via Youtube Music.
                tracks: wavelink.Search = await wavelink.Playable.search(query)
                if not isinstance(tracks, wavelink.Playlist) and len(tracks) > 1:
                    result = self.normalized_tracks(tracks, 5)
                    choice = await self.music_choices(ctx, result)

                    if choice is None:
                        return None
                elif not tracks:
                    # Otherwise search through normal Youtube.
                    yt = wavelink.TrackSource.YouTube
                    tracks: wavelink.Search = await wavelink.Playable.search(query, source=yt)

                    if not tracks:
                        await ctx.send("No tracks can be found with that query.")
                        return None
            
            return (choice, tracks)

    @classmethod
    def normalized_tracks(cls, tracks: wavelink.Search | Dict, limit: int) -> List[Dict]:
        norm_tracks: List[Dict] = []
        if len(tracks) < limit:
            limit = len(tracks)

        for i in range(0, limit):
            if isinstance(tracks, type(wavelink.Playable)):
                norm_tracks.append({
                    "song_name": tracks[i],
                    "artist_name": tracks[i].author
                })
            else:
                norm_tracks.append({
                    "song_name": tracks[i]['track_name'],
                    "artist_name": tracks[i]['track_id']
                })
        
        return norm_tracks

    @classmethod
    async def music_choices(cls, ctx: commands.Context, choices: List[Dict]) -> Optional[int]:
        embed = discord.Embed(title="Results")
        embed.add_field(name="", value="".join(f"{i + 1}). {choice['song_name']} - {choice['artist_name']}\n" for i, choice in enumerate(choices)))

        view = MusicChoicePicker(choices)
        await ctx.send(embed=embed, view=view, ephemeral=True)

        await view.wait()
        if view.current_choice is None:
            return None
        else:
            return view.current_choice
    
    @classmethod
    async def get_player(cls, ctx: commands.Context) -> wavelink.Player | None:
        player: wavelink.Player
        player = cast(wavelink.Player, ctx.voice_client)

        if not player:
            try:
                player = await ctx.author.voice.channel.connect(cls=wavelink.Player)  # type: ignore
            except AttributeError:
                await ctx.send("Please join a voice channel first before using this command.")
                return None
            except discord.ClientException:
                await ctx.send("I was unable to join this voice channel. Please try again.")
                return None
        
        if not hasattr(player, "home"):
            player.home = ctx.channel
        elif player.home != ctx.channel:
            await ctx.send(f"You can only play songs in {player.home.mention}, as the player has already started there.")
            return None
        
        player.autoplay = wavelink.AutoPlayMode.partial
        return player

async def setup(bot: commands.Bot) -> None:

    await bot.add_cog(Music(bot))