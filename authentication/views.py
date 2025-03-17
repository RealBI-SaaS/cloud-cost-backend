from django.shortcuts import render
from django.http import JsonResponse
from dotenv import load_dotenv
import requests
import os
from .models import User

load_dotenv()

# Create your views here.

def api_documentation(request):
    return render(request, "index.html")

def google_oauth_callback(request):
    # print(request.GET)
    code = request.GET.get('code')
    if not code:
        return JsonResponse({'error': 'Authorization code not provided'}, status=400)

    try:
        # Exchange auth code for tokens
        token_endpoint = 'https://oauth2.googleapis.com/token'
        data = {
            'code': code,
            'client_id': os.getenv('GOOGLE_CLIENT_ID'),
            'client_secret': os.getenv('GOOGLE_CLIENT_SECRET'), 
            'redirect_uri': os.getenv('GOOGLE_REDIRECT_URI'),
            'grant_type': 'authorization_code'
        }
       
        
        response = requests.post(token_endpoint, data=data)
        tokens = response.json()

        if response.status_code != 200:
            return JsonResponse({'error': 'Failed to exchange auth code', 'response': response.json()}, status=400)

        # Get user info from Google
        access_token = tokens['access_token']
        userinfo_endpoint = 'https://www.googleapis.com/oauth2/v2/userinfo'
        headers = {'Authorization': f'Bearer {access_token}'}
        
        userinfo_response = requests.get(userinfo_endpoint, headers=headers)
        user_data = userinfo_response.json()

        # Get or create user
        user, created = User.objects.get_or_create(
            email=user_data['email'],
            first_name=user_data['given_name'],
            last_name=user_data['family_name'],
            is_google_user=True,
            defaults={
                'role': 'member'
            }
        )


        return JsonResponse({
            'user_id': str(user.id),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'is_google_user': user.is_google_user,
            'role': user.role
        })

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
