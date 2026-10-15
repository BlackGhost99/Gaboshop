"""Règle des mots de passe : assez longs et pas faciles à deviner (messages en français).

Vérifiée à l'inscription, au « mot de passe oublié » et quand un admin choisit un mot de passe.
Les comptes existants gardent leur mot de passe : la règle s'applique au prochain changement.
"""
import re

from django.contrib.auth.password_validation import CommonPasswordValidator
from django.core.exceptions import ValidationError

MIN_LENGTH = 8
RULE = f'Au moins {MIN_LENGTH} caractères, avec au moins une lettre et un chiffre.'
LOCAL_WORDS = {'gaboshop', 'motdepasse', 'azerty', 'qwerty', 'libreville', 'gabon', 'airtel', 'moov', 'bonjour'}


def _simple_run(text):
    """Un même caractère répété, ou une suite (123456789, abcdefgh, 987654…), sur au moins 4 caractères."""
    if len(text) < 4:
        return False
    if len(set(text)) <= 2:
        return True
    steps = {ord(b) - ord(a) for a, b in zip(text, text[1:])}
    return steps in ({1}, {-1})


def password_problem(password, phone=''):
    """Raison en français si le mot de passe est trop faible, sinon ''."""
    password = str(password or '')
    lowered = password.lower()
    if len(password) < MIN_LENGTH:
        return f'Mot de passe trop court : {RULE}'
    if not re.search(r'[^\W\d_]', password) or not re.search(r'\d', password):
        return f'Mot de passe trop facile : {RULE}'
    if _simple_run(lowered) or _simple_run(re.sub(r'\d', '', lowered)) or _simple_run(re.sub(r'\D', '', lowered)):
        return 'Mot de passe trop facile à deviner (suite ou répétition, comme « abcd1234 »). Choisissez un mélange.'
    if re.sub(r'\d', '', lowered) in LOCAL_WORDS:
        return 'Mot de passe trop facile à deviner (mot courant). Choisissez un mélange de lettres et de chiffres.'
    digits = re.sub(r'\D', '', str(phone or ''))[-8:]
    if len(digits) >= 6 and digits[-6:] in password:
        return 'Le mot de passe ne doit pas contenir votre numéro de téléphone.'
    try:
        CommonPasswordValidator().validate(password)
    except ValidationError:
        return 'Ce mot de passe fait partie des plus utilisés au monde. Choisissez-en un autre.'
    return ''
