import numpy as np



import matplotlib.pyplot as plt

def plot_hourly_counts(hour_dict, 
                       filename='hourly_counts.png',
                       mode='count'):
    """
    Строит график по количеству значений в словаре с ключами-часами (0-23) и сохраняет его в файл.
    :param hour_dict: dict, где ключи - строки '0'...'23', значения - количества
    :param filename: имя файла для сохранения графика
    :param mode: 'count' (обычные значения), 'percent' (проценты), 'diff' (разность между соседними часами)
    """

    hours = [str(i) for i in range(24)]
    counts = [hour_dict.get(str(h), 0) for h in range(24)]

    if mode == 'percent':
        total = sum(counts)
        data = [(c / total * 100) if total > 0 else 0 for c in counts]
        ylabel = 'Процент'
        title = 'Распределение активности по часам (%)'

    elif mode == 'diff':
        data = np.diff([counts[-1]] + counts)  # разность между каждым и предыдущим (циклически)
        ylabel = 'Разность'
        title = 'Разность активности между часами'
        hours = [str(i) for i in range(24)]  # длина совпадает с diff

    else:
        data = counts
        ylabel = 'Количество'
        title = 'Распределение активности по часам'

    fig, ax = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor('#222e22')
    ax.set_facecolor('#2e4d2e')

    ax.grid(True, axis='y', color='#a5d6a7')

    font_size = 14  # увеличенный размер шрифта

    if mode == 'diff':
        ax.bar(hours, data, color='#ffb300', linewidth=2, edgecolor='#ffd54f')
    else:
        ax.bar(hours, data, color='#4caf50', linewidth=2, edgecolor='#81c784')

    ax.set_xlabel('Час (0-23)', color='white', fontsize=font_size)
    ax.set_ylabel(ylabel, color='white', fontsize=font_size)
    ax.set_title(title, color='white', fontsize=font_size + 2)
    ax.tick_params(colors='white', labelsize=font_size)

    plt.tight_layout()
    plt.savefig(filename, facecolor=fig.get_facecolor())
    plt.close()

# Пример использования:
data = {'0': 5, '1': 3, '2': 7, '4': 100, '5': 200, '23': 2}
plot_hourly_counts(data, 'output.png', 'count')