# Warthog
**War Th**under L**og**ger: data acquisition and analysis tool for War Thunder

## Why?

War Thunder's [matchmaking](https://wiki.warthunder.com/mechanics/matchmaking) is frustrating, and I don't think that's an uncommon sentiment. I primarily play Ground Realistic Battles, and it feels as though I'm very frequently uptiered (being inserted at or near the bottom of the match's battle rating bracket, and thus competing against more powerful enemies), regardless of squad size. However I didn't have any data to back this up, thus Warthog was created to help process local replay data to quantify these results.

However, since War Thunder replays expose a decent amount of data, it's also possible to look into more than just uptiers and downtiers. On the more innocuous side of things, there's player performance graphs available that chart your own performance at different battle ratings, score distribution, heatmapped performance for battle ratings and countries, battle rating deltas, etc. However, since War Thunder also offers some absurdly expensive (and shockingly powerful) vehicles that can be purchased with real-life money, I've also been cooking up some graphs that explore the performance of players with premium vehicles in their lineup.

## Setup

### Prerequisites
- Python 3.12 or greater installed

### Installation
- `git clone https://github.com/naschorr/warthog`
- `cd warthog`
- `python -m venv venv`
- Activate your virtual environment: `.\venv\Scripts\activate`
- `pip install -r .\requirements.txt`

#### VSCode
- Set the interpreter:
    - Open command palette: `Ctrl+P`
    - Select the interpreter: `Python: Select Interpreter`
    - Select the virtual environment's interpreter from the dropdown (it should have `venv` in it)
- Make sure the "Jupyter" extension is installed:
    - Open the extensions panel: `Ctrl+Shift+X`
    - Search for "Jupyter" from Microsoft
    - Hit the install button

## Running It
Warthog has a few different options, and they can be easily run inside VSCode:

- Open the project in VSCode
- Navigate to the "Run and Debug" panel (Ctrl+Shift+D)
- Pick the launch option that corresponds to what you'd like to do (more info below).
- Click "Start Debugging" (F5)

When running it for the first time, I'd recommend running the [`VehicleDataGrabber`](#vehicledatagrabber) launch option, then the [`ReplayDataGrabber - War Thunder`](#replaydatagrabber---war-thunder) launch option. This'll first populate the vehicle data prerequisites, then start converting your replay data into a more usable JSON replay.

### Launch Options

#### `ReplayDataGrabber - War Thunder (Overwrite)`
Iterates over the War Thunder replay directory, translating them into JSON replays for future usage. This one will overwrite existing JSON replays, if encountered. Make sure to set the War Thunder replay directory in the `src/config.json`!

#### `ReplayDataGrabber - War Thunder`
Iterates over the War Thunder replay directory, translating them into JSON replays for future usage. Make sure to set the War Thunder replay directory in the `src/config.json`!

#### `VehicleDataGrabber`
Retrieves datamined vehicle data (battle ratings, vehicle type, names, etc.) for all vehicles in War Thunder releases between now and your first JSON replay data. This vehicle data is then used to power the [analysis](#analysis).

### Development Specific Launch Options

#### `Dev - ReplayDataGrabber - Copied Replays`
Iterates over the local copied replay store, translating them into JSON replays for future usage. This is handy to mass update JSON replays if the schema ever changes.

#### `Dev - ReplayDataCopier`
Copies War Thunder replay data from the temporary game directory to a local copied replay store. This is handy to keep an archive of all replay data, again to rebuild the JSON replays if the schema ever changes.

## Analysis
Currently, analysis is done via graphs in a Jupyter Notebook located at `src/replay_data_explorer/player_data_explorer.ipynb`. Open it up and run through the cells!

## Contributing
Make sure that the notebook's outputs are cleared, so that things can stay clean. There's a git filter set up to run the `jupyter nbconvert` script to clean the outputs automatically, though it does need some first time setup. Simply run this command from the project root to register the `.gitconfig` that contains the filter to the local git config and it'll start working!

```shell
git config --local include.path ../.gitconfig
```
