"""Write JSON the way Delta Manager does (JavaScript JSON.stringify with 2 spaces).

Python writes some numbers differently (7.5e-05 instead of 0.000075). Writing like the game
keeps every line we do not change byte-identical, so a diff of the save shows only the update.
"""
import json
from decimal import Decimal


def js_number(x):
    if isinstance(x, bool):
        return 'true' if x else 'false'
    if isinstance(x, int):
        return str(x)
    if x != x or x in (float('inf'), float('-inf')):
        return 'null'  # what JSON.stringify writes for NaN / Infinity
    r = repr(x)
    if r.endswith('.0'):
        r = r[:-2]
    if 'e' not in r:
        return r
    exp = int(r.split('e')[1])
    if -7 < exp < 21:  # JavaScript writes these without an exponent
        text = format(Decimal(r), 'f')
        if '.' in text:
            text = text.rstrip('0').rstrip('.')
        return text
    mant, e = r.split('e')
    e = int(e)
    return '%se%s%d' % (mant, '+' if e > 0 else '-', abs(e))


def dumps(obj, indent=2, level=0):
    if obj is None:
        return 'null'
    if isinstance(obj, (bool, int, float)):
        return js_number(obj)
    if isinstance(obj, str):
        return json.dumps(obj, ensure_ascii=False)
    pad = ' ' * (indent * (level + 1))
    end = ' ' * (indent * level)
    if isinstance(obj, dict):
        if not obj:
            return '{}'
        items = ('%s%s: %s' % (pad, json.dumps(str(k), ensure_ascii=False), dumps(v, indent, level + 1))
                 for k, v in obj.items())
        return '{\n' + ',\n'.join(items) + '\n' + end + '}'
    if isinstance(obj, (list, tuple)):
        if not obj:
            return '[]'
        return '[\n' + ',\n'.join(pad + dumps(v, indent, level + 1) for v in obj) + '\n' + end + ']'
    raise TypeError('cannot write %r' % type(obj))


def detect_indent(text):
    """2 for the game's indented saves, 0 for a compact file."""
    if text.startswith('{\n') or text.startswith('[\n'):
        line = text.split('\n', 2)[1]
        return len(line) - len(line.lstrip(' ')) or 2
    return 0


def dumps_like(obj, original_text):
    indent = detect_indent(original_text)
    if indent:
        return dumps(obj, indent)
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
