from bson import ObjectId
from bot.models.dinosaur import Dino, DinoMood, DinoOwners
from bot.models.activity import Kindergarten
from bot.models.user import User
from time import time
from typing import Optional, Any

from bot.const import GAME_SETTINGS
from bot.exec import main_router, bot
from bot.modules.images_save import edit_SmartPhoto, send_SmartPhoto
from bot.models.items import Item
from bot.modules.data_format import (
    list_to_inline,
    list_to_keyboard,
    near_key_number,
    seconds_to_str,
)
from bot.models.dinosaur import Dino, Egg
from bot.models.other import Event
from bot.modules.images import async_open, create_skill_image, create_combat_image
from bot.modules.inline import dino_profile_markup, inline_menu
from bot.models.enums import DinoStatus, DinoOwnerType
from bot.modules.items.item import get_name
from bot.models.activity import Kindergarten
from bot.modules.localization import get_data, get_lang, t
from bot.modules.markup import confirm_markup
from bot.modules.markup import markups_menu as m
from bot.modules.states_fabric.state_handlers import (
    ChooseConfirmHandler,
    ChooseDinoHandler,
    ChooseOptionHandler,
)
from bot.modules.user.friends import get_friend_data

from aiogram import types
from aiogram.types import Message, CallbackQuery

from bot.filters.translated_text import Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F

from bot.modules.items.item import get_data as get_item_data


async def add_activity_info(dino: Any, lang: str, text: str, tem: dict[str, Any]) -> str:
    status = await dino.status
    status_key = status.value

    # Journey activity
    if status == DinoStatus.JOURNEY:
        text += "\n\n"
        from bot.models.activity import JourneyActivity

        journey_data = await JourneyActivity.find_one(
            JourneyActivity.dino.id == dino.id  # type: ignore
        )  # type: ignore

        if journey_data:
            st = journey_data.start_time or int(time())
            journey_time = seconds_to_str(int(time()) - st, lang)
            loc = journey_data.location
            loc_name = get_data(f"journey_start.locations.{loc}", lang)["name"]
            completed_events = [
                ev
                for ev in journey_data.pregenerated_events
                if ev.get("status") in ["completed", "waiting_choice"]
            ]
            col = len(completed_events)

            text += (
                t("p_profile.journey.text", lang, em_journey_act=tem["em_journey_act"])
                + "\n"
            )
            text += t(
                "p_profile.journey.info",
                lang,
                journey_time=journey_time,
                location=loc_name,
                col=col,
            )

    # Game activity
    elif status == DinoStatus.GAME:
        from bot.models.activity import GameActivity

        data = await GameActivity.find_one(GameActivity.dino.id == dino.id)
        text += t(f"p_profile.game.text", lang, em_game_act=tem["em_game_act"])
        if data:
            if await Item.check_accessory(dino, "timer", True):
                end = seconds_to_str(data.end_time - int(time()), lang)
                text += t(f"p_profile.game.game_end", lang, end=end)

            duration = seconds_to_str(int(time()) - data.start_time, lang)
            text += t(f"p_profile.game.game_duration", lang, duration=duration)

    # Collecting activity
    elif status == DinoStatus.COLLECTING:
        from bot.models.activity import CollectingActivity

        data = await CollectingActivity.find_one(CollectingActivity.dino.id == dino.id)
        if data:
            text += t(
                f"p_profile.collecting.text", lang, em_coll_act=tem["em_coll_act"]
            )
            now_count = 0
            current_time = int(time())
            if data.pregenerated_ticks:
                for tick in data.pregenerated_ticks:
                    if tick["trigger_time"] <= current_time:
                        now_count = tick["count"]
            else:
                now_count = data.now_count

            text += t(
                f"p_profile.collecting.progress.{data.collecting_type}",
                lang,
                now=now_count,
                max_count=data.max_count,
            )

    # Sleep activity
    elif status == DinoStatus.SLEEP:
        from bot.models.activity import SleepActivity

        data = await SleepActivity.find_one(SleepActivity.dino.id == dino.id)
        if data:
            text += t(
                f"p_profile.sleep.{data.sleep_type}",
                lang,
                em_sleep_act=tem["em_sleep_act"],
            )
            text += t(
                f"p_profile.sleep.sleep_duration",
                lang,
                duration=seconds_to_str(int(time()) - data.start_time, lang),
            )

    # Work activity
    elif status in [DinoStatus.BANK, DinoStatus.SAWMILL, DinoStatus.MINE]:
        from bot.models.activity import WorkActivity

        data = await WorkActivity.find_one(WorkActivity.dino.id == dino.id)
        text += t(
            f"p_profile.work.text",
            lang,
            em_work_act=tem[f"em_{status_key}_act"],
            work_type=t(f"p_profile.work.work_type.{status_key}", lang),
        )
        if data:
            duration = seconds_to_str(int(time()) - data.start_time, lang)
            text += t(f"p_profile.work.work_duration", lang, duration=duration)

    # Training activity
    elif status in [
        DinoStatus.SWIMMING_POOL,
        DinoStatus.GYM,
        DinoStatus.LIBRARY,
        DinoStatus.PARK,
    ]:
        from bot.models.activity import TrainingActivity

        data = await TrainingActivity.find_one(TrainingActivity.dino.id == dino.id)
        text += t(
            f"p_profile.training.text",
            lang,
            em_training_act=tem[f"em_{status_key}_act"],
            training_type=t(f"p_profile.training.training_type.{status_key}", lang),
        )

        if data:
            duration = seconds_to_str(int(time()) - data.start_time, lang)
            text += t(f"p_profile.training.training_duration", lang, duration=duration)

    return text


