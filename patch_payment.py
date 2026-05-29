"""
Patch payment.js:
1. On error: show alert and stay on payment page
2. On success: show alert and redirect to home
3. Add generateNumber method for 'random account' button

Usage: python patch_payment.py
"""
import frontend
import os

path = os.path.join(
    os.path.dirname(frontend.__file__),
    'static/frontend/assets/js/payment.js'
)

with open(path) as f:
    code = f.read()

# ── Step 1: Replace entire payment.js with corrected version ──
new_code = """var mix = {
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
\t\tvar btn = document.getElementById('generateBtn')
\t\tif (btn) btn.style.display = 'inline-block'
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

with open(path, 'w') as f:
    f.write(new_code)
print(f"OK: patched {path}")

# ── Step 2: Add generate button to payment.html ──
tpl_path = os.path.join(
    os.path.dirname(frontend.__file__),
    'templates/frontend/payment.html'
)

with open(tpl_path, encoding="utf-8") as f:
    tpl = f.read()

if 'generateBtn' not in tpl:
    # Add button after the number input label
    old_label_end = '</label>\n            </div>\n            <div class="form-group ">\n              <label for="month"'
    new_label_end = """</label>
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

    if old_label_end in tpl:
        tpl = tpl.replace(old_label_end, new_label_end)
        with open(tpl_path, 'w') as f:
            f.write(tpl)
        print(f"OK: patched {tpl_path}")
    else:
        print("WARNING: could not find label pattern in payment.html")
        print("Trying alternative pattern...")
        # Try finding just the month label
        alt_old = '            <div class="form-group ">\n              <label for="month"'
        if alt_old in tpl:
            alt_new = """            <div class="form-group">
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
            tpl = tpl.replace(alt_old, alt_new, 1)
            with open(tpl_path, 'w') as f:
                f.write(tpl)
            print(f"OK: patched {tpl_path} (alt)")
        else:
            print("ERROR: could not patch payment.html - add button manually")
else:
    print("OK: payment.html already has generateBtn")

# ── Step 3: Patch order-detail.js to show button for 'someone' payment ──
od_path = os.path.join(
    os.path.dirname(frontend.__file__),
    'static/frontend/assets/js/order-detail.js'
)

with open(od_path) as f:
    od = f.read()

if 'payment-someone' not in od and 'paymentType' in od:
    # Change redirect: if someone -> add query param so payment page knows
    old_redirect = "location.replace(`/payment/${orderId}/`)"
    new_redirect = """location.replace('/payment/' + orderId + '/?type=' + this.paymentType)"""
    if old_redirect in od:
        od = od.replace(old_redirect, new_redirect)
        with open(od_path, 'w') as f:
            f.write(od)
        print(f"OK: patched {od_path}")
    else:
        print("WARNING: redirect pattern not found in order-detail.js")
else:
    print("OK: order-detail.js already patched")

# ── Step 4: Update payment.js mounted() to check URL param ──
# Already handled: mounted() shows button, but only if type=someone
with open(path) as f:
    code = f.read()

old_mounted = """mounted() {
\t\tvar btn = document.getElementById('generateBtn')
\t\tif (btn) btn.style.display = 'inline-block'
\t}"""

new_mounted = """mounted() {
\t\tvar params = new URLSearchParams(location.search)
\t\tvar type = params.get('type')
\t\tvar btn = document.getElementById('generateBtn')
\t\tif (btn && type === 'someone') {
\t\t\tbtn.style.display = 'inline-block'
\t\t}
\t}"""

if old_mounted in code:
    code = code.replace(old_mounted, new_mounted)
    with open(path, 'w') as f:
        f.write(code)
    print(f"OK: updated mounted() in {path}")
