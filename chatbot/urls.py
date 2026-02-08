# chatbot/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('api/chat/', views.chat_api, name='chat_api'),
    path('api/resend-otp/', views.resend_otp, name='resend_otp'),
]