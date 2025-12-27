from rest_framework.test import APIClient
from users.models import DeliveryAgentApiKey

# pick one created key
api = DeliveryAgentApiKey.objects.first()
if not api:
    print('NO_API_KEY')
else:
    key = api.key
    user_id = api.user_id
    print('USING_API_KEY', user_id, key)
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION='ApiKey ' + key)
    resp = client.get('/api/v1/dashboard/delivery/available/')
    print('STATUS', resp.status_code)
    try:
        print('DATA', resp.json())
    except Exception as e:
        print('NO JSON:', e)
