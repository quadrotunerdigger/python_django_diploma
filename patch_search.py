"""
Патч catalog.js для поддержки поиска из шапки сайта.

Фронтенд-пакет ``diploma-frontend`` при поиске из шапки перенаправляет
на ``/catalog/?filter=<запрос>``, но компонент каталога (``catalog.js``)
не читает этот параметр из URL. Данный скрипт патчит ``catalog.js``,
добавляя в хук ``mounted()`` чтение ``URLSearchParams.get('filter')``
и запись значения в ``this.filter.name``.

Патч применяется к последнему вхождению паттерна ``getCatalogs/getTags``
в файле (т.е. именно к ``mounted()``, а не к другим методам).

Использование::

    python patch_search.py

Примечание:
    Скрипт нужно запускать после установки фронтенд-пакета
    (``pip install dist/diploma-frontend-0.6.tar.gz``),
    так как он модифицирует файл внутри установленного пакета.
"""

import os

import frontend

path: str = os.path.join(
    os.path.dirname(frontend.__file__),
    "static/frontend/assets/js/catalog.js",
)

with open(path) as f:
    code: str = f.read()

# Исходный фрагмент в mounted(): загрузка каталога и тегов
old: str = "this.getCatalogs()\n        this.getTags()"

# Новый фрагмент: сначала прочитать фильтр из URL, затем загрузить данные
new: str = """const urlParams = new URLSearchParams(location.search)
        const searchFilter = urlParams.get('filter')
        if (searchFilter) {
            this.filter.name = searchFilter
        }
        this.getCatalogs()
        this.getTags()"""

# Заменяем только последнее вхождение (в mounted(), а не в других методах)
idx: int = code.rfind(old)
if idx != -1:
    code = code[:idx] + new + code[idx + len(old) :]
    with open(path, "w") as f:
        f.write(code)
    print(f"OK: patched {path}")
    print(f"urlParams count: {code.count('urlParams')}")
else:
    print("ERROR: pattern not found")