async def get_dino_profile_text(userid: int, dino: Dino, lang: str) -> str:
    status_key = await dino.status
    status_key = status_key.value

    text_rare = get_data("rare", lang)
    replics = get_data("p_profile.replics", lang)
    status_rep = t(f"p_profile.stats.{status_key}", lang)
    joint_dino = False

    owners = await DinoOwners.find(DinoOwners.dino.id == dino.id).to_list()  # type: ignore

    for conn in owners:
        if conn.owner_id == userid and conn.type == DinoOwnerType.ADD_OWNER:
            joint_dino = True

    season = await Event.get_event("time_year")
    if "data" in season:
        season = season["data"]["season"]
    else:
        season = "standart"
    tem = GAME_SETTINGS["events"]["time_year"][season]

    stats_text = ""
    # Генерация блока со статистикой
    for i in ["heal", "eat", "game", "mood", "energy"]:
        repl = near_key_number(dino.stats[i], replics[i])
        stats_text += f"{tem[i]} {repl} [ *{dino.stats[i]}%* ]\n"

    age = await dino.age()
    if age.days == 0:
        age = seconds_to_str(age.seconds, lang)
    else:
        age = seconds_to_str(age.days * 86400, lang)

    from bot.modules.data_format import escape_markdown

    dino_name = escape_markdown(dino.name)
    if joint_dino:
        dino_name += t("p_profile.joint", lang)

    unique = await Dino.get_uniqueness_factor(dino.data_id)

    kwargs = {
        "em_name": tem["name"],
        "dino_name": dino_name,
        "em_status": tem["status"],
        "status": status_rep,
        "em_rare": tem["rare"],
        "qual": text_rare[dino.quality][1],
        "em_age": tem["age"],
        "age": age,
        "em_uniqueness": tem["uniqueness"],
        "uniqueness": unique,
    }

    # Первое апреля
    if await Event.check_event("april_1"):
        for k, v in kwargs.items():
            if k.startswith("em_"):
                kwargs[k] = "🤡"

    text = t("p_profile.profile_text", lang, formating=False).format(**kwargs)

    text = await add_activity_info(dino, lang, text, tem)
    text += "\n\n" + stats_text + "\n"

    # Генерация блока с аксессуарами
    acsess = {
        "game": tem["ac_game"],
        "collecting": tem["ac_collecting"],
        "journey": tem["ac_journey"],
        "sleep": tem["ac_sleep"],
        "weapon": tem["ac_weapon"],
        "armor": tem["ac_armor"],
        "backpack": tem["ac_backpack"],
    }

    assert dino.id is not None
    acc_items = await Item.find_accessory(dino.id)

    for key, acc in enumerate(acc_items):
        item_data = acc.items_data
        item_type = acc.data.get("type", "")

        name = get_name(acc.item_id, lang, item_data.get("abilities", {}))
        if "abilities" in item_data and "endurance" in item_data.get("abilities", {}):
            name = f"{name} [ *{item_data['abilities']['endurance']}* ]"

        separat = "-"
        if len(acc_items) > 1:
            if key == 0:
                separat = "┌"
            elif key == len(acc_items) - 1:
                separat = "└"
            else:
                separat = "├"

        text += (
            t(
                f"p_profile.accs.{item_type}",
                lang,
                separator=separat,
                item=name,
                emoji=acsess.get(item_type, "📦"),
            )
            + "\n"
        )

    return text


async def dino_profile(
    userid: int,
    chatid: int,
    dino: Dino,
    lang: str,
    custom_url: Optional[str],
    message_to_edit: Optional[Message] = None,
    without_buttons: bool = False,
    reply_to_message_id: Optional[int] = None,
) -> None:
    assert dino.id is not None
    text = await get_dino_profile_text(userid, dino, lang)

    joint_dino, my_joint = False, False
    user = await User().create(userid)
    owners = await DinoOwners.find(DinoOwners.dino.id == dino.id).to_list()  # type: ignore

    for conn in owners:
        if conn.owner_id == userid and conn.type == DinoOwnerType.ADD_OWNER:
            joint_dino = True
        if (
            conn.owner_id == userid
            and conn.type == DinoOwnerType.OWNER
            and len(owners) >= 2
        ):
            my_joint = True

    assert dino.id is not None
    acc_items = await Item.find_accessory(dino.id)

    if without_buttons:
        menu = None
    else:
        menu = dino_profile_markup(
            bool(acc_items), lang, dino.alt_id, joint_dino, my_joint
        )

    # затычка на случай если не сгенерируется изображение
    generate_image = "images/remain/no_generate.png"
    if message_to_edit is None:
        msg = await send_SmartPhoto(
            chatid,
            generate_image,
            text,
            "Markdown",
            reply_markup=menu,
            reply_to_message_id=reply_to_message_id,
        )
    else:
        msg = await edit_SmartPhoto(
            chatid,
            message_to_edit.message_id,
            generate_image,
            text,
            "Markdown",
            reply_markup=menu,
        )

    if message_to_edit is None and not without_buttons:
        await bot.send_message(
            chatid,
            t("p_profile.return", lang),
            reply_markup=await m(userid, "last_menu", lang),
        )

    # изменение сообщения с уже нужным изображением
    image = await dino.image(user.settings["profile_view"], custom_url or "")
    if isinstance(msg, Message):
        await bot.edit_message_media(
            chat_id=chatid,
            message_id=msg.message_id,
            media=types.InputMediaPhoto(media=image, parse_mode="Markdown", caption=text),
            reply_markup=menu,
        )


