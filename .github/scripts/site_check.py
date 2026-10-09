"""Vérifie que les sites Gaboshop (production et test) répondent, depuis GitHub Actions.

Écrit un rapport Markdown sur la sortie standard. Aucune donnée secrète : uniquement
des pages publiques. Lancé par .github/workflows/site-check.yml.
"""
import json
import re
import time
import urllib.error
import urllib.request

SITES = [
    {
        'name': 'Production',
        'api': 'https://gaboshop-api.onrender.com',
        'web': 'https://gaboshop-web-welf.onrender.com',
    },
    {
        'name': 'Test (staging)',
        'api': 'https://gaboshop-api-staging-uvn1.onrender.com',
        'web': 'https://gaboshop-web-staging-uvn1.onrender.com',
    },
]


# Textes présents dans le site web une fois une correction déployée (le site est un seul gros fichier JS).
MARKERS = {
    'Correction « commandes qui clignotent » (8 oct.)': 'Le serveur ne répond pas pour le moment',
    'Paiement en ligne SingPay (carte de suivi client)': "J'ai validé, vérifier",
    'SingPay : opérateur vérifié selon le numéro': 'choisissez Moov Money',
    'Versements : numéro Mobile Money du commerce': 'Recevoir vos ventes payées en ligne',
    'Texte du choix de paiement selon le mode (8 oct. soir)': 'après la commande, vous recevez une demande',
    'Relancer un paiement sur la même commande (9 oct.)': 'Demande expirée ou pas reçue',
}


def fetch(url, origin=None, attempts=2, max_bytes=400_000):
    """GET avec réveil des services gratuits Render (jusqu'à ~2 min la première fois)."""
    headers = {'User-Agent': 'gaboshop-site-check'}
    if origin:
        headers['Origin'] = origin
    last = None
    for _ in range(attempts):
        start = time.time()
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=150) as res:
                body = res.read(max_bytes)
                return {'status': res.status, 'seconds': round(time.time() - start, 1), 'headers': dict(res.headers), 'body': body}
        except urllib.error.HTTPError as err:
            last = {'status': err.code, 'seconds': round(time.time() - start, 1), 'headers': dict(err.headers or {}), 'body': err.read(2000)}
            if err.code < 500:
                return last
        except Exception as err:  # délai dépassé, DNS, connexion refusée…
            last = {'status': f'erreur ({type(err).__name__}: {err})', 'seconds': round(time.time() - start, 1), 'headers': {}, 'body': b''}
        time.sleep(5)
    return last


def short(body, limit=220):
    text = body.decode('utf-8', 'replace').replace('\n', ' ').strip()
    return (text[:limit] + '…') if len(text) > limit else text


def check(site):
    lines = [f"## {site['name']}"]
    api, web = site['api'], site['web']

    res = fetch(f'{api}/api/v1/stores/', origin=web)
    cors = res['headers'].get('Access-Control-Allow-Origin') or res['headers'].get('access-control-allow-origin') or 'absent'
    count = ''
    try:
        data = json.loads(res['body'])
        items = data.get('data') if isinstance(data, dict) else data
        if isinstance(items, dict):
            items = items.get('results', [])
        if isinstance(items, list):
            count = f', {len(items)} magasin(s) renvoyé(s)'
    except Exception:
        pass
    lines.append(f"- API magasins : **{res['status']}** en {res['seconds']} s{count}")
    lines.append(f"- Autorisation CORS pour {web} : `{cors}`")
    if res['status'] != 200:
        lines.append(f"  - Réponse : `{short(res['body'])}`")

    res = fetch(f'{api}/api/v1/ai/assistant/status/')
    if res['status'] == 200:
        try:
            data = json.loads(res['body']).get('data', {})
            lines.append(f"- Assistant IA : fournisseur `{data.get('provider')}`, clé présente : `{data.get('key_present')}`")
        except Exception:
            lines.append(f"- Assistant IA : `{short(res['body'])}`")
    else:
        lines.append(f"- Assistant IA : **{res['status']}**")

    res = fetch(f'{web}/')
    lines.append(f"- Site web : **{res['status']}** en {res['seconds']} s")
    if res['status'] == 200:
        scripts = re.findall(rb'src="(/assets/[^"]+\.js)"', res['body'])
        if scripts:
            js = fetch(web + scripts[0].decode(), attempts=1, max_bytes=20_000_000)
            lines.append(f"- Fichier du site : `{scripts[0].decode()}`")
            for label, text in MARKERS.items():
                present = text.encode() in (js['body'] or b'')
                lines.append(f"- {label} : {'présente' if present else 'ABSENTE'}")
            apis = sorted(set(re.findall(rb'https://[a-z0-9.-]*onrender\.com', js['body'] or b'')))
            found = ', '.join(a.decode() for a in apis) or 'aucune adresse onrender.com trouvée'
            verdict = 'OK' if api.encode() in apis else 'ATTENTION : ce site ne vise pas cette API'
            lines.append(f"- API visée par le site : {found} → {verdict}")
    return lines


def main():
    report = [f"Vérification du {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}", '']
    for site in SITES:
        report += check(site) + ['']
    print('\n'.join(report))


if __name__ == '__main__':
    main()
