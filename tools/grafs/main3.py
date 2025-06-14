import matplotlib.pyplot as plt

def plot_pie_chart(data: dict, filename: str):
    """
    Строит круговую диаграмму по словарю data и сохраняет в файл filename.
    :param data: словарь {код_языка: количество}
    :param filename: имя файла для сохранения (например, 'chart.png')
    """
    labels = list(data.keys())
    sizes = list(data.values())

    # Цвета в стиле main2.py (зелёные оттенки)
    colors = ["#0b946d", '#388e3c', "#0f6f19", "#5b900c"]

    fig = plt.figure(figsize=(10, 5))
    fig.patch.set_facecolor('#222e22')

    # Используем gridspec для двух областей
    gs = fig.add_gridspec(
        1, 2, 
        width_ratios=[1, 2], 
        wspace=0.05
    )

    ax_text = fig.add_subplot(gs[0, 0])
    ax_pie = fig.add_subplot(gs[0, 1])
    ax_text.set_facecolor('#2e4d2e')
    ax_pie.set_facecolor('#2e4d2e')

    # Левая часть: текст и мини-таблица
    ax_text.axis('off')
    ax_text.text(0.5, 0.93, 'Распределение по языкам', color='white', fontsize=16, ha='center', va='top', weight='bold')

    # Формируем данные для таблицы
    cell_text = [[label, value] for label, value in zip(labels, sizes)]
    table = ax_text.table(
        cellText=cell_text,
        colLabels=["Язык", "Количество"],
        cellLoc='center',
        loc='center',
        colColours=['#388e3c', '#388e3c']
    )

    table.auto_set_font_size(False)
    table.set_fontsize(15)
    table.scale(1.2, 2)

    # Стилизация таблицы: белый текст, прозрачный фон, зелёная обводка
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#a5d6a7')
        cell.set_linewidth(1.5)
        cell.set_text_props(color='white')
        if row == 0:
            cell.set_facecolor('#388e3c')
        else:
            cell.set_facecolor((0,0,0,0))

    # Правая часть: круговая диаграмма
    pie_result = ax_pie.pie(
        sizes,
        labels=labels,
        autopct='%1.1f%%',
        startangle=140,
        colors=colors[:len(sizes)],
        textprops={'color': 'white', 'fontsize': 14}
    )

    # Совместимость с разными версиями matplotlib
    if len(pie_result) == 3:
        wedges, texts, autotexts = pie_result
    else:
        wedges, texts = pie_result
        autotexts = []

    # Оформление подписей
    for text in texts:
        text.set_color('white')
        text.set_fontsize(14)

    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_fontsize(14)

    ax_pie.set_title('', color='white', fontsize=16)
    ax_pie.axis('equal')  # Круглая диаграмма

    # Вместо tight_layout используем subplots_adjust для корректных отступов
    fig.subplots_adjust(
        left=0.07, 
        right=0.98, 
        top=0.95, 
        bottom=0.05)
    plt.savefig(filename, facecolor=fig.get_facecolor())
    plt.close()

# Пример использования:
if __name__ == "__main__":
    lang_counts = {'en': 50, 
                   'es': 100,
                   'ru': 30, 'id': 20}
    plot_pie_chart(lang_counts, 'languages_pie.png')