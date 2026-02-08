import json
import uuid
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


@csrf_exempt
@require_http_methods(["POST"])
def chat_api(request):
    try:
        data = json.loads(request.body)

        message = data.get("message", "").strip()
        session_id = data.get("session_id") or str(uuid.uuid4())
        step = data.get("step", "greeting")
        temp_data = data.get("temp_data", {})

        reply, step, temp_data, redirect = process_chat(
            message, step, temp_data
        )

        response = {
            "reply": reply,
            "session_id": session_id,
            "step": step,
            "temp_data": temp_data,
        }

        if redirect:
            response.update(redirect)

        return JsonResponse(response)

    except Exception as e:
        return JsonResponse(
            {"error": str(e)},
            status=500
        )


def process_chat(message, step, temp_data):
    msg = message.lower().strip()
    redirect = None

    # ---- FLOW ----

    if step == "greeting":
        return (
            "Hello! 👋 Welcome to StudyGlobal. What’s your name?",
            "name",
            temp_data,
            None,
        )

    if step == "name":
        if len(message) < 2:
            return (
                "Please enter a valid name.",
                "name",
                temp_data,
                None,
            )
        temp_data["name"] = message.title()
        return (
            f"Nice to meet you, {temp_data['name']}! What country do you want to study in?",
            "country",
            temp_data,
            None,
        )

    if step == "country":
        temp_data["country"] = message.title()
        return (
            "Great choice! What duration are you looking for? (1 year / 2 years)",
            "duration",
            temp_data,
            None,
        )

    if step == "duration":
        temp_data["duration"] = message.lower()
        return (
            "What program level are you interested in? (Bachelor’s / Master’s / PhD)",
            "level",
            temp_data,
            None,
        )

    if step == "level":
        temp_data["level"] = message.title()
        return (
            "What course or field are you interested in?",
            "course",
            temp_data,
            None,
        )

    if step == "course":
        temp_data["course"] = message.title()

        params = (
            f"country={temp_data['country']}"
            f"&duration={temp_data['duration']}"
            f"&level={temp_data['level']}"
            f"&course={temp_data['course']}"
        )

        redirect = {
            "redirect_url": f"/courses?{params}",
            "button_text": "View Recommended Courses",
        }

        return (
            f"Perfect! 🎓 I found courses for:\n"
            f"• Country: {temp_data['country']}\n"
            f"• Duration: {temp_data['duration']}\n"
            f"• Level: {temp_data['level']}\n"
            f"• Course: {temp_data['course']}",
            "done",
            temp_data,
            redirect,
        )

    return (
        "Type 'search again' to start over.",
        "greeting",
        {},
        None,
    )


def home(request):
    return JsonResponse({
        "status": "OK",
        "endpoints": {
            "chat": "/api/chat/",
        }
    })