async def egg_profile(chatid: int, egg: Egg, lang: str) -> None:
    text = t(
        "p_profile.incubation_text",
        lang,
        time_end=seconds_to_str(egg.remaining_incubation_time(), lang),
    )
    img = await egg.image(lang)

    markup = None
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    if getattr(egg, "free_boost", False):
        builder = InlineKeyboardBuilder()
        builder.button(
            text=t(
                "p_profile.free_boost_button", lang, default="⚡ Ускорить вылупление"
            ),
            callback_data=f"free_egg_boost {egg.id}",
        )
        markup = builder.as_markup()
    else:
        builder = InlineKeyboardBuilder()
        builder.button(
            text=t("p_profile.boost_button", lang, default="⚡ Ускорить инкубацию"),
            callback_data=f"egg_boost_menu {egg.id}",
        )
        markup = builder.as_markup()

    await bot.send_photo(chatid, img, caption=text, reply_markup=markup)

    userid = egg.owner_id
    await bot.send_message(
        chatid,
        t("p_profile.return", lang),
        reply_markup=await m(userid, "last_menu", lang),
    )


@main_router.callback_query(IsPrivateChat(), F.data.startswith("free_egg_boost"))
async def free_egg_boost_callback(call: types.CallbackQuery) -> None:
    if not call.data or not call.message or not call.from_user: return
    egg_id_str = call.data.split()[1]
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)

    from bson import ObjectId

    egg = await Egg.find_one(Egg.id == ObjectId(egg_id_str))  # type: ignore

    if not egg or not getattr(egg, "free_boost", False):
        await call.answer(
            t(
                "p_profile.boost_error",
                lang,
                default="❌ Ошибка: Ускорение недоступно!",
            ),
            show_alert=True,
        )
        return

    from bot.models.dinosaur import Dino
    from bot.modules.managment.tracking import update_all_user_track
    from bot.modules.notifications import user_notification

    # создаём динозавра
    res, alt_id = await Dino.insert_dino(egg.owner_id, egg.dino_id, egg.quality)

    # удаляем динозавра из инкубаций
    await Egg.find_one(Egg.id == egg.id).delete()  # type: ignore

    # отправляем уведомление
    user = await User().create(egg.owner_id)
    await user_notification(
        egg.owner_id,
        "incubation_ready",
        lang,
        user_name=user.name,
        dino_alt_id_markup=alt_id,
    )

    assert user.userid is not None
    await update_all_user_track(user.userid, "gaming")

    try:
        await bot.delete_message(chatid, call.message.message_id)
    except:
        pass

    await call.answer(
        t("p_profile.boost_success", lang, default="⚡ Вылупление успешно ускорено!"),
        show_alert=True,
    )


async def transition(oid: ObjectId, transmitted_data: dict[str, Any]) -> None:
    userid = transmitted_data["userid"]
    chatid = transmitted_data["chatid"]
    lang = transmitted_data["lang"]
    custom_url = ""
    egg_find = None

    cl_name = "Dino"
    dino_find = await Dino().create(oid)
    if not dino_find:
        egg_find = await Egg().create(oid)
        if egg_find:
            cl_name = "Egg"

    if cl_name == "Dino":
        element = await Dino().create(oid)
        if element:
            user = await User.find_one(User.userid == userid)
            is_premium = await user.premium if user else False
            if element.profile["background_type"] == "custom" and is_premium:
                custom_url = element.profile["background_id"]

            if element.profile["background_type"] == "saved":
                idm = element.profile["background_id"]
                custom_url = await async_open(f"images/backgrounds/{idm}.png")

    if cl_name == "Dino":
        element = await Dino().create(oid)
        if element:
            await dino_profile(userid, chatid, element, lang, custom_url)

    elif cl_name == "Egg" and egg_find:
        element = await Egg().create(oid)
        await egg_profile(chatid, egg_find, lang)


@main_router.message(
    Text("commands_name.dino_profile"), IsAuthorizedUser(), IsPrivateChat()
)
async def dino_handler(message: Message) -> None:
    if not message.from_user: return
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)

    bstatus, status = await ChooseDinoHandler(
        transition, userid, message.chat.id, lang, send_error=False
    ).start()

    if not bstatus and status == "cancel":
        user = await User.find_one(User.userid == userid)
        dead_count = 0
        if user:
            dead_dinos = await user.get_dead_dinos()
            dead_count = len(dead_dinos)

        if await Dino.dead_check(userid):
            await bot.send_message(
                userid,
                t(f"p_profile.dialog", lang, dead_dinos_count=dead_count),
                reply_markup=inline_menu("dead_dialog", lang),
            )
        else:
            await bot.send_message(userid, t(f"p_profile.no_dino_no_egg", lang, dead_dinos_count=dead_count))


@main_router.callback_query(IsPrivateChat(), F.data.startswith("dino_profile"))
async def dino_profile_callback(call: types.CallbackQuery) -> None:
    if not call.data or not call.message or not call.from_user: return
    dino_data = call.data.split()[1]
    # await bot.delete_state(call.from_user.id, call.message.chat.id)

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    trans_data = {"userid": userid, "chatid": chatid, "lang": lang}
    dino = await Dino().create(dino_data)
    if dino:
        await transition(dino._id, trans_data)


