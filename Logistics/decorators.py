from Logistics.auth import decode_jwt_token
from functools import wraps
from django.http import JsonResponse

def jwt_auth_required(view_func):
    @wraps(view_func)
    def wrapped_view(root, info, *args, **kwargs):
        request = info.context
        token = request.META.get('HTTP_AUTHORIZATION')
        if not token:
            return JsonResponse({'error': 'Token is missing'}, status=403)

        user_id = decode_jwt_token(token)
        if user_id is None:
            return JsonResponse({'error': 'Invalid or expired token'}, status=403)
        setattr(request, 'user_id', user_id)
        return view_func(root, info, *args, **kwargs)
    return wrapped_view