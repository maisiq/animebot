"""Извлечение озвучек со страницы карточки аниме (animego.me).

На странице аниме есть блоки вида:

    <div class="g-col-5 ... text-body-tertiary ...">Озвучка</div>
    <div class="g-col-7 ... text-break">
        <a href="/anime/voiceover/28-anilibria" ... title="AniLibria">AniLibria</a>
        ...
    </div>

(структура аналогична блоку «Студия» из примера пользователя — та же сетка
g-col-*: левая колонка — подпись блока, правая — значения-ссылки).

Функция ``extract_dubbed_studios`` находит блок с подписью «Озвучка» и
возвращает названия студий. Так как в одном ряду сетки могут быть и другие
подписи («Тип», «Выход», «Ctries» и т.п.), candidates-значения фильтруются:
значение считается озвучкой, если оно есть в словаре известных студий
(DUB_LIST + содержимое таблицы voiceover_studios) либо это ссылка вида
/anime/voiceover/....
"""

from bs4 import BeautifulSoup

_LABEL_CLASSES = ('g-col-5', 'text-body-tertiary')
_VALUE_CLASSES = ('g-col-7', 'text-break')


def _has_all(classes: list[str], required: tuple[str, ...]) -> bool:
    return all(c in classes for c in required)


def extract_dubbed_studios(soup: BeautifulSoup, known_studios: set[str]) -> list[str]:
    """Возвращает список названий озвучек с карточки аниме (без дублей, порядок сохранён).

    known_studios — множество допустимых названий (DUB_LIST + БД). Пустое
    множество отключает фильтрацию по словарю: принимаются только ссылки
    /anime/voiceover/.
    """
    # 1. Ищем все div-подписи с текстом == "Озвучка" (на странице может быть
    # несколько блоков сетки; берём первый, у которого значения распознаны)
    labels = [
        div for div in soup.find_all('div')
        if _has_all(div.get('class') or [], _LABEL_CLASSES)
        and div.get_text(strip=True).lower() == 'озвучка'
    ]

    known_lower = {s.lower() for s in known_studios}
    result: list[str] = []

    for label in labels:
        # 2. Значения — соседний div того же ряда (g-col-7 ... text-break)
        value_block = label.find_next_sibling('div')
        if value_block is None or not _has_all(value_block.get('class') or [], _VALUE_CLASSES):
            continue

        anchors = value_block.find_all('a')
        if anchors:
            candidates = [(a.get('title') or a.get_text(strip=True), a) for a in anchors]
        else:
            candidates = [(value_block.get_text(strip=True), None)]

        for name, anchor in candidates:
            name = (name or '').strip()
            if not name or name in result:
                continue
            href = (anchor.get('href') or '') if anchor is not None else ''
            # озвучкой считаем ссылку вида /anime/voiceover/... либо название
            # из словаря известных студий (DUB_LIST + voiceover_studios из БД)
            if '/anime/voiceover/' in href or name.lower() in known_lower:
                result.append(name)

        if result:
            break

    return result
