import re

INVALID_MESSAGE = 'Numéro Mobile Money invalide : un numéro Airtel (074, 076, 077) ou Moov (060, 062, 065, 066).'


def normalize_mobile_money(value):
    """Retourne le numéro au format +241XXXXXXXX, '' si vide ; ValueError s'il n'est ni Airtel ni Moov."""
    digits = re.sub(r'\D', '', value or '')
    if not digits:
        return ''
    if len(digits) == 11 and digits.startswith('241'):
        digits = digits[3:]
    if len(digits) == 8:
        digits = '0' + digits
    if not re.fullmatch(r'0[67]\d{7}', digits):
        raise ValueError(INVALID_MESSAGE)
    return '+241' + digits[1:]
