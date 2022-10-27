import json, jwt, os

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import  Response
from rest_framework import generics, status, views, permissions, viewsets
from dj_rest_auth.views import LoginView as dj_Login

from accounts.models import CustomUser

from .serializers import CustomJWTSerializer, SearchUsernameSerializer, UserInlineSerializer


class CustomUserLogin(dj_Login):
    def get_response_serializer(self):
        return CustomJWTSerializer

class SearchUsername(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    queryset = CustomUser.objects.all()
    serializer_class = SearchUsernameSerializer
    def post(self, request, *args, **kwargs):
        return Response(UserInlineSerializer(instance=self.queryset.filter(username__contains=request.data['username']), many=True).data)

