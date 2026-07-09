from typing import Union, Optional
from bson import ObjectId
from bot.models.other import Company, MessageLog

async def generation_code(owner_id):
    return await Company.generation_code(owner_id)

async def create_company(owner: int, message: dict, time_end: int, 
                        count: int, coin_price: int, priority: bool, 
                        one_message: bool, pin_message: bool, min_timeout: int,
                        delete_after: bool, ignore_system_timeout: bool, name: str,
                        min_reg_time: int = 0
                        ):
    await Company.create_company(
        owner=owner, message=message, time_end=time_end, count=count,
        coin_price=coin_price, priority=priority, one_message=one_message,
        pin_message=pin_message, min_timeout=min_timeout, delete_after=delete_after,
        ignore_system_timeout=ignore_system_timeout, name=name, min_reg_time=min_reg_time
    )

async def save_message(advert_id: ObjectId, userid: int, message_id: int):
    await MessageLog.save_message(advert_id, userid, message_id)

async def end_company(advert_id: ObjectId):
    await Company.end_company(advert_id)

async def generate_message(userid: int, company_id: ObjectId, lang = None, save = True):
    return await Company.generate_message(userid, company_id, lang, save)

async def nextinqueue(userid: int, lang = None) -> Union[ObjectId, None]:
    return await Company.nextinqueue(userid, lang)

async def priority_and_timeout(companie_id: ObjectId):
    return await Company.priority_and_timeout(companie_id)

async def user_reg_min(userid: int, companie_id: ObjectId) -> bool:
    return await Company.user_reg_min(userid, companie_id)

async def info(companie_id: ObjectId, lang = None):
    return await Company.info(companie_id, lang)