@main_router.callback_query(IsPrivateChat(), F.data.startswith("dino_menu"))
async def dino_menu(call: types.CallbackQuery) -> None:
    if not call.data or not call.message or not call.from_user or not isinstance(call.message, Message): return
    split_d = call.data.split()
    action = split_d[1]
    alt_key = split_d[2]

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    user = await User.find_one(User.userid == userid)
    dino = await Dino.find_one(Dino.alt_id == alt_key)
    if dino and user:
        res = await DinoOwners.find_one(
            DinoOwners.dino.id == dino.id, DinoOwners.owner_id == userid
        )
        if not res:
            await bot.send_message(
                userid,
                t("css.no_dino", lang),
                reply_markup=await m(userid, "last_menu", lang),
            )
            return

        if action == "reset_activ_item":
            assert dino.id is not None

            acc_items = await Item.find_accessory(dino.id)
            activ_items = {}
            for acc in acc_items:
                display = get_name(
                    acc.item_id, lang, acc.items_data.get("abilities", {})
                )
                activ_items[display] = acc.item_id

            is_auto = len(activ_items) == 1

            result = await ChooseOptionHandler(
                remove_accessory,
                userid,
                chatid,
                lang,
                activ_items,
                {
                    "dino_id": dino.id,
                    "message_to_edit": call.message,
                    "is_auto": is_auto,
                },
            ).start()

            if result[0]:
                reply_buttons = [
                    list(activ_items.keys()),
                    [t(f"buttons_name.cancel", lang)],
                ]

                reply = list_to_keyboard(reply_buttons, 2)
                text = t("remove_accessory.choose_item", lang)
                await bot.send_message(userid, text, reply_markup=reply)
            else:
                await call.answer(t("remove_accessory.remove", lang), show_alert=True)

        elif action == "mood_log":
            mood_list = await DinoMood.find(DinoMood.dino.id == dino.id).to_list()  # type: ignore
            mood_dict: dict[str, Any] = {}
            text, event_text = "", ""
            res, event_end = 0, 0

            for mood in mood_list:
                if mood.type not in ["breakdown", "inspiration"]:
                    key = mood.action
                    if key not in mood_dict:
                        mood_dict[key] = {"col": 1, "unit": mood.unit}
                    else:
                        mood_dict[key]["col"] += 1
                    res += mood.unit or 0

                else:
                    event_text = t(f"mood_log.{mood.type.value}.{mood.action}", lang)
                    event_end = mood.end_time - mood.start_time

            # Calculate active while mood modifiers on the fly
            while_modifiers = []
            
            # Game
            if dino.stats.get('game', 0) <= 35:
                while_modifiers.append(('little_game', -1))
            elif dino.stats.get('game', 0) >= 45:
                while_modifiers.append(('multi_games', 1))
                
            # Eat
            if dino.stats.get('eat', 0) < 5:
                while_modifiers.append(('little_eat', -2))
            elif dino.stats.get('eat', 0) <= 50:
                while_modifiers.append(('little_eat', -1))
            elif dino.stats.get('eat', 0) >= 60:
                while_modifiers.append(('multi_eat', 1))
                
            # Energy
            if dino.stats.get('energy', 0) <= 40:
                while_modifiers.append(('little_energy', -1))
            elif dino.stats.get('energy', 0) >= 60:
                while_modifiers.append(('multi_energy', 1))
                
            # Heal
            if dino.stats.get('heal', 0) <= 40:
                while_modifiers.append(('little_heal', -1))
            elif dino.stats.get('heal', 0) >= 60:
                while_modifiers.append(('multi_heal', 1))

            for key, unit in while_modifiers:
                if key not in mood_dict:
                    mood_dict[key] = {"col": 1, "unit": unit}
                else:
                    mood_dict[key]["col"] += 1
                res += unit

            text = t("mood_log.info", lang, result=res)
            if event_text:
                event_time = seconds_to_str(event_end, lang, True)
                text += t(
                    "mood_log.event_info",
                    lang,
                    action=event_text,
                    event_time=event_time,
                )

            text += "\n"

            for key, data_m in mood_dict.items():
                em = "💚"
                if data_m["unit"] <= 0:
                    em = "💔"
                act = t(f"mood_log.{key}", lang)

                unit = str(data_m["unit"] * data_m["col"])
                if data_m["unit"] > 0:
                    unit = "+" + unit

                text += f"{em} {act}: `{unit}` "
                if data_m["col"] > 1:
                    text += f"x{data_m['col']}"
                text += "\n"

            await bot.send_message(userid, text, parse_mode="Markdown")

        elif action == "joint_cancel":
            # Октазать от совместного динозавра
            text = t("cancle_joint.confirm", lang)
            await bot.send_message(
                userid, text, parse_mode="Markdown", reply_markup=confirm_markup(lang)
            )

            await ChooseConfirmHandler(
                cnacel_joint,
                userid,
                chatid,
                lang,
                transmitted_data={"dinoid": dino.id},
            ).start()

        elif action == "my_joint_cancel":
            # Октазать от совместного динозавра
            text = t("my_joint.confirm", lang)
            await bot.send_message(
                userid, text, parse_mode="Markdown", reply_markup=confirm_markup(lang)
            )

            await ChooseConfirmHandler(
                cnacel_myjoint,
                userid,
                chatid,
                lang,
                transmitted_data={"dinoid": dino.id, "user": call.from_user.id},
            ).start()

        elif action == "kindergarten":
            user = await User.find_one(User.userid == userid)
            is_premium = await user.premium if user else False
            if not is_premium:
                text = t("no_premium", lang)
                reply_buttons = None
                if (
                    await Dino.check_status_by_id(dino.id)
                    == DinoStatus.KINDERGARTEN
                ):
                    reply_buttons = list_to_inline(
                        [
                            {
                                t(
                                    "kindergarten.cancel_name", lang
                                ): f"kindergarten stop {alt_key}"
                            }
                        ]
                    )
                await bot.send_message(userid, text, reply_markup=reply_buttons)
            else:
                total, end = await Kindergarten.check_hours(userid)
                hours = await Kindergarten.hours_now(userid)
                text = t(
                    "kindergarten.info",
                    lang,
                    hours_now=240 - (total or 0),
                    remained=total,
                    days=seconds_to_str(end - int(time()), lang, False, "hour"),
                    hours=hours,
                    remained_today=12,
                )

                if (
                    await Dino.check_status_by_id(dino.id)
                    == DinoStatus.KINDERGARTEN
                ):
                    reply_buttons = list_to_inline(
                        [
                            {
                                t(
                                    "kindergarten.cancel_name", lang
                                ): f"kindergarten stop {alt_key}"
                            }
                        ]
                    )
                else:
                    reply_buttons = list_to_inline(
                        [
                            {
                                t(
                                    "kindergarten.button_name", lang
                                ): f"kindergarten start {alt_key}"
                            }
                        ]
                    )
                await bot.send_message(
                    userid, text, parse_mode="Markdown", reply_markup=reply_buttons
                )

        elif action == "backgrounds_menu":
            await bot.send_message(
                chatid,
                t("menu_text.backgrounds_menu", lang),
                reply_markup=await m(userid, "backgrounds_menu", lang),
            )

        elif action == "skills":
            await skills_profile(dino, lang, call.message)

        elif action == "combat":
            await combat_profile(dino, lang, call.message, userid)

        elif action == "battle_history":
            await battle_history_profile(dino, lang, call.message, userid)

        elif action == "heal_dino":
            
            from bot.modules.items.item import get_data as get_item_data
            from bot.modules.states_fabric.state_handlers import ChooseInventoryHandler
            from aiogram.types import FSInputFile

            inventory_items, _ = await User.get_inventory(userid)

            healing_items = []
            for item in inventory_items:
                item_id = item["items_data"].get("item_id")
                static_data = get_item_data(item_id)
                if (
                    static_data
                    and "buffs" in static_data
                    and "heal" in static_data["buffs"]
                ):
                    healing_items.append(item)

            if healing_items:
                await ChooseInventoryHandler(
                    None, userid, chatid, lang, inventory=healing_items
                ).start()
            else:
                text = t("combat_profile.no_heal_items", lang)
                markup = list_to_inline(
                    [
                        {
                            t(
                                "buttons_name.donate_shop",
                                lang,
                                default="⭐ Донат-магазин",
                            ): "support main 0",
                            t(
                                "buttons_name.back_combat",
                                lang,
                                default="🔙 К боевым параметрам",
                            ): f"dino_menu combat {alt_key}",
                        }
                    ],
                    2,
                )
                await call.message.edit_caption(
                    caption=text, reply_markup=markup, parse_mode="Markdown"
                )

        elif action == "main_message":
            dino = await Dino().create(alt_key)
            custom_url = ""
            if dino:
                user = await User.find_one(User.userid == userid)
                is_premium = await user.premium if user else False
                if dino.profile["background_type"] == "custom" and is_premium:
                    custom_url = dino.profile["background_id"]

                if dino.profile["background_type"] == "saved":
                    idm = dino.profile["background_id"]
                    custom_url = await async_open(f"images/backgrounds/{idm}.png")

                await dino_profile(userid, chatid, dino, lang, custom_url, call.message)


