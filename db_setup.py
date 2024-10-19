import asyncio
import asyncpg

from pathlib import Path
from tinytag import TinyTag

from config import CONFIG

LIB_PATH = Path(CONFIG["MUSIC_PATH"])

with open("setup.sql", 'r') as script:
    query = script.read()

async def run(lib_path: Path):
    conn: asyncpg.connection.Connection = await asyncpg.connect(user=CONFIG["DB_USER"],
                                                                database=CONFIG["DB_DATABASE"],
                                                                host="127.0.0.1")
    
    await conn.execute(query)

    await setup_lib(conn, lib_path)
    await conn.close()

def iter_dir(directory):
    for file in directory.iterdir():
        if file.is_dir():
            iter_dir(file)
        else:
            if TinyTag.is_supported(file):
                tag = TinyTag.get(file)
                print(file)

async def insert_data(conn: asyncpg.connection.Connection, tag: TinyTag, path: Path):
    artist = tag.artist
    if artist is None:
        artist = "Unknown"

    artist_query = "SELECT artist_id FROM artist WHERE artist_name = $1"
    result = await conn.fetchrow(artist_query, artist)

    if result is None:
        await conn.execute(
            "INSERT INTO artist (artist_name) VALUES ($1)",
            artist
        )

        result = await conn.fetchrow(artist_query, artist)
        artist_id = result['artist_id']
    else:
        artist_id = result['artist_id']

    album = tag.album
    if album is None:
        album = "Unknown"
    album_query = "SELECT album_id FROM album WHERE album_name = $1"
    result = await conn.fetchrow(album_query, album)
  
    if result is None:
        await conn.execute(
            "INSERT INTO album (album_name) VALUES ($1)",
            album
        )

        result = await conn.fetchrow(album_query, album)
        album_id = result['album_id']
    else:
        album_id = result['album_id']

    if tag.title is None:
        tag.title = "Unknown"

    await conn.execute(
        '''
        INSERT INTO song (song_name, song_path, artist_id, album_id)
            VALUES ($1, $2, $3, $4)
        ''',
        tag.title, str(path), artist_id, album_id
    )

    await conn.execute(
        '''
        INSERT INTO tracks (track_uri, track_name)
            VALUES ($1, $2)
        ''',
        str(path), tag.title
    )

async def setup_lib(conn: asyncpg.connection.Connection, lib_path: Path):
    for file in lib_path.iterdir():
        if file.is_dir():
            await setup_lib(conn, file)
        else:
            if TinyTag.is_supported(file):
                tag = TinyTag.get(file)
                await insert_data(conn, tag, file)


if __name__ == "__main__":
    asyncio.run(run(LIB_PATH))