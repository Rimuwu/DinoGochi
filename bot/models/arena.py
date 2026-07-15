from typing import List, Dict, Any, Optional
from beanie import Document, Link, PydanticObjectId
from pymongo import IndexModel, ASCENDING, DESCENDING
from bot.models.base_private import PrivateModelMixin

class ArenaPlayerModel(PrivateModelMixin, Document):
    userid: int
    elo_solo: int = 1000
    elo_group: int = 1000
    wins_solo: int = 0
    losses_solo: int = 0
    wins_group: int = 0
    losses_group: int = 0
    free_battles_used: int = 0
    tickets_used: int = 0
    last_reset_date: str = ""
    win_streak_solo: int = 0
    win_streak_group: int = 0
    ban_end_time: int = 0
    last_battle_time: int = 0
    last_decay_time: int = 0

    class Settings:
        name = "arena_players"
        indexes = [
            IndexModel([("userid", ASCENDING)], unique=True, name="userid_idx"),
            IndexModel([("elo_solo", DESCENDING)], name="elo_solo_idx"),
            IndexModel([("elo_group", DESCENDING)], name="elo_group_idx")
        ]

class ArenaSeasonModel(PrivateModelMixin, Document):
    season_number: int = 1
    start_time: int
    end_time: int
    rewards: dict = {}

    class Settings:
        name = "arena_seasons"

class ArenaQueueModel(PrivateModelMixin, Document):
    userid: int
    dino_ids: List[PydanticObjectId]
    category: str  # 'solo' or 'group'
    joined_time: int
    elo: int
    bag_items: List[dict]
    is_free_attempt: bool

    class Settings:
        name = "arena_queue"
        indexes = [
            IndexModel([("userid", ASCENDING)], unique=True, name="queue_userid_idx"),
            IndexModel([("category", ASCENDING)], name="queue_category_idx")
        ]

class ArenaMatchModel(PrivateModelMixin, Document):
    player_a_id: int
    player_b_id: int
    player_a_name: str
    player_b_name: str
    player_a_dinos: List[PydanticObjectId]
    player_b_dinos: List[PydanticObjectId]
    player_a_bag: List[dict]
    player_b_bag: List[dict]
    player_a_free: bool
    player_b_free: bool
    player_a_ready: Optional[bool] = None
    player_b_ready: Optional[bool] = None
    player_a_msg_id: Optional[int] = None
    player_b_msg_id: Optional[int] = None
    category: str
    created_at: int
    expires_at: int

    class Settings:
        name = "arena_matches"

class ArenaBattleModel(PrivateModelMixin, Document):
    userid_a: int
    userid_b: int
    username_a: str
    username_b: str
    category: str
    winner_id: int  # 0 for draw, userid of winner otherwise
    elo_change_a: int
    elo_change_b: int
    battle_time: int
    dinos_a: List[str] = []
    dinos_b: List[str] = []

    class Settings:
        name = "arena_battles"
        indexes = [
            IndexModel([("userid_a", ASCENDING)], name="battle_userid_a_idx"),
            IndexModel([("userid_b", ASCENDING)], name="battle_userid_b_idx"),
            IndexModel([("battle_time", DESCENDING)], name="battle_time_idx")
        ]
