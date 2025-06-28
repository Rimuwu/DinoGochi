
import math
from PIL import Image, ImageDraw
from typing import Union


def draw_dotted_arc_on_cells(
    img: Image.Image,
    cells: list,
    cell_size: int = 100,
    color: Union[tuple, str] = (0, 0, 0, 255),
    width: int = 4,
    dot_length: int = 10,
    gap_length: int = 10,
    cell_points: list = None  # Новый параметр: список словарей {"cell": [x, y], "percent": float (0..1)}
    ):
    """
    Рисует сглаженную пунктирную дугу по центрам указанных ячеек.
    cells: список [x, y] координат ячеек (дуга идет по порядку).
    color: цвет дуги.
    width: толщина дуги.
    dot_length: длина штриха.
    gap_length: длина промежутка между штрихами.
    cell_points: список {"cell": [x, y], "percent": float (0..1)} — для каждой клетки рисует точку на соответствующем проценте прохода этой клетки.
    """

    draw = ImageDraw.Draw(img)

    # Получаем список центров ячеек
    centers = [
        (
            x * cell_size + cell_size // 2,
            y * cell_size + cell_size // 2
        )
        for x, y in cells
    ]

    if len(centers) < 2:
        return img  # нечего рисовать

    # Используем сглаженную кривую Catmull-Rom для плавности
    def catmull_rom_spline(P, n_points=500):
        """P - список точек, n_points - сколько точек на кривой"""
        if len(P) < 2:
            return P

        # Добавляем фиктивные точки в начало и конец для плавности
        points = [P[0]] + P + [P[-1]]
        curve = []
        for i in range(1, len(points) - 2):
            p0, p1, p2, p3 = points[i-1], points[i], points[i+1], points[i+2]
            for t in [j / n_points for j in range(n_points)]:
                t2 = t * t
                t3 = t2 * t
                x = 0.5 * (
                    (2 * p1[0]) +
                    (-p0[0] + p2[0]) * t +
                    (2*p0[0] - 5*p1[0] + 4*p2[0] - p3[0]) * t2 +
                    (-p0[0] + 3*p1[0] - 3*p2[0] + p3[0]) * t3
                )
                y = 0.5 * (
                    (2 * p1[1]) +
                    (-p0[1] + p2[1]) * t +
                    (2*p0[1] - 5*p1[1] + 4*p2[1] - p3[1]) * t2 +
                    (-p0[1] + 3*p1[1] - 3*p2[1] + p3[1]) * t3
                )
                curve.append((x, y))
        curve.append(P[-1])
        return curve

    if len(centers) == 2:
        arc_points = [centers[0], centers[1]]
    else:
        arc_points = catmull_rom_spline(centers, n_points=100)

    # Теперь рисуем пунктир по дуге
    # Сначала вычисляем длину всей дуги и создаём список сегментов
    segments = []
    for i in range(len(arc_points) - 1):
        p1 = arc_points[i]
        p2 = arc_points[i + 1]
        seg_len = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
        segments.append((p1, p2, seg_len))

    total_len = sum(seg[2] for seg in segments)
    if total_len == 0:
        return img

    # Для поиска позиции точки внутри клетки
    def get_cell_arc_range(cells, arc_points):
        """
        Возвращает список (start_idx, end_idx) для каждой клетки,
        где start_idx - индекс первой точки дуги внутри клетки,
        end_idx - индекс последней точки дуги внутри клетки.
        """
        cell_ranges = []
        for idx, (x, y) in enumerate(cells):
            left = x * cell_size
            top = y * cell_size
            right = (x + 1) * cell_size
            bottom = (y + 1) * cell_size
            indices = [i for i, (px, py) in enumerate(arc_points)
                        if left <= px < right and top <= py < bottom]
            if indices:
                cell_ranges.append((min(indices), max(indices)))
            else:
                cell_ranges.append((None, None))
        return cell_ranges

    # Теперь идём по дуге, чередуя dot_length и gap_length
    pos_on_curve = 0
    seg_idx = 0
    seg_pos = 0

    while pos_on_curve < total_len:
        # Рисуем штрих
        draw_len = min(dot_length, total_len - pos_on_curve)
        start = None
        end = None
        draw_left = draw_len
        curr_pos = pos_on_curve

        # Найти начальную точку
        while seg_idx < len(segments):
            p1, p2, seg_len = segments[seg_idx]
            if seg_pos + draw_left <= seg_len:
                # В пределах текущего сегмента
                ratio_start = seg_pos / seg_len if seg_len != 0 else 0
                ratio_end = (seg_pos + draw_left) / seg_len if seg_len != 0 else 0
                start = (
                    p1[0] + (p2[0] - p1[0]) * ratio_start,
                    p1[1] + (p2[1] - p1[1]) * ratio_start
                )
                end = (
                    p1[0] + (p2[0] - p1[0]) * ratio_end,
                    p1[1] + (p2[1] - p1[1]) * ratio_end
                )
                draw.line([start, end], fill=color, width=width)
                seg_pos += draw_left
                if seg_pos >= seg_len:
                    seg_idx += 1
                    seg_pos = 0
                break
            else:
                # Заканчиваем сегмент, переходим к следующему
                if seg_len - seg_pos > 0:
                    ratio_start = seg_pos / seg_len if seg_len != 0 else 0
                    start = (
                        p1[0] + (p2[0] - p1[0]) * ratio_start,
                        p1[1] + (p2[1] - p1[1]) * ratio_start
                    )
                    end = p2
                    draw.line([start, end], fill=color, width=width)
                    draw_left -= (seg_len - seg_pos)
                seg_idx += 1
                seg_pos = 0

        pos_on_curve += draw_len

        # Пропускаем gap
        gap_left = gap_length
        while gap_left > 0 and seg_idx < len(segments):
            p1, p2, seg_len = segments[seg_idx]
            if seg_pos + gap_left <= seg_len:
                seg_pos += gap_left
                gap_left = 0
                if seg_pos >= seg_len:
                    seg_idx += 1
                    seg_pos = 0
            else:
                gap_left -= (seg_len - seg_pos)
                seg_idx += 1
                seg_pos = 0
        pos_on_curve += gap_length

    # --- Добавляем точки с процентом прохода клетки ---
    if cell_points:
        # Получаем диапазоны индексов дуги для каждой клетки
        cell_ranges = get_cell_arc_range(cells, arc_points)
        for cp in cell_points:
            cell = cp.get("cell")
            percent = cp.get("percent", 0.5)
            if not cell or percent is None:
                continue

            try:
                idx = cells.index(cell)
            except ValueError:
                continue

            start_idx, end_idx = cell_ranges[idx]
            if start_idx is None or end_idx is None or end_idx <= start_idx:
                continue

            arc_idx = int(start_idx + (end_idx - start_idx) * percent)
            arc_idx = max(start_idx, min(end_idx, arc_idx))
            px, py = arc_points[arc_idx]
            # Рисуем точку (круг)
            r = width * 2  # радиус точки (можно настроить)
            r = max(6, width * 2)
            draw.ellipse(
                [px - r, py - r, px + r, py + r],
                fill=color if isinstance(color, tuple) else (255, 0, 0, 255)
            )

    return img