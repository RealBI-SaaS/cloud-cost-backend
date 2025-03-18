from django.shortcuts import render, redirect
from django.http import JsonResponse
from dotenv import load_dotenv
import requests
import os
from .models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from urllib.parse import urlencode
from rest_framework.views import APIView
from rest_framework.status import HTTP_201_CREATED, HTTP_400_BAD_REQUEST
from .serializers import UserSerializer
from django.contrib.auth import get_user_model

load_dotenv()

# Create your views here.

def api_documentation(request):
    return render(request, "index.html")

def google_oauth_callback(request):
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
            defaults={
                'first_name': user_data.get('given_name', ''),
                'last_name': user_data.get('family_name', ''),
                'is_google_user': True,
                'role': 'member'
            }
        )

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = str(refresh.access_token)
        refresh_token = str(refresh)

        # Create redirect URL with tokens as parameters
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173/home')
        params = {
            'access_token': access_token,
            'refresh_token': refresh_token
        }
        redirect_url = f"{frontend_url}?{urlencode(params)}"
        
        return redirect(redirect_url)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

# @api_view(["POST"])
# def create_user(request):
#     try:
#         email = request.data.get('email')
#         password = request.data.get('password')


#         if not email or not password:
#             return Response({'error': 'Email and password are required'}, status=400)

#         # Check if user already exists
#         if User.objects.filter(email=email).exists():
#             return Response({'error': 'User with this email already exists'}, status=400)

#         # Create new user
#         user = User.objects.create(
#             email=email,
#             # username=email,  # Using email as username            
#             is_google_user=False,
#             role='member'
#         )
#         user.set_password(password)
#         user.save()

#         # Generate JWT tokens
#         refresh = RefreshToken.for_user(user)
#         access_token = str(refresh.access_token)
#         refresh_token = str(refresh)

#         return Response({
#             'access_token': access_token,
#             'refresh_token': refresh_token,
#             # 'user': {
#             #     'userId': str(user.id),
#             #     'email': user.email,
#             #     'firstName': user.first_name,
#             #     'lastName': user.last_name,
#             #     'role': user.role
#             # }
#         })

#     except Exception as e:
#         return Response({'error': str(e)}, status=500)


class RegisterView(APIView):
    http_method_names = ['post']

    def post(self, *args, **kwargs):
        serializer = UserSerializer(data=self.request.data)
        if serializer.is_valid():
            data = serializer.validated_data
            user = get_user_model().objects.create(**data)
            user.set_password(data['password'])
            user.save()
            
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            return Response({
                'access_token': access_token,
                'refresh_token': refresh_token
            }, status=HTTP_201_CREATED)
        return Response(status=HTTP_400_BAD_REQUEST, data={'errors': serializer.errors})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_user(request):
    try:
        user = request.user
        return Response({
            "userId": str(user.id),
            "email": user.email,
            "firstName": user.first_name,
            "lastName": user.last_name,
            "role": user.role,
            "isGoogleUser": user.is_google_user
        })
    except Exception as e:
        return Response({"error": str(e)}, status=500)