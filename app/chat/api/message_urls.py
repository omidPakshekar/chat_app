from django.urls import path, include

from .views import *




urlpatterns = [
	path('delete/', DeleteMessageView.as_view()),

]