async def skills_profile(dino_data: Dino, lang: str, message: Message) -> None:
    dino = await Dino().create(dino_data.id)
    if not dino:
        await bot.send_message(message.chat.id, t("skills_profile.error", lang))
        return

    age = await dino.age()
    image = await create_skill_image(dino.data_id, age.days, lang, dino.stats)
    data_skills = {}

    for i in ["power", "dexterity", "intelligence", "charisma"]:
        data_skills[i] = near_key_number(
            dino.stats[i], get_data(f"skills_profile.{i}", lang)
        )
        data_skills[i + "_u"] = round(dino.stats[i], 4)

    text = t("skills_profile.info", lang, **data_skills)

    markup = list_to_inline(
        [
            {
                t(
                    "p_profile.inline_menu.profile_back", lang
                ): f"dino_menu main_message {dino.alt_id}",
                t(
                    "p_profile.inline_menu.combat.text", lang
                ): f"dino_menu combat {dino.alt_id}",
            }
        ],
        2,
    )

    await message.edit_media(
        types.InputMediaPhoto(media=image, parse_mode="Markdown", caption=text),
        reply_markup=markup,
    )


async def battle_history_profile(
    dino_data: Dino, lang: str, message: Message, userid: int = 0
) -> None:
    from bot.redismanager import get_redis
    from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
    import json

    r = get_redis()

    dino_id = dino_data.id
    dino_alt = dino_data.alt_id
    dino_name = dino_data.name

    dino_battles_key = f"dino_battles:{dino_id}"
    history_bytes = await r.lrange(dino_battles_key, 0, -1)  # type: ignore

    history = []
    for h_b in history_bytes:
        try:
            history.append(json.loads(h_b))
        except Exception:
            pass

    async def _edit(txt: str, markup: Optional[Any]) -> None:
        """Safely edit message regardless of type (text or photo)."""
        try:
            await message.edit_text(txt, reply_markup=markup, parse_mode="html")
        except Exception as e:
            try:
                await message.edit_caption(
                    caption=txt, reply_markup=markup, parse_mode="html"
                )
            except Exception as ex:
                import logging

                logging.exception(
                    f"battle_history_profile _edit failed. edit_text err: {e}, edit_caption err: {ex}"
                )

    if not history:
        text = t(
            "combat_log.ui.no_history",
            lang,
            dino_name=dino_name,
            default=f"⚔️ <b>История боев {dino_name}</b>\n\nЗаписей боев не зафиксировано.",
        )
        markup = list_to_inline(
            [
                {
                    t(
                        "buttons_name.back_combat",
                        lang,
                        default="🔙 К боевым параметрам",
                    ): f"dino_menu combat {dino_alt}"
                }
            ],
            1,
        )
        await _edit(text, markup)
        return

    text = t(
        "combat_log.ui.history_title",
        lang,
        dino_name=dino_name,
        default=f"⚔️ <b>История боев {dino_name}</b>:\n\nВыберите бой для просмотра лога:",
    )
    buttons = []
    for item in history:
        loc_data = get_data(f"journey_start.locations.{item['location']}", lang)
        loc_name = (
            loc_data.get("name", item["location"])
            if isinstance(loc_data, dict)
            else item["location"]
        )

        if item["winner"] == "X":
            winner_emoji = t("combat_log.ui.win", lang, default="🟢 Победа")
        elif item["winner"] == "Y":
            winner_emoji = t("combat_log.ui.defeat", lang, default="🔴 Поражение")
        else:
            winner_emoji = t("combat_log.ui.draw", lang, default="🟡 Ничья")

        mobs = item["mobs"]
        mobs_str = ", ".join(mobs) if isinstance(mobs, list) else str(mobs)
        btn_text = t(
            "combat_log.ui.battle_btn",
            lang,
            winner_emoji=winner_emoji,
            loc_name=loc_name,
            mobs_str=mobs_str,
            default=f"{winner_emoji} в {loc_name} ({mobs_str})",
        )

        battle_uuid = item["battle_id"].replace("combat_log:", "")
        buttons.append(
            [
                InlineKeyboardButton(
                    text=btn_text, callback_data=f"clv {battle_uuid} 0 {dino_id}"
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                text=t(
                    "combat_log.buttons.clear_history",
                    lang,
                    default="🗑️ Очистить всю историю",
                ),
                callback_data=f"dino_battles_clear {dino_id}",
            )
        ]
    )
    buttons.append(
        [
            InlineKeyboardButton(
                text=t(
                    "buttons_name.back_combat", lang, default="🔙 К боевым параметрам"
                ),
                callback_data=f"dino_menu combat {dino_alt}",
            )
        ]
    )

    await _edit(text, InlineKeyboardMarkup(inline_keyboard=buttons))


