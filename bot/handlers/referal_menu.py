from bot.modules.states_fabric.state_handlers import ChooseCustomHandler
from bot.models.user import Referral
from aiogram.types import CallbackQuery, Message, BufferedInputFile

from bot.const import GAME_SETTINGS as GS
from bot.exec import main_router, bot
from bot.modules.data_format import escape_markdown, list_to_inline
from bot.modules.localization import get_data, t, get_lang
from bot.modules.markup import markups_menu as m
from bot.models.user import Referral, User

from bot.filters.translated_text import StartWith, Text
from bot.filters.private import IsPrivateChat
from bot.filters.authorized import IsAuthorizedUser
from aiogram import F


# ---------------------------------------------------------------------------
# My code: show referral link
# ---------------------------------------------------------------------------

@main_router.message(IsPrivateChat(), StartWith('commands_name.referal.my_code'), IsAuthorizedUser())
async def my_code(message: Message):
    """Button: My referral code."""
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    referal = await Referral.find_one(Referral.userid == userid, Referral.type == "general")
    if referal:
        code = referal.code
        uses = len(await Referral.find(
            Referral.code == code, Referral.type == "sub"
        ).to_list())

        iambot = await bot.get_me()
        bot_name = iambot.username
        url = f'https://t.me/{bot_name}/?start={code}'

        has_rewards = await Referral.has_pending_rewards(userid)
        reward_hint = (' 🔥' if has_rewards else '')

        await bot.send_message(
            chatid,
            t('referals.my_code', lang, code=code, url=url, uses=uses) + reward_hint,
            parse_mode='Markdown'
        )


# ---------------------------------------------------------------------------
# Generate code
# ---------------------------------------------------------------------------

async def create_custom_code(code: str, transmitted_data: dict):
    lang = transmitted_data['lang']
    userid = transmitted_data['userid']
    chatid = transmitted_data['chatid']

    existing = await Referral.find_one(Referral.userid == userid, Referral.type == 'general')
    if existing:
        await bot.send_message(chatid, t('referals.have_code', lang))
        return

    from bot.modules.overwriting.DataCalsses import Transaction
    async with Transaction():
        user = await User.find_one(User.userid == userid)
        if user and await user.remove_coins(abs(GS['referal']['custom_price'])):
            code = code.replace(' ', '')
            await Referral.create_referal(userid, code)
            has_coins = True
        else:
            has_coins = False

    if has_coins:
        iambot = await bot.get_me()
        bot_name = iambot.username
        url = f'https://t.me/{bot_name}/?start={code}'
        text = t('referals.code', lang, code=code, url=url)
    else:
        text = t('referals.custom_code.no_coins', lang)

    await bot.send_message(
        chatid, text, parse_mode='Markdown',
        reply_markup=await m(userid, 'last_menu', lang, True)
    )


async def custom_handler(message: Message, transmitted_data: dict):
    lang = transmitted_data['lang']
    chatid = transmitted_data['chatid']

    code = escape_markdown(str(message.text))
    status = False
    text = ''

    if len(code) > 10:
        text = t('referals.custom_code.max_len', lang)
    if len(code) == 0:
        text = t('referals.custom_code.min_len', lang)
    else:
        res = await Referral.find_one(Referral.code == code)
        if res:
            text = t('referals.custom_code.found_code', lang)
        else:
            status = True

    if not status:
        await bot.send_message(chatid, text, parse_mode='Markdown')
    return status, code


