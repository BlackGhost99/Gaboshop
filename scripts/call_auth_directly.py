from rest_framework.test import APIClient
from users.models import DeliveryAgentApiKey
from users.authentication import ApiKeyAuthentication
from rest_framework.request import Request

api = DeliveryAgentApiKey.objects.first()
client = APIClient()
client.credentials(HTTP_AUTHORIZATION='ApiKey ' + api.key)
resp = client.get('/api/v1/dashboard/delivery/available/')
req = resp.wsgi_request
print('STATUS', resp.status_code)
print('WSGI_HTTP_AUTH', req.META.get('HTTP_AUTHORIZATION'))

drf_req = Request(req)
print('DRF_REQUEST_META', drf_req.META.get('HTTP_AUTHORIZATION'))

auth = ApiKeyAuthentication()
try:
    result = auth.authenticate(drf_req)
    print('AUTH_RESULT', result)
except Exception as e:
    print('AUTH_EXCEPTION', e)
