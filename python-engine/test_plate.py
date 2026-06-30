import re
# Test the new plate regex
pat = re.compile(
    r'\b(?:'
    r'[A-Z]{2}\s*\d{2}\s*[A-Z]{1,3}\s*\d{1,4}'  # standard: MH12AB1234
    r'|(?:\d{1,2}\s*)?BH\s*\d{2,4}\s*[A-Z]{1,2}' # BH series
    r')\b',
    re.ASCII
)
tests = [
    '22BH6517A IND',
    'BH6517A',
    'MH12AB1234',
    'KA01AB1234',
    '22BH6517A',
    'IND 22BH6517A',
    'number is BH6517A hello',
]
for t in tests:
    m = pat.search(t)
    val = m.group(0) if m else None
    print(repr(t), '->', repr(val))
