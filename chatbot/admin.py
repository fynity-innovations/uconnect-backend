# chatbot/admin.py
from django.contrib import admin
from .models import User, OTP, ChatSession

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'is_verified', 'created_at']
    list_filter = ['is_verified', 'created_at']
    search_fields = ['email', 'name']

@admin.register(OTP)
class OTPAdmin(admin.ModelAdmin):
    list_display = ['user', 'code', 'is_used', 'created_at']
    list_filter = ['is_used', 'created_at']

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['session_id', 'user', 'step', 'created_at']
    list_filter = ['step', 'created_at']