# chatbot/models.py
import uuid
import random
import string
from datetime import datetime, timedelta
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None):
        if not email:
            raise ValueError('Users must have an email address')
        email = self.normalize_email(email)
        user = self.model(email=email, name=name)
        user.set_password(password)
        user.save(using=self._db)
        return user

class User(AbstractBaseUser):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.email

# chatbot/models.py (update the is_valid method)
from django.utils import timezone  # Add this import at the top

class OTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def generate_code(self):
        self.code = ''.join(random.choices(string.digits, k=6))
        self.save()
        return self.code
    
    def is_valid(self):
        # Fix: Use timezone.now() instead of datetime.now()
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=10)

class ChatSession(models.Model):
    STEP_CHOICES = [
        ('greeting', 'Greeting'),
        ('name', 'Name'),
        ('email', 'Email'),
        ('otp', 'OTP'),
        ('verified', 'Verified'),
    ]
    
    session_id = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    step = models.CharField(max_length=20, choices=STEP_CHOICES, default='greeting')
    temp_data = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Session {self.session_id} - {self.step}"