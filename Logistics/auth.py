import jwt
from django.conf import settings
from datetime import datetime, timedelta
from django.contrib.auth import authenticate
from django.http import JsonResponse
import json


def generate_jwt_token(user_id):
    payload = {
        'user_id': user_id,
        'exp': datetime.utcnow() + timedelta(seconds=settings.JWT_EXPIRATION_SECONDS)
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_jwt_token(token):
    try:
        payload = jwt.decode(token.replace("Bearer ",""), settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload['user_id']
    except jwt.ExpiredSignatureError:
        # Handle token expiration
        return None
    except jwt.InvalidTokenError:
        # Handle invalid token
        return None


def login(request):
    if request.method == 'POST':
        # Get the JSON payload from the request body
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON payload'}, status=400)

        # Extract username and password from the JSON payload
        username = data.get('username')
        password = data.get('password')

        # Perform authentication and generate JWT token
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # Authentication successful, generate JWT token
                token = generate_jwt_token(user.id)
                return JsonResponse({'token': token})
            else:
                # Authentication failed
                return JsonResponse({'error': 'Invalid credentials'}, status=401)
        else:
            return JsonResponse({'error': 'Username and/or password missing'}, status=400)
    else:
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)