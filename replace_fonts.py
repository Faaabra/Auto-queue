import re
with open('main.py', 'r', encoding='utf-8') as f:
    src = f.read()

src = re.sub(r'family=[\'\"]Segoe UI[\'\"]', 'family=UI_FONT', src)
src = re.sub(r'font=\([\'\"]Segoe UI[\'\"]', 'font=(UI_FONT', src)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print("done")
