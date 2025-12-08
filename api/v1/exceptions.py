from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        customized_response = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': response.data.get('detail', 'Une erreur est survenue.'),
                'details': response.data
            }
        }
        response.data = customized_response
    
    return response
