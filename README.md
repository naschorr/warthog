# Warthog
**War Th**under L**og**ger: data acquisition tool for War Thunder

It's ridiculous that detailed historical performance information isn't presented anywhere, so here's a solution to collect and process the data! Warthog crawls through the War Thunder replays stored locally, processes them into simple JSON models, and exposes that data for future analysis

## Prerequisites
- Python 3.12 or greater installed
- War Thunder installed and running. Must be opened to the "Messages" screen.

## Installation
- `git clone https://github.com/naschorr/warthog`
- `cd warthog`
- `python -m venv venv`
- Activate your virtual environment: `.\venv\Scripts\activate`
- `pip install -r .\requirements.txt`
- Set the interpreter in VSCode:
    - Open command palette: `Ctrl+P`
    - Select the interpreter: `Python: Select Interpreter`
    - Select the virtual environment's interpreter from the dropdown (it should have `venv` in it)

## Running It
Warthog has a few different options, and they can be easily run inside VSCode:

- Open the project in VSCode
- Navigate to the "Run and Debug" panel (Ctrl+Shift+D)
- Pick the launch option that corresponds to what you'd like to do (more info below).
- Click "Start Debugging" (F5)

When running it for the first time, I'd recommend running the [Vehicle Data Grabber](#vehicle-data-grabber), then the [Replay Data Grabber - War Thunder](#replay-data-grabber)

### Replay Data Grabber
This pulls in War Thunder replay data from the replays directory, processes them into JSON, and precalculates some values (battle ratings, premium vehicles, timestamps, etc) to aid in future statistical analysis

### Vehicle Data Grabber
This pulls datamined vehicle data from the [datamine repository](https://github.com/gszabi99/War-Thunder-Datamine), correlates and formats it, and saves it. This happens for each game version, as vehicle stats can change between versions.

### Replay Data Copier
This handles copying replay data from your War Thunder game directory to a local folder for safe keeping as War Thunder will clear out old replays.
