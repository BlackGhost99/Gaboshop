import os
import requests

BASE = 'http://localhost:8000'
login_url = BASE + '/api/v1/auth/login/'
profile_url = BASE + '/api/v1/auth/profile/'

payload = {'phone': '+241970000001', 'password': 'TestPass123'}

resp = requests.post(login_url, json=payload)
print('LOGIN STATUS', resp.status_code)
try:
    data = resp.json()
except Exception:
    print('LOGIN RESPONSE', resp.text)
    raise

print('LOGIN JSON:', data)

if data.get('success'):
    access = data['data']['tokens']['access']
    headers = {'Authorization': f'Bearer {access}'}
    r = requests.get(profile_url, headers=headers)
    print('PROFILE STATUS', r.status_code)
    try:
        print('PROFILE JSON:', r.json())
    except Exception:
        print('PROFILE TEXT:', r.text)
else:
    print('Login failed; cannot call profile')