@main_router.callback_query(IsPrivateChat(), F.data.startswith("dino_battles_clear"))
async def clear_dino_battles(call: CallbackQuery):
    from bot.redismanager import get_redis, redis_del
    from bot.models.dinosaur import Dino
    from bson import ObjectId
    import json

    dino_id = call.data.split()[1]
    userid = call.from_user.id
    lang = await get_lang(userid)

    r = get_redis()
    dino_battles_key = f"dino_battles:{dino_id}"

    # Load and delete individual combat logs
    history_bytes = await r.lrange(dino_battles_key, 0, -1)  # type: ignore
    for h_b in history_bytes:
        try:
            item = json.loads(h_b)
            await redis_del(item["battle_id"])
        except Exception:
            pass

    # Delete the list key
    await r.delete(dino_battles_key)

    await call.answer(
        t("combat_log.cleared_success", lang, default="Вся история боев удалена."),
        show_alert=True,
    )

    dino_obj = await Dino.find_one(Dino.id == ObjectId(dino_id))  # type: ignore
    if dino_obj:
        await battle_history_profile(
            dino_obj, lang, call.message, userid)


async def combat_profile(dino_data: Dino, lang: str, message: Message, userid: int = 0) -> None:
    dino = await Dino().create(dino_data.id)
    if not dino:
        await bot.send_message(message.chat.id, t("skills_profile.error", lang))
        return

    if not userid:
        userid = message.chat.id

    combat_data = await dino.get_combat_capabilities()

    default_text = (
        "⚔️ *Боевые возможности {dino_name}*:\n\n"
        "❤️ *Здоровье*: `{hp}/100`\n\n"
        "💪 *Характеристики*:\n"
        " ├ Сила: `{power}`\n"
        " └ Ловкость: `{dexterity}`\n\n"
        "📊 *Боевые показатели*:\n"
        " ├ Бонус к урону от силы: `+{strength_damage_buff}`\n"
        " ├ Шанс уклонения: `{evasion_chance}%`\n"
        " ├ Урон от оружия: `{weapon_min} - {weapon_max}`\n"
        " ├ Итоговый урон: `{total_min} - {total_max}`\n"
        " └ Блокирование урона: `{total_block}`\n\n"
        "🎒 *Снаряжение*:\n"
    )

    weapons_text = ""
    if combat_data["active_weapons"]:
        for w in combat_data["active_weapons"]:
            w_name = get_name(w["name"], lang)
            weapons_text += f" ├ ⚔️ {w_name} ({t('combat_profile.damage', lang, default='Урон')}: {w['min']}-{w['max']})\n"
    else:
        weapons_text += (
            f" ├ ⚔️ {t('combat_profile.no_weapon', lang, default='Нет оружия')}\n"
        )

    armors_text = ""
    if combat_data["active_armors"]:
        for a in combat_data["active_armors"]:
            a_name = get_name(a["name"], lang)
            armors_text += f" └ 🛡️ {a_name} ({t('combat_profile.block', lang, default='Блок')}: {a['block']})\n"
    else:
        armors_text += (
            f" └ 🛡️ {t('combat_profile.no_armor', lang, default='Нет брони')}\n"
        )

    text = t(
        "combat_profile.info",
        lang,
        dino_name=dino.name,
        hp=dino.stats.get("heal", 100),
        power=combat_data["power"],
        dexterity=combat_data["dexterity"],
        strength_damage_buff=combat_data["strength_damage_buff"],
        evasion_chance=combat_data["evasion_chance"],
        weapon_min=combat_data["weapon_min"],
        weapon_max=combat_data["weapon_max"],
        total_min=combat_data["total_min"],
        total_max=combat_data["total_max"],
        total_block=combat_data["total_block"],
        default=default_text,
    )

    text += weapons_text + armors_text

    markup = list_to_inline(
        [
            {
                t(
                    "p_profile.inline_menu.combat_heal",
                    lang,
                    default="❤️ Восстановить здоровье",
                ): f"dino_menu heal_dino {dino.alt_id}",
                t(
                    "combat_profile.buttons.history", lang, default="⚔️ История боев"
                ): f"dino_menu battle_history {dino.alt_id}",
            },
            {
                t(
                    "p_profile.inline_menu.profile_back", lang
                ): f"dino_menu main_message {dino.alt_id}",
                t(
                    "p_profile.inline_menu.skills_btn", lang
                ): f"dino_menu skills {dino.alt_id}",
            },
        ],
        2,
    )

    custom_url = ""
    user = await User.find_one(User.userid == userid)
    is_premium = await user.premium if user else False
    if dino.profile["background_type"] == "custom" and is_premium:
        custom_url = dino.profile["background_id"]
    elif dino.profile["background_type"] == "saved":
        idm = dino.profile["background_id"]
        from bot.modules.images import async_open

        custom_url = await async_open(f"images/backgrounds/{idm}.png")

    image = await create_combat_image(dino.data_id, dino.stats, custom_url)

    await message.edit_media(
        types.InputMediaPhoto(media=image, parse_mode="Markdown", caption=text),
        reply_markup=markup,
    )


