import json

from src.replay_data_explorer.services.data_loader import DataLoaders


class StubPlayer:
    def __init__(self, username: str, battle_rating: float):
        self.username = username
        self.country = "Germany"
        self.battle_rating = battle_rating

    def to_json(self) -> str:
        return json.dumps(
            {
                "username": self.username,
                "country": self.country,
                "battle_rating": self.battle_rating,
            }
        )


class StubReplay:
    def __init__(
        self,
        session_id: str,
        level_settings: str,
        replay_br: float,
        author_br: float,
    ):
        self.session_id = session_id
        self.level_settings = level_settings
        self.battle_rating = replay_br
        self.author = StubPlayer("Ranol", author_br)
        self.players = [self.author, StubPlayer("teammate", replay_br)]

    def to_json(self) -> str:
        return json.dumps(
            {
                "session_id": self.session_id,
                "level_settings": self.level_settings,
                "battle_rating": self.battle_rating,
                "players": [],
            }
        )


class StubReplayManager:
    def __init__(self, replays: dict[str, StubReplay]):
        self.loaded_replays = replays

    def iter_loaded_replays(self, *, release: bool = False):
        yield from self.loaded_replays.items()


def test_performance_data_excludes_event_and_race_replays() -> None:
    event_replay = StubReplay(
        "event-session",
        "gamedata/missions/cta/events/tanks/great_war/great_war_dom.blk",
        replay_br=14.7,
        author_br=1.3,
    )
    regular_replay = StubReplay(
        "regular-session",
        "gamedata/missions/cta/tanks/berlin/berlin_dom.blk",
        replay_br=9.3,
        author_br=9.3,
    )
    replay_above_history_max = StubReplay(
        "above-player-max-session",
        "gamedata/missions/cta/tanks/berlin/berlin_dom.blk",
        replay_br=10.3,
        author_br=9.3,
    )
    outlier_replay = StubReplay(
        "outlier-session",
        "gamedata/missions/cta/tanks/berlin/berlin_dom.blk",
        replay_br=14.7,
        author_br=1.3,
    )
    race_replay = StubReplay(
        "race-session",
        "gamedata/missions/cta/ffa_race/finland_tank_race/finland_tank_race_v1_race_inverted.blk",
        replay_br=12.7,
        author_br=4.0,
    )
    manager = StubReplayManager(
        {
            "event.json": event_replay,
            "regular.json": regular_replay,
            "above-history-max.json": replay_above_history_max,
            "outlier.json": outlier_replay,
            "race.json": race_replay,
        }
    )
    data_loaders = DataLoaders(manager)

    player_data = data_loaders.get_player_performance_data("Ranol")
    global_data = data_loaders.get_global_performance_data()

    assert player_data["session_id"].tolist() == ["regular-session"]
    assert global_data["session_id"].tolist() == [
        "regular-session",
        "regular-session",
        "above-player-max-session",
        "above-player-max-session",
        "outlier-session",
        "outlier-session",
    ]
