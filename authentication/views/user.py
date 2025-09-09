from django.contrib.auth import get_user_model
from django.shortcuts import render
from dotenv import load_dotenv
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

User = get_user_model()
from authentication.serializers import UserSerializer

load_dotenv()
#
# # Environment variables
# GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
# GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
# GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
# SUCCESS_REDIRECT_URL = os.getenv("GOOGLE_SUCCESS_REDIRECT_URL")
# LOGIN_FROM_REDIRECT_URL = os.getenv("GOOGLE_LOGIN_FROM_REDIRECT_URL")
#


def api_documentation(request):
    return render(request, "index.html")


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """Return the logged-in user"""
        return self.request.user