@main_router.message(IsPrivateChat(), StartWith('commands_name.referal.code'), IsAuthorizedUser())
async def generate_code_start(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    ref_obj = await Referral.find_one(Referral.userid == userid, Referral.type == "general")
    if not ref_obj:
        var_buttons = get_data('referals.var_buttons', lang)
        buttons = []
        for k, v in var_buttons.items():
            buttons.append({v: k})
        markup = list_to_inline([buttons])
        price = GS['referal']['custom_price']
        await bot.send_message(
            chatid,
            t('referals.generate', lang, price=price),
            parse_mode='Markdown',
            reply_markup=markup
        )
    else:
        await bot.send_message(chatid, t('referals.have_code', lang))


@main_router.callback_query(IsPrivateChat(), F.data.startswith('generate_referal'))
async def generate_code(call: CallbackQuery):
    chatid = call.message.chat.id
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    action = call.data.split()[1]

    ref_obj = await Referral.find_one(Referral.userid == userid, Referral.type == "general")
    if not ref_obj:
        if action == 'random':
            ref = await Referral.create_referal(userid)
            code = ref[1]
            iambot = await bot.get_me()
            bot_name = iambot.username
            url = f'https://t.me/{bot_name}/?start={code}'
            await bot.send_message(
                chatid,
                t('referals.code', lang, code=code, url=url),
                parse_mode='Markdown',
                reply_markup=await m(userid, 'last_menu', lang, True)
            )
        elif action == 'custom':
            from bot.modules.markup import cancel_markup
            await bot.send_message(
                chatid,
                t('referals.custom_code.start', lang),
                parse_mode='Markdown',
                reply_markup=cancel_markup(lang)
            )
            await ChooseCustomHandler(
                create_custom_code, custom_handler,
                userid, chatid, lang
            ).start()
    else:
        await bot.send_message(chatid, t('referals.have_code', lang))


# ---------------------------------------------------------------------------
# Dummy callback for pagination counters
# ---------------------------------------------------------------------------

@main_router.callback_query(IsPrivateChat(), F.data == 'referal_none', IsAuthorizedUser())
async def referal_none_callback(call: CallbackQuery):
    await call.answer()


# ---------------------------------------------------------------------------
# Claim reward (with pagination)
# ---------------------------------------------------------------------------

async def send_claim_reward_menu(userid: int, chatid: int, lang: str, page: int = 1, message_to_edit=None):
    pending = await Referral.get_pending_inviter_rewards(userid)
    if not pending:
        text = t('referals.claim_reward.empty', lang)
        if message_to_edit:
            try:
                await message_to_edit.edit_text(text, parse_mode='Markdown')
            except Exception:
                await bot.send_message(chatid, text, parse_mode='Markdown')
        else:
            await bot.send_message(chatid, text, parse_mode='Markdown')
        return

    items_per_page = 5
    total_pages = max(1, (len(pending) - 1) // items_per_page + 1)
    page = max(1, min(page, total_pages))

    page_pending = pending[(page - 1) * items_per_page : page * items_per_page]

    btn_rows = []
    for entry in page_pending:
        lvl   = entry['lvl']
        coins = entry['coins']
        sc    = entry['sc']
        count = entry['count']
        label = t('referals.claim_reward.button', lang, lvl=lvl, coins=coins, sc=sc, count=count)
        btn_rows.append([{label: f'referal_claim {lvl} {page}'}])

    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append({GS['back_button']: f'referal_claim_page {page - 1}'})
        nav_row.append({f'{page}/{total_pages}': 'referal_none'})
        if page < total_pages:
            nav_row.append({GS['forward_button']: f'referal_claim_page {page + 1}'})
        btn_rows.append(nav_row)

    markup = list_to_inline(btn_rows)
    text = t('referals.claim_reward.choose', lang)

    if message_to_edit:
        try:
            await message_to_edit.edit_text(text, parse_mode='Markdown', reply_markup=markup)
        except Exception:
            await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)
    else:
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)


