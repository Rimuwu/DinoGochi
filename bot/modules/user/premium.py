from bot.models.user import Subscription
import time

async def premium(userid: int):
    sub = await Subscription.find_one(Subscription.userid == userid)
    if sub:
        if isinstance(sub.sub_end, str) and sub.sub_end == "inf":
            return True
        if isinstance(sub.sub_end, (int, float)) and sub.sub_end > time.time():
            return True
    return False