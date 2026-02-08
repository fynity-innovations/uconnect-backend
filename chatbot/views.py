# chatbot/views.py (completely fixed version)
import traceback
import uuid
import random
import string
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
import json
from .models import User, OTP, ChatSession

@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    try:
        data = json.loads(request.body)
        message = data.get('message', '').strip()
        session_id = data.get('session_id', '')
        

        
        # Get or create session
        if session_id:
            try:
                session = ChatSession.objects.get(session_id=session_id)
                print(f"Found existing session: {session.session_id}, Step: {session.step}")
            except ChatSession.DoesNotExist:
                session = ChatSession.objects.create()
                print(f"Created new session: {session.session_id}")
        else:
            session = ChatSession.objects.create()
            print(f"Created new session: {session.session_id}")
        
        response = process_chat_message(session, message)
        
        result = {
            'reply': response['message'],
            'session_id': str(session.session_id),
            'step': session.step
        }
        
        if 'redirect_url' in response:
            result['redirect_url'] = response['redirect_url']
            result['button_text'] = response['button_text']

        return JsonResponse(result)
        
    except json.JSONDecodeError as e:
        return JsonResponse({'error': f'Invalid JSON: {str(e)}'}, status=400)
    except Exception as e:

        return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

# chatbot/views.py (updated to include program level)
def process_chat_message(session, message):
    """Process the chat message based on the current step in the session."""
    message_lower = message.lower().strip()
    
    if session.step == 'greeting':
        session.step = 'name'
        session.save()
        return {
            'message': "Hello! Welcome to StudyGlobal. To get started, could you please tell me your name?"
        }
    
    elif session.step == 'name':
        if len(message) < 2:
            return {
                'message': "Please enter a valid name (at least 2 characters)."
            }
        
        session.temp_data = {'name': message.title()}
        session.step = 'email'
        session.save()
        return {
            'message': f"Nice to meet you, {message.title()}! Now, could you please provide your email address so we can verify your account?"
        }
    
    elif session.step == 'email':
        # Validate email format
        if '@' not in message or '.' not in message.split('@')[-1]:
            return {
                'message': "That doesn't look like a valid email address. Please provide a valid email."
            }
        
        # Check if user exists
        user, created = User.objects.get_or_create(
            email=message.lower(),
            defaults={'name': session.temp_data.get('name', 'User')}
        )
        
        session.user = user
        session.step = 'otp'
        session.save()
        
        # Generate and send OTP
        otp = OTP.objects.create(user=user)
        otp_code = otp.generate_code()
        
        # Send email
        try:
            send_mail(
                'StudyGlobal Verification Code',
                f'Your verification code is: {otp_code}\n\nThis code will expire in 10 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Email sending failed: {str(e)}")
        
        return {
            'message': f"Great! We've sent a 6-digit verification code to {user.email}. Please enter it here to continue."
        }
    
    elif session.step == 'otp':
        if not message.isdigit() or len(message) != 6:
            return {
                'message': "Please enter a valid 6-digit code."
            }
        try:
            otp = OTP.objects.get(user=session.user, code=message, is_used=False)
            
            if not otp.is_valid():
                return {
                    'message': "This code has expired. Please request a new one."
                }
            
            # Mark OTP as used
            otp.is_used = True
            otp.save()
            
            # Verify user
            session.user.is_verified = True
            session.user.save()
            
            session.step = 'verified'
            session.save()
            
            return {
                'message': "Perfect! Your account has been verified. How can I help you with your study abroad journey today?"
            }
            
        except OTP.DoesNotExist:
            return {
                'message': "Invalid verification code. Please try again."
            }
    
    elif session.step == 'verified':
        # Check if user wants to find courses
        if any(keyword in message_lower for keyword in ["university", "course", "find", "study", "program"]):
            # Start collecting preferences
            session.step = 'collect_country'
            session.save()
            return {
                'message': "Great! I can help you to find that. First, which country would you like to study in?"
            }
        else:
            return {
                'message': "I can help you find universities and courses. Just tell me you'd like to find a course, and I'll guide you through the process."
            }
    
    elif session.step == 'collect_country':
        # Store country preference
        session.temp_data = session.temp_data or {}
        session.temp_data['country'] = message.title()
        session.step = 'collect_duration'
        session.save()
        
        formatted_country = message.title()
        
        return {
            'message': f"Perfect! {formatted_country} is a great choice. What duration are you looking for? (e.g., 1 year, 2 years, etc.)"
        }
    
    elif session.step == 'collect_duration':
        # Store duration preference
        session.temp_data = session.temp_data or {}
        session.temp_data['duration'] = message.lower()
        session.step = 'collect_level'  # NEW: Go to program level step
        session.save()
        return {
            'message': "Got it! What program level are you interested in? (e.g., Bachelor's, Master's, PhD, Diploma, etc.)"
        }
    
    elif session.step == 'collect_level':
        # Store program level preference
        session.temp_data = session.temp_data or {}
        session.temp_data['level'] = message.title()
        session.step = 'collect_course'
        session.save()
        
        formatted_level = message.title()
        return {
            'message': f"Excellent! {formatted_level} level it is. Now, what specific course or field of study are you interested in? (e.g., Computer Science, Business, Engineering, etc.)"
        }
    
    elif session.step == 'collect_course':
        # Store course preference and generate redirect URL
        session.temp_data = session.temp_data or {}
        session.temp_data['course'] = message.title()
        
        # Generate URL parameters for courses page
        country = session.temp_data['country']
        duration = session.temp_data['duration']
        level = session.temp_data['level']
        course = session.temp_data['course']
        
        # Create URL-encoded parameters
        import urllib.parse
        params = urllib.parse.urlencode({
            'country': country,
            'duration': duration,
            'level': level,  # NEW: Include level in URL parameters
            'course': course
        })
        
        # Update session to indicate we've collected all preferences
        session.step = 'preferences_collected'
        session.save()
        
        return {
            'message': f"Perfect! I've found courses matching your preferences:\n• Country: {country}\n• Duration: {duration}\n• Level: {level}\n• Course: {course}\n\nClick the button below to see your personalized course recommendations!",
            'redirect_url': f"/courses?{params}",
            'button_text': "View Recommended Courses"
        }
    
    elif session.step == 'preferences_collected':
        # User wants to search again or modify preferences
        if any(keyword in message_lower for keyword in ["search", "again", "new", "different", "change"]):
            # Reset to start collecting preferences again
            session.step = 'collect_country'
            session.save()
            return {
                'message': "Let's find more courses for you! Which country would you like to study in this time?"
            }
        elif any(keyword in message_lower for keyword in ["university", "course", "find", "study", "program"]):
            # Start a new search
            session.step = 'collect_country'
            session.save()
            return {
                'message': "Great! I can help you find another course. Which country would you like to study in?"
            }
        else:
            # Just provide general help
            return {
                'message': "I can help you find more courses. Just say 'search again' to start a new search, or tell me you'd like to find courses."
            }
    
    else:
        return {
            'message': "I'm not sure how to respond to that. Could you please try again?"
        }

@csrf_exempt
@require_http_methods(["POST"])
def resend_otp(request):
    """Resend OTP to the user's email."""
    try:
        print("=== Resend OTP Request ===")
        data = json.loads(request.body)
        session_id = data.get('session_id', '')
        
        print(f"Resend OTP for session: {session_id}")
        
        if not session_id:
            return JsonResponse({'error': 'Session ID required'}, status=400)
        
        session = ChatSession.objects.get(session_id=session_id)
        
        if session.step != 'otp' or not session.user:
            return JsonResponse({'error': 'Invalid request - not in OTP step'}, status=400)
        
        # Generate new OTP
        otp = OTP.objects.create(user=session.user)
        otp_code = otp.generate_code()
        
        # Send email
        try:
            send_mail(
                'StudyGlobal Verification Code (New)',
                f'Your new verification code is: {otp_code}\n\nThis code will expire in 10 minutes.',
                settings.DEFAULT_FROM_EMAIL,
                [session.user.email],
                fail_silently=False,
            )
        except Exception as e:
            print(f"Resend email failed: {str(e)}")
        
        return JsonResponse({
            'message': f"A new verification code has been sent to {session.user.email}."
        })
        
    except Exception as e:
        print(f"Resend OTP error: {str(e)}")
        print(traceback.format_exc())
        return JsonResponse({'error': str(e)}, status=400)

def home(request):
    """Home view to show API information."""
    if request.method == 'GET':
        return JsonResponse({
            'message': 'StudyGlobal Chatbot API',
            'version': '1.0.0',
            'endpoints': {
                'chat': '/api/chat/',
                'resend_otp': '/api/resend-otp/',
                'admin': '/admin/'
            }
        })
    return JsonResponse({'error': 'Method not allowed'}, status=405)