@main_router.message(IsPrivateChat(), Text('commands_name.referal.claim_reward'), IsAuthorizedUser())
async def claim_reward_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    await send_claim_reward_menu(userid, chatid, lang, page=1)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('referal_claim_page'), IsAuthorizedUser())
async def claim_reward_page_callback(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id

    parts = call.data.split()
    page = int(parts[1]) if len(parts) > 1 else 1

    await send_claim_reward_menu(userid, chatid, lang, page=page, message_to_edit=call.message)
    await call.answer()


@main_router.callback_query(IsPrivateChat(), F.data.startswith('referal_claim '), IsAuthorizedUser())
async def do_claim_reward(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id

    parts = call.data.split()
    lvl = int(parts[1])
    page = int(parts[2]) if len(parts) > 2 else 1

    success = await Referral.claim_inviter_reward(userid, lvl)

    if success:
        from bot.const import GAME_SETTINGS as gs
        lvl_cfg = gs['referal']['levels'].get(str(lvl), {})
        coins = lvl_cfg.get('inviter_coins', 0)
        sc    = lvl_cfg.get('inviter_sc', 0)
        text = t('referals.claim_reward.success', lang, lvl=lvl, coins=coins, sc=sc)
    else:
        text = t('referals.claim_reward.fail', lang)

    await bot.send_message(chatid, text, parse_mode='Markdown',
                           reply_markup=await m(userid, 'last_menu', lang, True))
    await send_claim_reward_menu(userid, chatid, lang, page=page, message_to_edit=call.message)
    await call.answer()


# ---------------------------------------------------------------------------
# My referrals list (with pagination)
# ---------------------------------------------------------------------------

async def send_my_referals_menu(userid: int, chatid: int, lang: str, page: int = 1, message_to_edit=None):
    referal_doc = await Referral.get_user_code(userid)
    if not referal_doc:
        text = t('referals.my_referals.no_code', lang)
        if message_to_edit:
            try:
                await message_to_edit.edit_text(text, parse_mode='Markdown')
            except Exception:
                await bot.send_message(chatid, text, parse_mode='Markdown')
        else:
            await bot.send_message(chatid, text, parse_mode='Markdown')
        return

    code = referal_doc.code
    subs = await Referral.find(Referral.code == code, Referral.type == "sub").to_list()

    if not subs:
        text = t('referals.my_referals.empty', lang)
        if message_to_edit:
            try:
                await message_to_edit.edit_text(text, parse_mode='Markdown')
            except Exception:
                await bot.send_message(chatid, text, parse_mode='Markdown')
        else:
            await bot.send_message(chatid, text, parse_mode='Markdown')
        return

    REWARD_LEVELS = [1, 5, 15, 30, 50]

    def has_unclaimed(sub):
        for lvl in sub.invited_lvl_rewards_given:
            if lvl not in REWARD_LEVELS:
                continue
            if lvl not in sub.inviter_claimed_lvls:
                return True
        return False

    subs_sorted = sorted(subs, key=lambda s: (0 if has_unclaimed(s) else 1, -s.referral_lvl))

    items_per_page = 10
    total_pages = max(1, (len(subs_sorted) - 1) // items_per_page + 1)
    page = max(1, min(page, total_pages))

    page_subs = subs_sorted[(page - 1) * items_per_page : page * items_per_page]

    lines = []
    for sub in page_subs:
        user = await User.find_one(User.userid == sub.userid)
        name = user.name if user else str(sub.userid)
        fire = ' 🔥' if has_unclaimed(sub) else ''
        lvl_str = f' (LVL {sub.referral_lvl})' if sub.referral_lvl > 0 else ''
        lines.append(f"• {name}{fire}{lvl_str}")

    text = t('referals.my_referals.header', lang, count=len(subs)) + '\n\n' + '\n'.join(lines)
    if total_pages > 1:
        page_str = t('referals.my_referals.page_label', lang, page=page, total_pages=total_pages)
        text += f"\n\n📖 *{page_str}*"

    btn_rows = []
    if total_pages > 1:
        nav_row = []
        if page > 1:
            nav_row.append({GS['back_button']: f'referal_my_page {page - 1}'})
        nav_row.append({f'{page}/{total_pages}': 'referal_none'})
        if page < total_pages:
            nav_row.append({GS['forward_button']: f'referal_my_page {page + 1}'})
        btn_rows.append(nav_row)

    markup = list_to_inline(btn_rows) if btn_rows else None

    if message_to_edit:
        try:
            await message_to_edit.edit_text(text, parse_mode='Markdown', reply_markup=markup)
        except Exception:
            await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)
    else:
        await bot.send_message(chatid, text, parse_mode='Markdown', reply_markup=markup)


@main_router.message(IsPrivateChat(), Text('commands_name.referal.my_referals'), IsAuthorizedUser())
async def my_referals_menu(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id
    await send_my_referals_menu(userid, chatid, lang, page=1)


@main_router.callback_query(IsPrivateChat(), F.data.startswith('referal_my_page'), IsAuthorizedUser())
async def my_referals_page_callback(call: CallbackQuery):
    userid = call.from_user.id
    lang = await get_lang(call.from_user.id)
    chatid = call.message.chat.id

    parts = call.data.split()
    page = int(parts[1]) if len(parts) > 1 else 1

    await send_my_referals_menu(userid, chatid, lang, page=page, message_to_edit=call.message)
    await call.answer()


# ---------------------------------------------------------------------------
# Info: show referral image with reward table
# ---------------------------------------------------------------------------

@main_router.message(IsPrivateChat(), Text('commands_name.referal.info'), IsAuthorizedUser())
async def referal_info(message: Message):
    userid = message.from_user.id
    lang = await get_lang(message.from_user.id)
    chatid = message.chat.id

    from bot.modules.items.item import counts_items
    from bot.modules.images_save import send_SmartPhoto

    levels_cfg = GS.get('referal', {}).get('levels', {})
    quote_blocks = []

    for lvl in [1, 5, 15, 30, 50]:
        lvl_cfg = levels_cfg.get(str(lvl), {})
        coins = lvl_cfg.get('inviter_coins', 0)
        sc = lvl_cfg.get('inviter_sc', 0)
        invited_items = lvl_cfg.get('invited_items', [])

        inviter_parts = []
        if coins > 0:
            coins_str = f"{coins:,}".replace(",", ".")
            inviter_parts.append(f"{coins_str} {{custom_emoji:coins}}")
        if sc > 0:
            inviter_parts.append(f"{sc} {{custom_emoji:super_coin}}")
        inviter_str = ", ".join(inviter_parts)

        invited_str = counts_items(invited_items, lang, html=True)
        lvl_title = t('referals.info.lvl_header', lang, lvl=lvl)
        lvl_note = f"\n{t('referals.info.lvl_1_note', lang)}" if lvl == 1 else ''

        block = (
            f"<blockquote>{lvl_title}\n"
            f"{{custom_emoji:person}} {inviter_str}\n"
            f"{{custom_emoji:persons}} {invited_str}{lvl_note}</blockquote>"
        )
        quote_blocks.append(block)

    rewards_list = "\n\n".join(quote_blocks)

    # Check if user is an invitee and calculate levels to next reward
    caption_extra = ''
    sub = await Referral.get_user_sub(userid)
    if sub:
        REWARD_LEVELS = [1, 5, 15, 30, 50]
        cur_lvl = sub.referral_lvl
        given   = sub.invited_lvl_rewards_given
        next_reward_lvl = None
        for rl in REWARD_LEVELS:
            if rl not in given and cur_lvl < rl:
                next_reward_lvl = rl
                break
        if next_reward_lvl:
            levels_left = next_reward_lvl - cur_lvl
            caption_extra = '\n\n' + t('referals.info.next_reward', lang,
                                       levels=levels_left, next_lvl=next_reward_lvl)

    text = t('referals.info.caption', lang, rewards_list=rewards_list) + caption_extra
    await send_SmartPhoto(chatid, 'images/remain/referral_image.png', caption=text, parse_mode='HTML')

