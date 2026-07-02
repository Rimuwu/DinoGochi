---
name: dinogochi_project_guidelines
description: Guidelines for architecture, models, configurations, and game mechanics of Telegram DinoGochi bot
---

# DinoGochi Project Guidelines

This document describes the architecture, structure, database models, and core game mechanics of the **DinoGochi** Telegram bot (a virtual Tamagotchi-dinosaur game with RPG elements).

## 1. Technology Stack & Architecture

*   **Language**: Python 3.10+
*   **Telegram API**: [aiogram v3](../../../requirements.txt) (asynchronous library for Telegram bots).
*   **Database**: MongoDB accessed asynchronously via the [Beanie ODM](https://beanie-odm.dev) in [bot/dbmanager.py](../../../bot/dbmanager.py). All collections are unified inside a single `dinogochi` database.
*   **Image Generation**: [Pillow (PIL)](../../../bot/modules/images.py) for dynamically creating dinosaur profiles, egg incubation visual status, inventory displays, and item cards.
*   **Data Analysis**: `matplotlib` for generating charts of game statistics.
*   **Asynchronous Background Tasks**: A custom scheduling loop implemented in [bot/taskmanager.py](../../../bot/taskmanager.py).

---

## 2. Directory Structure & Key Files

The general structure of the project directory is organized as follows:

```text
DinoGochi/
├── .agents/
│   └── skills/
│       └── dinogochi_project_guidelines/
│           └── SKILL.md                 # This guidelines file
├── bot/
│   ├── config.py                        # Settings loader and validator
│   ├── const.py                         # Constants & static data loader
│   ├── dbmanager.py                     # Database connection, Beanie ODM init & APM logger
│   ├── exec.py                          # Bot execution setup and polling initiation
│   ├── taskmanager.py                   # Async loop scheduler
│   ├── models/                          # Beanie ODM/Pydantic schemas
│   │   ├── user.py
│   │   ├── dinosaur.py
│   │   ├── items.py
│   │   ├── market.py
│   │   ├── activity.py
│   │   ├── tavern.py
│   │   ├── tracking.py
│   │   ├── group.py
│   │   └── other.py
│   ├── dataclasess/                     # Type definitions and data schemas
│   │   ├── items/
│   │   │   └── base.py
│   │   └── minigame.py
│   ├── handlers/                        # aiogram handler modules
│   │   └── states.py
│   ├── json/                            # Static game databases
│   │   ├── settings.json
│   │   └── journey.json
│   ├── localization/                    # Localization files (JSON)
│   │   └── en.json
│   ├── modules/                         # Core game logic and subsystems
│   │   ├── dinosaur/
│   │   │   ├── dinosaur.py
│   │   │   └── mood.py
│   │   ├── states_fabric/
│   │   │   └── state_handlers.py
│   │   ├── user/
│   │   │   └── user.py
│   │   ├── functransport.py
│   │   ├── images.py
│   │   ├── localization.py
│   │   └── notifications.py
│   └── tasks/                           # Background schedulers/workers
│       └── incubation.py
├── main.py                              # Bot startup entrypoint
└── requirements.txt                     # Project dependencies
```

*   [`main.py`](../../../main.py) — The application entry point. Initializes and runs the bot.
*   [`bot/exec.py`](../../../bot/exec.py) — Declares `Bot` and `Dispatcher` instances (using MongoStorage for FSM state storage) and manages the polling startup lifecycle.
*   [`bot/config.py`](../../../bot/config.py) — Config deserialization and settings manager using `config.json`.
*   [`bot/dbmanager.py`](../../../bot/dbmanager.py) — Verifies MongoDB connectivity, creates missing databases, collections, and indexes, and populates required documents.
*   [`bot/const.py`](../../../bot/const.py) — Global helper that loads static JSON game configurations (mobs, items, dinosaur structures).
*   [`bot/taskmanager.py`](../../../bot/taskmanager.py) — Handles task loop registration and execution on the asyncio event loop.
*   [`bot/tasks/`](../../../bot/tasks/) — Submodules representing periodic checks (e.g. state/mood checks, sleep decay, journey ticks, auction checks).
*   [`bot/handlers/`](../../../bot/handlers/) — Telegram user action, command, message, and inline callback handlers.
*   [`bot/modules/`](../../../bot/modules/) — The core logic layer containing business logic models (dinosaur actions, user tracking, inventory handling, localization utilities).
*   [`bot/dataclasess/`](../../../bot/dataclasess/) — Helper dataclasses (e.g., base item descriptions, craft structures).
*   [`bot/json/`](../../../bot/json/) — Static JSON configurations defining database collections, items, achievements, quests, etc.
*   [`bot/localization/`](../../../bot/localization/) — Localization dictionaries for translating interface text (`ru.json`, `en.json`, `es.json`, `id.json`).

---

## 3. Data Models & Database Structure

All database models are implemented using **Beanie ODM** (inheriting from `beanie.Document`) and are stored in a single unified database named `dinogochi` on the MongoDB server. 

### Beanie Document Models (`bot/models/`)

1.  **User Models** — [`bot/models/user.py`](../../../bot/models/user.py)
    *   `UserModel` (collection `users`): Tracks user ID, balances (`coins`, `super_coins`), experience (`xp`, `lvl`), settings, and notification preferences.
    *   `LangModel` (collection `lang`): Stores user interface language settings.
    *   `ReferralModel` (collection `referals`), `FriendModel` (collection `friends`), `SubscriptionModel` (collection `subscriptions`), `AdModel` (collection `ads`), `DinoCollectionModel` (collection `dino_collection`), `AchievementModel` (collection `achievements`).
2.  **Dinosaur Models** — [`bot/models/dinosaur.py`](../../../bot/models/dinosaur.py)
    *   `DinoModel` (collection `dinosaurs`): Core stats (health, hunger, play, mood, energy), RPG characteristics, quality/rarity, activ_items, memories.
    *   `EggModel` (collection `incubation`): Incubation timers, quality, chosen pool, choosing status.
    *   `DeadDinoModel` (collection `dead_dinos`), `DinoOwnersModel` (collection `dino_owners`), `DinoMoodModel` (collection `dino_mood`), `StateModel` (collection `state`).
3.  **Item Models** — [`bot/models/items.py`](../../../bot/models/items.py)
    *   `ItemModel` (collection `items`): User inventory items (`owner_id`, `items_data`, `count`).
    *   `ItemCraftModel` (collection `item_craft`): Ongoing desktop item crafting progress.
    *   `FarmModel` (collection `farm`).
4.  **Market Models** — [`bot/models/market.py`](../../../bot/models/market.py)
    *   `ProductModel` (collection `products`): Trade deals (fixed items-for-coins, barters, auctions).
    *   `SellerModel` (collection `sellers`): Player-owned shops (earned coins, total sales, description).
    *   `PreferentialModel` (collection `preferential`), `PuhsModel` (collection `puhs`).
5.  **Other Collections**
    *   `activity.py` (kd_activity, long_activity, kindergarten).
    *   `tavern.py` (quests, tavern, daily_award, inside_shop).
    *   `tracking.py` (links, tracking_members).
    *   `group.py` (groups, messages, group_users).
    *   `other.py` (management, statistic, events, promo, dead_users, companies, message_log, states, boosters, onetime_rewards, lottery, lottery_members, online).

### Legacy/ActiveRecord Classes & Compatibility
The custom ActiveRecord-like Python wrapper classes (`User` in `bot/modules/user/user.py`, `Dino` and `Egg` in `bot/modules/dinosaur/dinosaur.py`) interact with the database. A compatibility proxy layer in [bot/dbmanager.py](../../../bot/dbmanager.py) wraps the `mongo_client` to transparently route all legacy database calls (`mongo_client.user.users`) to the unified `dinogochi` database and rename clashing collections (`group.users` -> `group_users`, etc.).

---

## 4. Core Game Mechanics

### A. Incubation & Birth
*   Using an egg item allows the user to choose 1 out of 3 random dinosaurs of the egg's rarity within a 12-hour period.
*   Once selected, the egg is incubated in the database. The background worker [`bot/tasks/incubation.py`](../../../bot/tasks/incubation.py) polls incubation times, creates the dinosaur object via `insert_dino()`, and alerts the player.

### B. Mood System
*   Activities like sleeping, eating, and playing fire mood triggers via [`add_mood()`](../../../bot/modules/dinosaur/mood.py).
*   **Breakdowns** (triggered at low mood): Dinosaurs may exhibit breakdown behaviors like seclusion, hysteria, or unrestrained play.
*   **Inspirations** (triggered at high mood): Temporary boosters affecting resource collecting, mini-games, journey events, and crafting.

### C. Journey Mechanics
*   Dinosaurs can be sent on wilderness journeys. The background checker [`bot/tasks/journey_check.py`](../../../bot/tasks/journey_check.py) evaluates random wilderness events based on the configuration [`bot/json/journey.json`](../../../bot/json/journey.json).
*   Events can be positive or negative, modifying stats, rewarding coins or items, or causing status updates.

### D. Item Crafting
*   Recipes and table-crafting (time craft) utilize materials and items from the user's inventory to construct new components.

### E. State System & FSM Fabric
*   Located in [`bot/modules/states_fabric/state_handlers.py`](../../../bot/modules/states_fabric/state_handlers.py) and routed in [`bot/handlers/states.py`](../../../bot/handlers/states.py).
*   **Structure**: Uses `GeneralStates` (`StatesGroup` subclass) to define generic states: ChooseDino, ChooseInt, ChooseString, ChooseConfirm, ChooseOption, ChoosePagesState, and ChooseCustom.
*   **Dynamic Callback Binding**: Handlers inherit from `BaseStateHandler` (e.g. `ChooseDinoHandler`, `ChooseConfirmHandler`). When setting up a state, they convert transition callbacks to string functions via [`functransport.py`](../../../bot/modules/functransport.py) (`func_to_str` and `str_to_func`). This serializes callbacks into the state data in MongoDB, allowing transitions to survive server reboots, file reloads, and long-term user inactivity.
*   **Routing**: The standard message handlers in [`bot/handlers/states.py`](../../../bot/handlers/states.py) catch state-filtered messages, retrieve the active FSM parameters, perform value/format validation, clear the FSM state, and invoke the dynamically mapped callback.

### F. Reply Keyboard Menus
*   Implemented in [`bot/modules/markup.py`](../../../bot/modules/markup.py).
*   **Navigation & Last State**: The bot persists the user's active keyboard screen key in MongoDB (`users` collection, `last_markup` field).
*   **Menu Constructor**: The `markups_menu(userid, markup_key, language_code, last_markup)` function creates ReplyKeyboardMarkup blocks dynamically.
*   **History & Back Navigation**: If `markup_key` is set to `'last_menu'`, the constructor resolves the previous menu screen by walking back the navigation pathways defined in `back_menu()`. Main buttons are translated on the fly using localization keys under the `commands_name.` prefix.

### G. Notification System
*   Located in [`bot/modules/notifications.py`](../../../bot/modules/notifications.py).
*   **Dinosaur Alerts (`dino_notification`)**: Alerts owners when stats run low (e.g. low food/health/energy warnings) or when mood states trigger (inspiration/breakdown).
    *   To prevent notification spam, active alerts are stored in the dinosaur document's `notifications` dictionary as timestamps. These are checked before sending a new alert, and are deleted (`$unset`) once stats recovery conditions are met.
*   **User Alerts (`user_notification`)**: Sends transactional alerts (donations, referral codes, egg hatching readiness, crafting success, level-ups). Level-up notifications generate custom Pillow-rendered certificates.
*   **Dynamic Dialogue (Replics)**: Critical notifications leverage the `replics_notifications` list. The system randomly selects one of several contextual translation lines ("replics") from localization configurations, adding personality to the dinosaur's alerts.

### H. Blacksmith & Runes Mechanics
*   **Blacksmith Menu (Кузнец)**: Located in [`bot/handlers/blacksmith.py`](../../../bot/handlers/blacksmith.py) and registered in [`bot/handlers/transition.py`](../../../bot/handlers/transition.py). Presents a main welcome menu using a standard ReplyKeyboardMarkup containing:
    1.  *Upgrade*: Prompts players to fuse two identical accessories (up to level 5) or weapons (up to level 10) of the same level to upgrade them.
    2.  *My Upgraded Items*: Displays all active level > 0 items in the user's inventory with their level-scaled stats.
    3.  *Information*: Lists pricing, default chances, and rune effects.
*   **Upgrades Pricing & Chances**: Upgrade fee is configured under `blacksmith_prices` and default chances under `blacksmith_chances` in [`bot/json/settings.json`](../../../bot/json/settings.json). Max durability `endurance_max` scales geometrically by 1.5x per level: `int(base_endurance * (1.5 ** lvl))`.
*   **Repair Recipes Clamping**: Increment actions in repair recipes (e.g. `repair_tool` in [`bot/modules/items/craft_recipe.py`](../../../bot/modules/items/craft_recipe.py)) clamp durability to the level-adjusted maximum durability `get_item_endurance_max` of the item being repaired instead of the base level 0 maximum.
*   **Runes (Руны)**: Introduced as the `'rune'` item type. Players can apply runes during blacksmith upgrades to modify outcomes:
    *   *Type 1 (Certainty)*: Guarantees 100% success up to level Y.
    *   *Type 2 (Luck)*: Increases success probability by +X%.
*   **Level-Aware Getters**: Item properties are scale-adjusted depending on their level (stored in the item's `abilities` under `'lvl'`) using level-aware helper functions in [`bot/modules/items/item.py`](../../../bot/modules/items/item.py). Getters on the `Item` model include `get_level()`, `get_damage()`, `get_endurance_max()`, `get_reflection()`, `get_capacity()`, `get_effectiv()`, and `get_ability()`.

---

## 5. Development Guidelines & Standards

1.  **Safe Database Queries (`DBconstructor`)**:
    *   Always query collections using instances of `DBconstructor` wrapping the motor collection.
    *   **CRITICAL**: You must provide a descriptive `comment` parameter on query method calls (such as `update_one` or `find_one`). This comment is printed in logs to track query performance:
        ```python
        await dinosaurs.update_one({"_id": dino_id}, {"$set": {"stats.eat": 100}}, comment="dino_feed_max")
        ```
2.  **Localization & Multi-Language Support**:
    *   Hardcoded user-facing strings are strictly forbidden.
    *   Render all text with the `t(key, locale, **kwargs)` function imported from [`bot/modules/localization.py`](../../../bot/modules/localization.py):
        ```python
        text = t("incubation.ready_message", lang, user_name=name)
        ```
3.  **Handler Logging & Decorators**:
    *   Decorate aiogram message handlers with `@HDMessage` and callback query handlers with `@HDCallback` to monitor routing times and log potential issues.
        ```python
        @HDMessage
        @main_router.message(Command("start"))
        async def handler(message: types.Message):
            ...
        ```
4.  **Registering Asynchronous Loop Tasks**:
    *   Do not spawn background loops directly via `asyncio.create_task()`.
    *   Register them with the central task manager using `add_task` in [`bot/taskmanager.py`](../../../bot/taskmanager.py):
        ```python
        from bot.taskmanager import add_task
        add_task(my_periodic_check, repeat_time=60.0, delay=5.0)
        ```
5.  **Dockerization & Static Assets**:
    *   Static asset folders such as `fonts/` and `images/` are not copied during the Docker build stage to keep the image lightweight. They are mounted as read-only volumes (`ro`) via `docker-compose.yml`.
    *   To ensure fast build times, temporary directories, virtual environments (`.venv/`), local database storage (`mongodb/`), backups, and logs are excluded using `.dockerignore`.
6.  **Configuration & Environment Variables**:
    *   Secrets like database credentials must not be hardcoded in `config.json` or `docker-compose.yml`.
    *   A `.env` file is used to define `MONGO_USERNAME` and `MONGO_PASSWORD`.
    *   In `config.json`, use placeholders like `mongodb://${MONGO_USERNAME}:${MONGO_PASSWORD}@mongo:27017`.
    *   `bot/config.py` automatically parses `.env` at startup and interpolates placeholders of the form `${VAR}` with corresponding environment variables.
7.  **Data Access Layer & Beanie ODM**:
    *   To keep database operations clean and safe, all queries, updates, and inserts in handlers and helper modules (excluding periodic/background tasks) must be performed using Beanie ODM models directly.
    *   Avoid using `LazyCollection` proxies in non-task code. Load documents using model classmethods (e.g., `User.find_one`, `Dino.find_one`).
    *   Document mutations must be encapsulated strictly within the model's own helper methods (such as `add_coins`, `remove_coins`, `add_super_coins`, `remove_super_coins`, `set_name`, `set_avatar`, `set_last_markup`, `set_profile_background`, `inc_quests_ended` on the `User` or `Dino` models) which handle the field modifications and call `self.save()` internally. Direct updates or field modifications followed by `doc.save()` outside the model classes are prohibited.

8.  **Database Migration, Backup & Recovery Utilities**:
    *   The single-database migration script `tools/migration_merge_dbs.py` handles merging all collections from separate databases (including `dungeon` database lobby data and `deleted_dungeon_lobby`) into the primary `dinogochi` database.
    *   For backups and restores, use the utilities `tools/backup_db.py` and `tools/restore_db.py`. They natively run `mongodump` and `mongorestore` under gzipped compression and drop existing collections for consistency.

---

## 6. Critical Rule for AI Agents

> [!IMPORTANT]
> **When modifying the codebase, adding new features, database collections, or changing existing gameplay systems, the AI agent is REQUIRED to automatically update this `SKILL.md` file.** This maintains documentation accuracy for future development tasks.


## 7. Guidelines for Creating New Item Classes

When adding a new type/class of item to the bot, you must update the following files and locations:

1.  **Item Type Definition**:
    *   Add the new type string to the `TYPES` literal in [`bot/dataclasess/items/base.py`](file:///c:/Папки/коды/Telegram DinoGochi/DinoGochi/bot/dataclasess/items/base.py).

2.  **Item Data Class**:
    *   Define the new item class in [`bot/dataclasess/items/nullitems.py`](file:///c:/Папки/коды/Telegram DinoGochi/DinoGochi/bot/dataclasess/items/nullitems.py) (or a separate file under `bot/dataclasess/items/`), inheriting from `BaseItem`. Declare any specific properties (e.g. `time_boost` for `IncubationBoost`).

3.  **Type Registry Mapping**:
    *   Import and register the new class mapping under `ITEM_CLASSES` inside [`bot/modules/items/collect_items.py`](file:///c:/Папки/коды/Telegram DinoGochi/DinoGochi/bot/modules/items/collect_items.py).

4.  **Item Info Formatting**:
    *   Add custom formatting logic for displaying the item's specific attributes inside the `item_info` function in [`bot/modules/items/item.py`](file:///c:/Папки/коды/Telegram DinoGochi/DinoGochi/bot/modules/items/item.py).

5.  **Localization Files**:
    *   Add translation entries under `item_info.type_info.<new_type_name>` in all localization JSON files (`ru.json`, `en.json`, `es.json`, `id.json`). This includes specifying `type_name` (display name of the item class) and `add_text` (template for displaying properties like durability, capacity, etc.).

## 8. Premium and Super Shop Configuration

*   Paid `/premium` products are configured in [`bot/json/settings.json`](../../../bot/json/settings.json) under `products`.
    *   Product text and media are localized under `support_command.products_bio` in every localization file.
    *   Category/subpage labels are localized under `support_command.pages`.
    *   The `/premium` page structure is defined by `SUPPORT_PAGES` in [`bot/handlers/profile_menu/support.py`](../../../bot/handlers/profile_menu/support.py).
    *   Premium shop subpages are paginated by `SUPPORT_ITEMS_PER_PAGE`; main category buttons are shown two per row.
    *   The profile "Support" button opens `support_command.choose`, a two-button choice between the super shop and donations; `/premium` opens the donation shop directly.
*   Super coin `/super` shop products are configured in [`bot/json/settings.json`](../../../bot/json/settings.json) under `super_shop`.
    *   Each entry must contain an `items` list and a `price` in super coins.
    *   All item ids referenced by `products` or `super_shop` must exist in one of the files under [`bot/json/items/`](../../../bot/json/items/).

## 9. Weapon & Armor Properties System

Weapons and armor items support combat properties with level scaling and priority sorting:
1.  **Properties Schema**: Defined in `bot/modules/items/combat_properties.py` using `CombatPropertyModel`. Supported types include `multi_strike`, `ignore_armor`, `aoe`, `apply_effect_enemy`, `apply_effect_self` (weapons) and `ignore_effects`, `self_repair`, `counter_attack` (armor).
2.  **Stat Dependency**: Trigger chances can scale dynamically with dinosaur stats (e.g. `dexterity`, `power`).
3.  **Level Scaling**: Auto-scaled using `lvl_scale` dynamic math (`base_value + level * multiplier`) or explicit level overrides in `lvls[lvl]['properties']` inside the items config.
4.  **UI & Customization**:
    *   Descriptions are displayed on a separate item properties page using `format_all_properties`, opened by the `🔮 Свойства` button.
    *   The `🔮 Эффекты уровней` button displays properties scaled for all levels.
    *   The `⚙ Приоритет навыков` button is displayed on the properties page and allows players to change activation priorities. Priorities are stored in the item's database document under `abilities.skills_priority`.
    *   Priority configuration can be reset (removing priority fields, making property activation order random).
