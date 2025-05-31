from datetime import datetime, timedelta
from random import randint

import matplotlib.pyplot as plt

def plot_stats(data, days=30, data_type='dinosaurs', output_file='output.png', filter_mode=None):
    """
    filter_mode: None (default) - обычный режим
                 'diff' - разница между днями
                 'percent' - процентное изменение между днями
    """
    type_map = {
        'dinosaurs': 'Динозавры',
        'users': 'Пользователи',
        'items': 'Предметы',
        'groups': 'Группы'
    }
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
        title_suffix = " (прирост)"

    elif filter_mode == 'percent':
        values = [0] + [
            ((curr - prev) / prev * 100 if prev != 0 else 0)
            for prev, curr in zip(values[:-1], values[1:])
        ]
        title_suffix = " (% изменение)"
    else:
        title_suffix = ""

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#222e22')
    ax.set_facecolor('#2e4d2e')

    ax.plot(dates, values, marker='o',
            color='#4caf50', linewidth=2, markersize=8,
            markerfacecolor='#81c784')

    ax.set_title(f"{type_map.get(data_type, data_type)} за последние {days} дней{title_suffix}",
                 color='white')
    ax.set_xlabel("Дата", color='white')
    ax.set_ylabel(type_map.get(data_type, data_type), color='white')
    ax.grid(True, color='#a5d6a7')
    ax.tick_params(colors='white')
    for spine in ax.spines.values():
        spine.set_color('#a5d6a7')

    plt.tight_layout()
    plt.savefig(output_file, facecolor=fig.get_facecolor())
    plt.close()

# Пример использования:
if __name__ == "__main__":
    # Пример данных
    data = [
        {'_id': '1', 'date': '2025-05-29', 'dinosaurs': 2200, 'users': 22000, 'items': 260000, 'groups': 80},
        {'_id': '2', 'date': '2025-05-30', 'dinosaurs': 2250, 'users': 22500, 'items': 262000},
        {'_id': '3', 'date': '2025-05-31', 'dinosaurs': 2268, 'users': 22819, 'items': 264361, 'groups': 82},
    ]
    
    for i in range(1, 206):
        data.append({
            '_id': str(i + 3),
            'date': (datetime.strptime(data[-1]['date'], "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d"),
            'dinosaurs': randint(1, 3000),
            'users': randint(20000, 30000),
            'items': randint(260000, 270000),
            'groups': randint(80, 100)
        })
    
    plot_stats(data, days=30, data_type='dinosaurs', output_file='dinosaurs.png')
    plot_stats(data, days=30, data_type='dinosaurs', output_file='dinosaurs_f.png', filter_mode='diff')
    # plot_stats(data, days=1000, data_type='groups', output_file='groups.png')
    # plot_stats(data, days=1000, data_type='users', output_file='users.png')