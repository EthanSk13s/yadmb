# YADMB (Yet Another Discord Music Bot)
I was unsatisfied with how music bots worked and I wanted to play
music from my local machine.

## Features:
- Playing music locally via search.
- Ability to play (most) youtube links.
- Basic playlist support.

## Setup
### Prerequisites:
- Python 3.10
- PostgreSQL

1) Clone the repository.
2) Initialize a virtual environment via:
    ```
    python -m venv .venv
    ``` 
    Change into the virtual environment via

    Unix:
    ```
    source .venv/bin/activate
    ```

    Windows:
    ```
    .venv\Scripts\activate.bat
    ```
3) Insall requirements.
    ```
    pip install -r requirements.txt
    ```
4) Create a `config.py` file see `example_config.py` for setup.
5) Install Lavalink [here](https://github.com/lavalink-devs/Lavalink/releases). Place the jar file into `bin/lavalink`.
6. Configure lavalink, see `bin/lavalink/example_application.yml`.
The only thing that you should really need to configure is the port and password. For the OAUTH setup see their plugin [page](https://github.com/lavalink-devs/youtube-source?tab=readme-ov-file#using-oauth-tokens).
7. Run `db_setup.py`.

## Running the bot
1. Launch the lavalink server.
    - Note for lavalink to pickup the `application.yml`, the current working directory must be `/bin/lavalink/
    ```
    java -jar lavalink.jar
    ```
2. Run `bot.py`. Have fun!