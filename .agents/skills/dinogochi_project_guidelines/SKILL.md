---
name: dinogochi_project_guidelines
description: Guidelines for architecture, models, configurations, and game mechanics of Telegram DinoGochi bot
---

# DinoGochi Project Guidelines

This document describes the architecture, structure, database models, and core game mechanics of the **DinoGochi** Telegram bot (a virtual Tamagotchi-dinosaur game with RPG elements).

## 1. Technology Stack & Architecture

*   **Language**: Python 3.10+
*   **Telegram API**: [aiogram v3](../../../requirements.txt) (asynchronous library for Telegram bots).
*   **Database**: [MongoDB](../../../bot/dbmanager.py) accessed asynchronously via the `motor` client.
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
│   ├── dbmanager.py                     # Database connection & setup
│   ├── exec.py                          # Bot execution setup and polling initiation
│   ├── taskmanager.py                   # Async loop scheduler
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

MongoDB databases and collections are dynamically prepared according to [`bot/json/settings.json`](../../../bot/json/settings.json).

### Core Python Model Classes

1.  **User Model (`User`)** — [`bot/modules/user/user.py`](../../../bot/modules/user/user.py)
    *   Tracks user ID, name, currency balances (`coins`, `super_coins`), experience/levels (`xp`, `lvl`), notification preferences, and active dinosaur reference (`settings.last_dino`).
2.  **Dinosaur Model (`Dino`)** — [`bot/modules/dinosaur/dinosaur.py`](../../../bot/modules/dinosaur/dinosaur.py)
    *   Manages key statistics:
        *   Core: health (`heal`), hunger (`eat`), play (`game`), mood (`mood`), energy (`energy`).
        *   RPG stats: strength (`power`), dexterity (`dexterity`), intelligence (`intelligence`), charisma (`charisma`).
    *   Maintains rarity (`quality`): com (common), uncommon, rare, legendary, mystical.
    *   Stores interaction memory (`memory` lists for game types and food kinds) to penalize redundant actions.
3.  **Egg Model (`Egg`)** — [`bot/modules/dinosaur/dinosaur.py`](../../../bot/modules/dinosaur/dinosaur.py)
    *   Tracks egg rarity, incubation finish timestamp, and a pool of dinosaur options presented to the user during the choosing stage.
4.  **Item Model (`BaseItem`)** — [`bot/dataclasess/items/base.py`](../../../bot/dataclasess/items/base.py)
    *   Defines item configurations loaded from JSON files: type (eat, material, case, weapon, etc.), rarity (`rank`), abilities (`abilities` dictionary), and merchant resell values.

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

---

## 6. Critical Rule for AI Agents

> [!IMPORTANT]
> **When modifying the codebase, adding new features, database collections, or changing existing gameplay systems, the AI agent is REQUIRED to automatically update this `SKILL.md` file.** This maintains documentation accuracy for future development tasks.

