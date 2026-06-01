"""
Патч фронтенд-пакета для корректной работы оплаты.

Фронтенд-пакет ``diploma-frontend`` имеет две проблемы с оплатой:

1. **Ошибки оплаты не отображаются.** Фронтенд обрабатывает ошибки
   в ``.catch()``, который срабатывает только при HTTP-статусах 4xx/5xx.
   Наш бэкенд возвращает ошибки со статусом 200 (в поле ``error`` JSON),
   чтобы фронтенд мог прочитать текст ошибки. Патч переписывает
   ``payment.js``, чтобы ошибки читались из тела ответа и показывались
   через ``alert()``.

2. **Нет кнопки генерации номера счёта.** При выборе способа оплаты
   «со случайного чужого счёта» (``type=someone``) пользователю нужна
   кнопка для генерации валидного 8-значного номера. Патч добавляет
   кнопку в ``payment.html`` и метод ``generateNumber()`` в ``payment.js``.

Патч затрагивает 3 файла внутри установленного пакета:
    - ``payment.js`` — полная перезапись: обработка ошибок, генерация номера.
    - ``payment.html`` — добавление кнопки «Сгенерировать случайный счёт».
    - ``order-detail.js`` — передача типа оплаты через URL-параметр ``?type=``.

Использование::

    python patch_payment.py

Примечание:
    Скрипт нужно запускать после установки фронтенд-пакета.
    Все файлы открываются с ``encoding="utf-8"`` для корректной работы
    на Windows (где системная кодировка может быть cp1252).
"""

import os

import frontend


def _get_frontend_path(*parts: str) -> str:
    """
    Построить абсолютный путь к файлу внутри пакета ``frontend``.

    Args:
        parts: Компоненты пути относительно корня пакета
               (например, ``"static", "frontend", "assets", "js", "payment.js"``).

    Returns:
        Абсолютный путь к файлу.
    """
    return os.path.join(os.path.dirname(frontend.__file__), *parts)


# ═══════════════════════════════════════════════
# Шаг 1. Полная перезапись payment.js
# ═══════════════════════════════════════════════
#
# Новая версия:
#   - submitPayment(): читает ошибку из тела ответа (data.error),
#     показывает alert при ошибке, редиректит на главную при успехе.
#   - generateNumber(): генерирует валидный 8-значный номер
#     (последняя цифра — чётная, не 0, чтобы оплата прошла).
#   - mounted(): показывает кнопку генерации только если URL
#     содержит ?type=someone.

PAYMENT_JS_CODE: str = """var mix = {
\tmethods: {
\t\tsubmitPayment() {
\t\t\tconst orderId = location.pathname.startsWith('/payment/')
\t\t\t\t? Number(location.pathname.replace('/payment/', '').replace('/', ''))
\t\t\t\t: null
\t\t\tthis.postData('/api/payment/' + orderId, {
\t\t\t\tname: this.name,
\t\t\t\tnumber: this.number1,
\t\t\t\tyear: this.year,
\t\t\t\tmonth: this.month,
\t\t\t\tcode: this.code
\t\t\t}).then(function(response) {
\t\t\t\tvar data = response.data || response
\t\t\t\tif (data && data.error) {
\t\t\t\t\talert('Ошибка оплаты: ' + data.error)
\t\t\t\t} else {
\t\t\t\t\talert('Успешная оплата')
\t\t\t\t\tlocation.assign('/')
\t\t\t\t}
\t\t\t}).catch(function() {
\t\t\t\tconsole.warn('Ошибка при оплате')
\t\t\t})
\t\t},
\t\tgenerateNumber() {
\t\t\tvar num = ''
\t\t\tfor (var i = 0; i < 7; i++) {
\t\t\t\tnum += Math.floor(Math.random() * 10).toString()
\t\t\t}
\t\t\tvar lastDigits = [2, 4, 6, 8]
\t\t\tnum += lastDigits[Math.floor(Math.random() * 4)].toString()
\t\t\tthis.number1 = num
\t\t}
\t},
\tmounted() {
\t\tvar params = new URLSearchParams(location.search)
\t\tvar type = params.get('type')
\t\tvar btn = document.getElementById('generateBtn')
\t\tif (btn && type === 'someone') {
\t\t\tbtn.style.display = 'inline-block'
\t\t}
\t},
\tdata() {
\t\treturn {
\t\t\tnumber1: '',
\t\t\tmonth: '',
\t\t\tyear: '',
\t\t\tname: '',
\t\t\tcode: ''
\t\t}
\t}
}"""


