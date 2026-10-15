"""Faux SingPay pour le site de test (PAYMENTS_SIMULATED=1) : aucun appel réseau, aucun argent réel.

Il répond à la place de l'API SingPay, avec les mêmes formes de réponse, pour que tout le reste du code
(lancement, vérification du statut, confirmation de commande, abonnements, forfaits, mise en avant,
versements) tourne exactement comme en production.

Règles du faux paiement :
- le paiement est « en attente » pendant SIMULATED_DELAY_SECONDS (le temps de taper son code secret),
  puis réussi ;
- un numéro qui paie se terminant par 99 est refusé (solde insuffisant), pour tester un échec.

Sans état : le montant, la référence, l'heure et l'issue sont inscrits dans l'identifiant de transaction.
"""
import base64
import json
import re
import time

SIMULATED_DELAY_SECONDS = 8
ID_PREFIX = 'SIM'
REFUSED_SUFFIX = '99'


def _encode(data):
    raw = json.dumps(data, separators=(',', ':')).encode()
    return ID_PREFIX + base64.urlsafe_b64encode(raw).decode().rstrip('=')


def _decode(tx_id):
    tx_id = str(tx_id or '')
    if not tx_id.startswith(ID_PREFIX):
        return None
    body = tx_id[len(ID_PREFIX):]
    try:
        return json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
    except (ValueError, TypeError):
        return None


def _payment(payload):
    payload = payload or {}
    phone = str(payload.get('client_msisdn') or '')
    tx_id = _encode({
        'a': payload.get('amount'), 'r': payload.get('reference'), 't': int(time.time()),
        'ko': phone.endswith(REFUSED_SUFFIX),
    })
    return {
        'status': {'success': True, 'code': '200', 'message': 'Paiement simulé (site de test)'},
        'transaction': {'id': tx_id, 'reference': payload.get('reference'), 'amount': payload.get('amount'),
                        'status': 'Start', 'result': ''},
    }


def _status(tx_id):
    data = _decode(tx_id)
    if data is None:
        return {'error': 'SingPay HTTP 404', 'response': {'message': 'Transaction inconnue (simulation)'}}
    transaction = {'id': tx_id, 'reference': data.get('r'), 'amount': data.get('a')}
    if time.time() - data.get('t', 0) < SIMULATED_DELAY_SECONDS:
        transaction.update(status='Start', result='')
    elif data.get('ko'):
        transaction.update(status='Terminate', result='BalanceError')
    else:
        transaction.update(status='Terminate', result='Success')
    return {'transaction': transaction}


def handle(method, path, payload=None):
    """Réponse simulée pour un appel ``_singpay_request``."""
    method = (method or '').upper()
    if method == 'POST' and re.fullmatch(r'/(74|62|maviance)/paiement', path):
        return _payment(payload)
    if method == 'POST' and path == '/transfer':
        payload = payload or {}
        return {'status': {'success': True, 'code': '200', 'message': 'Versement simulé (site de test)'},
                'transaction_id': f"SIMT-{payload.get('reference')}", 'amount': payload.get('amount')}
    match = re.fullmatch(r'/transaction/api/(?:status/)?([^/]+)', path)
    if method == 'GET' and match and not path.startswith('/transaction/api/search/'):
        return _status(match.group(1))
    if method == 'GET' and path.startswith('/transaction/api/search/'):
        return {'transactions': []}
    if method == 'GET' and path.startswith('/transfer/transaction/'):
        return {'error': 'SingPay HTTP 404', 'response': {'message': 'Aucun transfert (simulation)'}}
    return {'error': f'Appel SingPay non simulé : {method} {path}'}
