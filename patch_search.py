"""Patch catalog.js to read search filter from URL params."""
import frontend
import os

path = os.path.join(os.path.dirname(frontend.__file__),
                    'static/frontend/assets/js/catalog.js')

with open(path) as f:
    code = f.read()

# Find and patch the mounted() section
old = "this.getCatalogs()\n        this.getTags()"
new = """const urlParams = new URLSearchParams(location.search)
        const searchFilter = urlParams.get('filter')
        if (searchFilter) {
            this.filter.name = searchFilter
        }
        this.getCatalogs()
        this.getTags()"""

# Only replace the LAST occurrence (the one in mounted())
idx = code.rfind(old)
if idx != -1:
    code = code[:idx] + new + code[idx + len(old):]
    with open(path, 'w') as f:
        f.write(code)
    print(f"OK: patched {path}")
    print(f"urlParams count: {code.count('urlParams')}")
else:
    print("ERROR: pattern not found")
