# Warthog
**War Th**under L**og**ger: stats acquisition tool for the game client

It's ridiculous that detailed battle information isn't presented anywhere, so here's a solution to acquire the data! Warthog will automatically drive War Thunder's UI to grab info about recent battles from the Battles tab of the Messages UI, then ingest that information into a useful JSON format before deduping and saving the data.

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
- Open project in VSCode
- Navigate to the "Run and Debug" panel
- Pick the "Run: Warthog" launch option
- Click "Start Debugging"

Data is stored by default in `warthog/data`. Tools to explore and graph that data are coming soon(tm).
