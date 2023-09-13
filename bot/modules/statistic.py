from datetime import datetime, timedelta

from bot.config import conf, mongo_client

statistic = mongo_client.other.statistic


async def get_now_statistic():
    """ {'items': 0, 'users': 0, 'dinosaurs': 0}
    """
    now = datetime.now()
    res, repets = None, -1

    while not res and repets < 25:
        repets += 1

        res = await statistic.find_one({'date': str(now.date())})
        if not res: now -= timedelta(days=1.0)

    return res