from bot.models.other import Statistic
from datetime import datetime, timedelta
from bot.dbmanager import mongo_client
import matplotlib.pyplot as plt

from bot.modules.images import async_open
from bot.modules.localization import t, get_data

async def get_now_statistic():
    """ {'items': 0, 'users': 0, 'dinosaurs': 0, 'groups': 0}
    """
    now = datetime.now()
    res, repets = None, -1

    while not res and repets < 25:
        repets += 1

        res_model = await Statistic.find_one(Statistic.date == str(now.date()))
        res = res_model.dict() if res_model else None
        if not res: 
            now -= timedelta(days=1.0)

    return res

def plot_stats(data, days=30, data_type='dinosaurs', output_file='output.png', 
               filter_mode=None, lang='ru'):
    """
    filter_mode: None (default) - обычный режим
                 'diff' - разница между днями
                 'percent' - процентное изменение между днями
    """
    loc_data = get_data('grafs', lang)
    type_map = {
        'dinosaurs': loc_data['dinosaurs'],
        'users': loc_data['users'],
        'items': loc_data['items'],
        'groups': loc_data['groups']
    }

    if not data:
        data = [{
            'date': datetime.now(),
            'dinosaurs': 0,
            'users': 0,
            'items': 0,
            'groups': 0
        }]

    for entry in data:
        if not isinstance(entry['date'], datetime):
            entry['date'] = datetime.strptime(entry['date'], "%Y-%m-%d")
        if 'groups' not in entry:
            entry['groups'] = 0

    data.sort(key=lambda x: x['date'])
    end_date = data[-1]['date']
    start_date = end_date - timedelta(days=days-1)
    filtered = [d for d in data if start_date <= d['date'] <= end_date]

    dates = [d['date'] for d in filtered]
    values = [d.get(data_type, 0) for d in filtered]

    # Фильтрация значений
    if filter_mode == 'diff':
        values = [0] + [curr - prev for prev, curr in zip(values[:-1], values[1:])]
        title_suffix = " " + loc_data['diff']

    elif filter_mode == 'percent':
        values = [0] + [
            ((curr - prev) / prev * 100 if prev != 0 else 0)
            for prev, curr in zip(values[:-1], values[1:])
        ]
        title_suffix = " " + loc_data['percent']
    else:
        title_suffix = ""

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#222e22')
    ax.set_facecolor('#2e4d2e')

    ax.plot(dates, values, marker='o',
            color='#4caf50', linewidth=2, markersize=8,
            markerfacecolor='#81c784')
    
    
    name_graf = type_map.get(data_type, data_type)
    text = loc_data['title'].format(name_graf=name_graf, days=days, title_suffix=title_suffix)
    ax.set_title(text, color='white')

    ax.set_xlabel(loc_data['date'], color='white')

    ax.set_ylabel(type_map.get(data_type, data_type), color='white')
    ax.grid(True, color='#a5d6a7')

    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_color('#a5d6a7')

    plt.tight_layout()
    import os
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    plt.savefig(output_file, facecolor=fig.get_facecolor())
    plt.close()

async def get_simple_graf(days=30, data_type='dinosaurs', filter_mode=None, lang='ru'):
    """
    Возвращает данные за последние `days` дней.
    filter_mode: None (default) - обычный режим
                 'diff' - разница между днями
                 'percent' - процентное изменение между днями
    """

    data_models = await Statistic.find_all().to_list()
    data = [d.dict() for d in data_models]

    output_file = f'bot/temp/graf_{lang}_{data_type}.png'
    plot_stats(data, days=days, data_type=data_type, 
               output_file=output_file, filter_mode=filter_mode, lang=lang)

    fil = await async_open(output_file, True)
    return fil