async def cnacel_joint(confirm: bool, transmitted_data: dict[str, Any]) -> None:
    userid = transmitted_data["userid"]
    lang = transmitted_data["lang"]
    if not confirm:
        await bot.send_message(
            userid, "❌", reply_markup=await m(userid, "last_menu", lang)
        )
        return

    dinoid = transmitted_data["dinoid"]

    user = await User.find_one(User.userid == userid)
    await DinoOwners.find(
        DinoOwners.dino.id == ObjectId(dinoid), DinoOwners.owner_id == userid
    ).delete()
    await bot.send_message(
        userid, "✅", reply_markup=await m(userid, "last_menu", lang)
    )
    if user:
        await user.update_last_dino(None)  # type: ignore


async def cnacel_myjoint(confirm: bool, transmitted_data: dict[str, Any]) -> None:
    userid = transmitted_data["user"]
    lang = transmitted_data["lang"]
    if not confirm:
        await bot.send_message(
            userid, "❌", reply_markup=await m(userid, "last_menu", lang)
        )
        return

    dinoid = transmitted_data["dinoid"]

    res = await DinoOwners.find_one(
        DinoOwners.dino.id == ObjectId(dinoid), DinoOwners.type == DinoOwnerType.ADD_OWNER
    )
    if res:
        owner_user = await User.find_one(User.userid == res.owner_id)
        if owner_user:
            assert owner_user.userid is not None
            await res.delete()
            myname_for_friend = await get_friend_data(owner_user.userid, userid)
            if "name" in myname_for_friend:
                myname_for_friend_str = myname_for_friend["name"]
            else:
                main_user = await User.find_one(User.userid == userid)
                myname_for_friend_str = main_user.name if main_user else "Владелец"

            text = t("my_joint.m_for_add_owner", lang, username=myname_for_friend_str)
            await bot.send_message(
                owner_user.userid, text, reply_markup=await m(userid, "last_menu", lang)
            )

            await owner_user.update_last_dino(None)  # type: ignore

    await bot.send_message(
        userid, "✅", reply_markup=await m(userid, "last_menu", lang)
    )


async def remove_accessory(item_id: str, transmitted_data: dict[str, Any]) -> None:
    userid = transmitted_data["userid"]
    lang = transmitted_data["lang"]
    dino_id = transmitted_data["dino_id"]
    message_to_edit = transmitted_data.get("message_to_edit")
    is_auto = transmitted_data.get("is_auto", False)

    await Item.remove_accessory(userid, dino_id, item_id)

    if is_auto and message_to_edit:
        dino = await Dino().create(dino_id)
        if dino:
            custom_url = ""
            user = await User.find_one(User.userid == userid)
            is_premium = await user.premium if user else False
            if dino.profile["background_type"] == "custom" and is_premium:
                custom_url = dino.profile["background_id"]
            elif dino.profile["background_type"] == "saved":
                idm = dino.profile["background_id"]
                from bot.modules.images import async_open

                custom_url = await async_open(f"images/backgrounds/{idm}.png")

            await dino_profile(
                userid,
                transmitted_data["chatid"],
                dino,
                lang,
                custom_url,
                message_to_edit=message_to_edit,
            )
    else:
        await bot.send_message(
            userid,
            t("remove_accessory.remove", lang),
            reply_markup=await m(userid, "last_menu", lang),
        )
        await transition(dino_id, transmitted_data)


@main_router.callback_query(IsPrivateChat(), F.data.startswith("kindergarten"))
async def kindergarten(call: types.CallbackQuery):
    split_d = call.data.split()
    action = split_d[1]
    alt_key = split_d[2]

    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(call.from_user.id)

    dino = await Dino.find_one(Dino.alt_id == alt_key)
    if dino:
        assert dino.id is not None
        if action == "start":
            if await Dino.check_status_by_id(dino.id) == DinoStatus.PASS:
                all_h, end = await Kindergarten.check_hours(userid)
                h = await Kindergarten.hours_now(userid)

                max_choice = min(12 - h, all_h or 0)
                if max_choice > 0:
                    options = {}

                    if max_choice >= 1:
                        options[f"1 {t('time_format.hour.0', lang)}"] = 1
                    if max_choice >= 3:
                        options[f"3 {t('time_format.hour.1', lang)}"] = 3
                    if max_choice >= 6:
                        options[f"6 {t('time_format.hour.2', lang)}"] = 6

                    bb = list_to_keyboard(
                        [list(options.keys()), [t("buttons_name.cancel", lang)]], 2
                    )

                    await ChooseOptionHandler(
                        start_kind,
                        userid,
                        chatid,
                        lang,
                        options,
                        transmitted_data={"dino": dino.id},
                    ).start()
                    await bot.send_message(
                        userid, t("kindergarten.choose_house", lang), reply_markup=bb
                    )
                else:
                    await bot.send_message(userid, t("kindergarten.no_hours", lang))
            else:
                await bot.send_message(userid, t("alredy_busy", lang))

        elif action == "stop":
            if await Dino.check_status_by_id(dino.id) == DinoStatus.KINDERGARTEN:
                await Kindergarten.remove_dino(dino.id)  # type: ignore
                await bot.send_message(userid, t("kindergarten.stop", lang))


