from rest_framework.test import APIClient
from users.models import DeliveryAgentApiKey

api = DeliveryAgentApiKey.objects.first()
if not api:
    print('NO_API_KEY')
else:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='ApiKey ' + api.key)
    resp = client.get('/api/v1/dashboard/delivery/available/')
    print('STATUS', resp.status_code)
    req = getattr(resp, 'wsgi_request', None)
    if req:
        print('WSGI_HTTP_AUTH', req.META.get('HTTP_AUTHORIZATION'))
        print('WSGI_AUTHORIZATION', req.META.get('Authorization'))
        print('HEADERS_SAMPLE', {k: req.META[k] for k in ['REQUEST_METHOD','PATH_INFO'] if k in req.META})
    else:
        print('no wsgi_request')
