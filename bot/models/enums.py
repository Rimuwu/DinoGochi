from enum import Enum

class DinoStatus(str, Enum):
    PASS = 'pass'
    SLEEP = 'sleep'
    UNRESTRAINED_PLAY = 'unrestrained_play'
    GAME = 'game'
    JOURNEY = 'journey'
    COLLECTING = 'collecting'
    KINDERGARTEN = 'kindergarten'
    HYSTERIA = 'hysteria'
    FARM = 'farm'
    MINE = 'mine'
    BANK = 'bank'
    SAWMILL = 'sawmill'
    GYM = 'gym'
    LIBRARY = 'library'
    PARK = 'park'
    SWIMMING_POOL = 'swimming_pool'
    CRAFT = 'craft'
    INACTIVE = 'inactive'

class MoodType(str, Enum):
    MOOD_EDIT = 'mood_edit'
    MOOD_WHILE = 'mood_while'
    BREAKDOWN = 'breakdown'
    INSPIRATION = 'inspiration'

class StatType(str, Enum):
    HEAL = 'heal'
    EAT = 'eat'
    GAME = 'game'
    MOOD = 'mood'
    ENERGY = 'energy'

class ActivityType(str, Enum):
    SLEEP = 'sleep'
    GAME = 'game'
    JOURNEY = 'journey'
    COLLECTING = 'collecting'
    TRAINING = 'training'
    WORK = 'work'
    CRAFT = 'craft'

class ReferralType(str, Enum):
    GENERAL = 'general'
    SUB = 'sub'

class FriendType(str, Enum):
    FRIENDS = 'friends'
    REQUEST = 'request'

class DinoOwnerType(str, Enum):
    OWNER = 'owner'
    ADD_OWNER = 'add_owner'
