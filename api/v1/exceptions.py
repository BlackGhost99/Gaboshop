from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    
    if response is not None:
        data = response.data
        if isinstance(data, dict):
            message = data.get('detail') or _first_message(data) or 'Une erreur est survenue.'
        else:
            # ValidationError('texte') donne une liste : on la garde lisible au lieu de planter.
            message = _first_message(data) or 'Une erreur est survenue.'
        customized_response = {
            'success': False,
            'error': {
                'code': response.status_code,
                'message': str(message),
                'details': data
            }
        }
        response.data = customized_response
    
    return response


def _first_message(value):
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _first_message(item)
            if found:
                return found
        return ''
    if isinstance(value, dict):
        for item in value.values():
            found = _first_message(item)
            if found:
                return found
        return ''
    return str(value) if value else ''
