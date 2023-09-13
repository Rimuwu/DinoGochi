from bot.exec import bot
from typing import Optional
from time import time
from asyncio import sleep
from bot.modules.logs import log
from bot.modules.data_format import seconds_to_str

last_message = 0
col_now = 0

async def send_message(chat_id: int, text: str, 
                       parse_mode: Optional[str]=None, 
                       **kwargs):
    global col_now, last_message, last_messages, last_time_start
    """
        Use this method to send text messages.

        Warning: Do not send more than about 4096 characters each message, otherwise you'll risk an HTTP 414 error.
        If you must send more than 4096 characters, 
        use the `split_string` or `smart_split` function in util.py.

        Telegram documentation: https://core.telegram.org/bots/api#sendmessage

        :param chat_id: Unique identifier for the target chat or username of the target channel (in the format @channelusername)
        :type chat_id: :obj:`int` or :obj:`str`

        :param text: Text of the message to be sent
        :type text: :obj:`str`

        :param parse_mode: Mode for parsing entities in the message text.
        :type parse_mode: :obj:`str`

        :param entities: List of special entities that appear in message text, which can be specified instead of parse_mode
        :type entities: Array of :class:`telebot.types.MessageEntity`

        :param disable_web_page_preview: Disables link previews for links in this message
        :type disable_web_page_preview: :obj:`bool`

        :param disable_notification: Sends the message silently. Users will receive a notification with no sound.
        :type disable_notification: :obj:`bool`

        :param protect_content: If True, the message content will be hidden for all users except for the target user
        :type protect_content: :obj:`bool`

        :param reply_to_message_id: If the message is a reply, ID of the original message
        :type reply_to_message_id: :obj:`int`

        :param allow_sending_without_reply: Pass True, if the message should be sent even if the specified replied-to message is not found
        :type allow_sending_without_reply: :obj:`bool`

        :param reply_markup: Additional interface options. A JSON-serialized object for an inline keyboard, custom reply keyboard, instructions to remove reply keyboard or to force a reply from the user.
        :type reply_markup: :class:`telebot.types.InlineKeyboardMarkup` or :class:`telebot.types.ReplyKeyboardMarkup` or :class:`telebot.types.ReplyKeyboardRemove`
            or :class:`telebot.types.ForceReply`

        :param timeout: Timeout in seconds for the request.
        :type timeout: :obj:`int`

        :param message_thread_id: Unique identifier for the target message thread (topic) of the forum; for forum supergroups only
        :type message_thread_id: :obj:`int`

        :return: On success, the sent Message is returned.
        :rtype: :class:`telebot.types.Message`
        """

    if 'caption' in kwargs: kwargs['text'] = kwargs['caption']

    if last_message == int(time()):
        if col_now < 30:
            col_now += 1
            return await bot.send_message(chat_id, text, parse_mode, **kwargs)
        else:
            st = float(int(time()) + 1) - time()
            log(f'Достигнуто ограничение по сообщениям в секунду. Сон {st}')
            await sleep(st)
            return await bot.send_message(chat_id, text, parse_mode, **kwargs)
    else:
        last_message = int(time())
        col_now = 0
        return await bot.send_message(chat_id, text, parse_mode, **kwargs)