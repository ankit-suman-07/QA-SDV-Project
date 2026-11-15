"""Redact authentication before durable evidence; normalize log whitespace only."""
import base64
import re
from urllib.parse import quote


def sanitize_text(text, username, password):
    if username and password:
        pair = username + ':' + password
        for value in (base64.b64encode(pair.encode()).decode(), pair, quote(pair, safe='')):
            text = text.replace(value, '[REDACTED]')
        # Long passwords are safe to remove verbatim. Short sample passwords may
        # equal component names; redact them only in explicit credential fields.
        if len(password) >= 8:
            text = text.replace(password, '[REDACTED]')
    text = re.sub(r'(?i)(authorization[\s\W]{0,8}(?:Basic|Bearer)\s+)[A-Za-z0-9+/_=.\-]+',
                  r'\1[REDACTED]', text)
    text = re.sub(r'(?i)((?:password|passwd|client_secret)[\s\W]{1,8})[^\s,;"\'}]+',
                  r'\1[REDACTED]', text)
    return '\n'.join(line.rstrip() for line in text.splitlines()).rstrip() + '\n'
