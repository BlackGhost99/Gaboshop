"""Tailles/pointures et couleurs d'un produit : listes propres, choisies par le client au panier."""
import re

_SEPARATORS = re.compile(r'[,;/|\n]+')
_NUMBER = re.compile(r'^\d+(?:[.,]5)?$')


def split_values(text):
    """« 40 41 42 », « 40,41;42 » ou « S / M / L » donnent ['40', '41', '42'] ou ['S', 'M', 'L'].
    Un libellé de plusieurs mots (« Taille unique ») reste entier ; doublons retirés, ordre gardé."""
    values = []
    for part in _SEPARATORS.split(str(text or '')):
        part = part.strip()
        if not part:
            continue
        words = part.split()
        if len(words) > 1 and all(_NUMBER.match(w) or len(w) <= 4 and w.isupper() for w in words):
            values.extend(words)
        else:
            values.append(part)
    seen, unique = set(), []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            unique.append(value[:20])
    return unique[:40]


def join_values(text):
    return ', '.join(split_values(text))


def product_options(product):
    attrs = getattr(product, 'attributes', None) or {}
    return {'size': split_values(attrs.get('sizes')), 'color': split_values(attrs.get('color'))}


def clean_choice(product, chosen):
    """Choix du client validé contre les listes du produit. Une seule valeur possible : prise d'office.
    Lève ValueError avec un message clair si un choix manque ou n'existe pas."""
    chosen = chosen if isinstance(chosen, dict) else {}
    labels = {'size': 'la taille / pointure', 'color': 'la couleur'}
    result = {}
    for key, values in product_options(product).items():
        if not values:
            continue
        value = str(chosen.get(key) or '').strip()
        if not value and len(values) == 1:
            value = values[0]
        if not value:
            raise ValueError(f"Choisissez {labels[key]} de « {product.name} » : {', '.join(values)}.")
        match = next((v for v in values if v.lower() == value.lower()), None)
        if match is None:
            raise ValueError(f"{labels[key].capitalize()} « {value} » n'existe pas pour « {product.name} ». "
                             f"Choix possibles : {', '.join(values)}.")
        result[key] = match
    return result


def describe(options):
    parts = []
    if (options or {}).get('size'):
        parts.append(f"Taille {options['size']}")
    if (options or {}).get('color'):
        parts.append(options['color'])
    return ' · '.join(parts)