def patch_payment_js() -> None:
    """
    Перезаписать ``payment.js`` исправленной версией.

    Новая версия корректно обрабатывает ответы API оплаты
    и содержит метод генерации номера счёта.
    """
    path: str = _get_frontend_path("static", "frontend", "assets", "js", "payment.js")
    with open(path, "w", encoding="utf-8") as f:
        f.write(PAYMENT_JS_CODE)
    print(f"OK: patched {path}")


# ═══════════════════════════════════════════════
# Шаг 2. Добавление кнопки генерации в payment.html
# ═══════════════════════════════════════════════

#: HTML-разметка кнопки «Сгенерировать случайный счёт».
#: Кнопка скрыта по умолчанию (``display: none``), становится видимой
#: через ``mounted()`` в payment.js при ``?type=someone`` в URL.
GENERATE_BUTTON_HTML: str = """</label>
              <button type="button"
                      id="generateBtn"
                      class="btn btn_secondary"
                      @click="generateNumber"
                      style="margin-top: 8px; display: none;">
                Сгенерировать случайный счёт
              </button>
            </div>
            <div class="form-group ">
              <label for="month\""""


def patch_payment_html() -> None:
    """
    Добавить кнопку генерации номера счёта в шаблон ``payment.html``.

    Кнопка вставляется между полем ввода номера карты и полем месяца.
    Если кнопка уже присутствует — пропускает.
    Пробует два варианта паттерна для совместимости с разными версиями шаблона.
    """
    tpl_path: str = _get_frontend_path("templates", "frontend", "payment.html")
    with open(tpl_path, encoding="utf-8") as f:
        tpl: str = f.read()

    if "generateBtn" in tpl:
        print("OK: payment.html already has generateBtn")
        return

    # Основной паттерн: конец label + начало div с month
    old_label_end: str = (
        "</label>\n            </div>\n"
        '            <div class="form-group ">\n'
        '              <label for="month"'
    )

    if old_label_end in tpl:
        tpl = tpl.replace(old_label_end, GENERATE_BUTTON_HTML)
        with open(tpl_path, "w", encoding="utf-8") as f:
            f.write(tpl)
        print(f"OK: patched {tpl_path}")
        return

    # Альтернативный паттерн (другой отступ или структура)
    print("WARNING: could not find label pattern in payment.html")
    print("Trying alternative pattern...")

    alt_old: str = '            <div class="form-group ">\n' '              <label for="month"'

    if alt_old in tpl:
        alt_new: str = (
            '            <div class="form-group">\n'
            '              <button type="button"\n'
            '                      id="generateBtn"\n'
            '                      class="btn btn_secondary"\n'
            '                      @click="generateNumber"\n'
            '                      style="margin-top: 8px; display: none;">\n'
            "                Сгенерировать случайный счёт\n"
            "              </button>\n"
            "            </div>\n"
            '            <div class="form-group ">\n'
            '              <label for="month"'
        )
        tpl = tpl.replace(alt_old, alt_new, 1)
        with open(tpl_path, "w", encoding="utf-8") as f:
            f.write(tpl)
        print(f"OK: patched {tpl_path} (alt)")
    else:
        print("ERROR: could not patch payment.html - add button manually")


# ═══════════════════════════════════════════════
# Шаг 3. Передача типа оплаты через URL в order-detail.js
# ═══════════════════════════════════════════════


def patch_order_detail_js() -> None:
    """
    Изменить редирект в ``order-detail.js``, чтобы тип оплаты
    передавался через URL-параметр ``?type=``.

    Было::

        location.replace(`/payment/${orderId}/`)

    Стало::

        location.replace('/payment/' + orderId + '/?type=' + this.paymentType)

    Это позволяет ``payment.js`` в ``mounted()`` определить,
    нужно ли показывать кнопку генерации номера счёта.
    """
    od_path: str = _get_frontend_path("static", "frontend", "assets", "js", "order-detail.js")
    with open(od_path, encoding="utf-8") as f:
        od: str = f.read()

    if "payment-someone" in od or "paymentType" not in od:
        print("OK: order-detail.js already patched")
        return

    old_redirect: str = "location.replace(`/payment/${orderId}/`)"
    new_redirect: str = "location.replace('/payment/' + orderId + '/?type=' + this.paymentType)"

    if old_redirect in od:
        od = od.replace(old_redirect, new_redirect)
        with open(od_path, "w", encoding="utf-8") as f:
            f.write(od)
        print(f"OK: patched {od_path}")
    else:
        print("WARNING: redirect pattern not found in order-detail.js")


# ═══════════════════════════════════════════════
# Точка входа
# ═══════════════════════════════════════════════

if __name__ == "__main__":
    patch_payment_js()
    patch_payment_html()
    patch_order_detail_js()