async def start_kind(col: int, transmitted_data: dict[str, Any]) -> None:
    chatid = transmitted_data["chatid"]
    userid = transmitted_data["userid"]
    lang = transmitted_data["lang"]
    # dino = transmitted_data['dino']
    dino_id = transmitted_data["dino"]
    dino = await Dino().create(dino_id)

    if dino is None:
        await bot.send_message(
            chatid,
            t("kindergarten.error", lang),
            reply_markup=await m(userid, "last_menu", lang),
        )
        return

    await Kindergarten.minus_hours(userid, col)
    await Kindergarten.dino_kind(dino_id, col)
    await bot.send_message(
        chatid,
        t("kindergarten.ok", lang),
        reply_markup=await m(userid, "last_menu", lang),
    )


@main_router.callback_query(IsPrivateChat(), F.data.startswith("egg_boost_menu"))
async def egg_boost_menu_callback(call: types.CallbackQuery) -> None:
    if not call.data or not call.message or not call.from_user or not isinstance(call.message, Message): return
    egg_id_str = call.data.split()[1]
    userid = call.from_user.id
    chatid = call.message.chat.id
    lang = await get_lang(userid)

    from bson import ObjectId

    egg = await Egg.find_one(Egg.id == ObjectId(egg_id_str))  # type: ignore
    if not egg:
        await call.answer(
            t(
                "p_profile.boost_error",
                lang,
                default="❌ Ошибка: Ускорение недоступно!",
            ),
            show_alert=True,
        )
        return

    from bot.modules.items.collect_items import get_all_items
    

    inventory, count = await User.get_inventory(userid)
    all_items = get_all_items()

    boosters = []
    for item in inventory:
        item_id = item["items_data"]["item_id"]
        if item_id in all_items:
            item_data = all_items[item_id]
            if item_data.type == "incubation_boost":
                boosters.append(item)

    if not boosters:
        await call.answer()
        await bot.send_message(
            chatid,
            t(
                "p_profile.no_boosters",
                lang,
                default="❌ У вас нет ускорителей инкубации. Вы можете приобрести их в премиум-магазине по команде /premium.",
            ),
        )
        return

    from bot.modules.states_fabric.state_handlers import ChooseInventoryHandler

    await call.answer()

    try:
        await bot.delete_message(chatid, call.message.message_id)
    except:
        pass

    await ChooseInventoryHandler(
        use_boost_on_egg,
        userid,
        chatid,
        lang,
        type_filter=["incubation_boost"],
        transmitted_data={"egg_id": egg_id_str},
    ).start()


async def use_boost_on_egg(item: dict[str, Any], transmitted_data: dict[str, Any]) -> None:
    userid = transmitted_data["userid"]
    chatid = transmitted_data["chatid"]
    lang = transmitted_data["lang"]
    egg_id_str = transmitted_data["egg_id"]

    from bson import ObjectId

    egg = await Egg.find_one(Egg.id == ObjectId(egg_id_str))  # type: ignore
    if not egg:
        await bot.send_message(
            chatid,
            t(
                "p_profile.boost_error",
                lang,
                default="❌ Ошибка: Ускорение недоступно!",
            ),
            reply_markup=await m(userid, "last_menu", lang),
        )
        return

    from bot.modules.items.item import RemoveItemFromUser

    preabil = item.get("abilities", {})
    removed = await RemoveItemFromUser(userid, item["item_id"], 1, preabil)
    if not removed:
        await bot.send_message(
            chatid,
            t(
                "p_profile.boost_error",
                lang,
                default="❌ Ошибка: Ускорение недоступно!",
            ),
            reply_markup=await m(userid, "last_menu", lang),
        )
        return

    from bot.modules.items.collect_items import get_all_items

    all_items = get_all_items()
    item_data = all_items.get(item["item_id"])
    time_boost = getattr(item_data, "time_boost", 0) if item_data else 0

    new_incubation_time = egg.incubation_time - time_boost

    import time

    if new_incubation_time <= int(time.time()):
        from bot.models.dinosaur import Dino
        from bot.modules.managment.tracking import update_all_user_track
        from bot.modules.notifications import user_notification

        res, alt_id = await Dino.insert_dino(egg.owner_id, egg.dino_id, egg.quality)
        await Egg.find_one(Egg.id == egg.id).delete()  # type: ignore

        user = await User().create(egg.owner_id)
        await user_notification(
            egg.owner_id,
            "incubation_ready",
            lang,
            user_name=user.name,
            dino_alt_id_markup=alt_id,
        )

        assert user.userid is not None
        await update_all_user_track(user.userid, "gaming")
        await bot.send_message(
            chatid,
            t(
                "p_profile.boost_success",
                lang,
                default="⚡ Вылупление успешно ускорено!",
            ),
            reply_markup=await m(userid, "last_menu", lang),
        )
    else:
        await egg.update_incubation_time(new_incubation_time)
        from bot.modules.data_format import seconds_to_str

        boost_time_str = seconds_to_str(time_boost, lang)
        remained_time_str = seconds_to_str(
            max(0, new_incubation_time - int(time.time())), lang
        )
        text = t(
            "p_profile.boost_progress",
            lang,
            boost_time=boost_time_str,
            remained_time=remained_time_str,
            default=f"⚡ Инкубация ускорена на {boost_time_str}!\n⌛ Осталось времени: {remained_time_str}",
        )
        await bot.send_message(
            chatid, text, reply_markup=await m(userid, "last_menu", lang)
        )
