import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Student, Transaction
from bus.models import Bus, BusDriver
import base64
import face_recognition
from django.http import JsonResponse
import io
import cv2
from django.utils import timezone
from .models import Student
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.conf import settings
import requests
from django.core.cache import cache


@login_required
def change_password(request):
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Keep the user logged in
            messages.success(request, "Your password has been updated successfully!")
            return redirect("student_dashboard")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = PasswordChangeForm(request.user)

    return render(request, "change_password.html", {"form": form})


@login_required
def face_enrollment(request):
    """Handles face enrollment for the student with multiple angles and improved quality checks."""
    if request.method == "POST":
        try:
            # Get the uploaded image from the request
            image_data = request.POST.get("image_data")
            angle = request.POST.get("angle", "center")  # Get the angle of the face

            if not image_data:
                return JsonResponse(
                    {"status": "error", "message": "No image data provided."}
                )

            # Decode the base64 image
            image_data = base64.b64decode(image_data.split(",")[1])
            np_image = face_recognition.load_image_file(io.BytesIO(image_data))

            # Check image quality
            if np_image.shape[0] < 100 or np_image.shape[1] < 100:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Image resolution too low. Please move closer to the camera.",
                    }
                )

            # Convert to RGB if needed
            if len(np_image.shape) == 3 and np_image.shape[2] == 4:  # RGBA format
                np_image = np_image[:, :, :3]  # Convert to RGB

            # Get face locations first to check quality
            face_locations = face_recognition.face_locations(np_image, model="hog")

            if len(face_locations) == 0:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "No face detected. Please ensure your face is clearly visible.",
                    }
                )

            if len(face_locations) > 1:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Multiple faces detected. Please ensure only your face is in the frame.",
                    }
                )

            # Check face size - if too small, recognition will be poor
            top, right, bottom, left = face_locations[0]
            face_width = right - left
            face_height = bottom - top

            if face_width < 50 or face_height < 50:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": f"Face too small in image. Please move closer to the camera. (Size: {face_width}x{face_height})",
                    }
                )

            # IMPORTANT: Use the SAME model and jitters here as in recognition
            # To ensure consistency between enrollment and recognition
            encodings = face_recognition.face_encodings(
                np_image, face_locations, num_jitters=3, model="small"
            )

            if len(encodings) == 0:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Could not extract facial features. Please try again with better lighting.",
                    }
                )

            # Debug info
            print(f"Encoding shape: {encodings[0].shape}, type: {type(encodings[0])}")

            # Save the face encoding to the student's profile
            student = request.user.student_profile

            # Get existing encodings if any
            existing_encodings = []
            if student.face_encodings:
                try:
                    existing_encodings = json.loads(student.face_encodings)
                except:
                    # If there's an error parsing, start fresh
                    existing_encodings = []

            # Add the new encoding with its angle
            new_encoding = {
                "angle": angle,
                "encoding": base64.b64encode(encodings[0].tobytes()).decode("utf-8"),
                "quality": {
                    "width": face_width,
                    "height": face_height,
                    "timestamp": str(timezone.now()),
                },
            }

            # Add to existing or create new
            existing_encodings.append(new_encoding)

            # Save as JSON string
            student.face_encodings = json.dumps(existing_encodings)

            # For backward compatibility, also save to face_encoding field
            student.face_encoding = base64.b64encode(encodings[0].tobytes()).decode(
                "utf-8"
            )

            student.save()

            # Calculate progress based on number of angles collected
            angles_count = len(existing_encodings)
            total_required = 5  # We want 5 different angles
            progress = min(angles_count / total_required * 100, 100)

            # Calculate quality score based on face size relative to image
            image_area = np_image.shape[0] * np_image.shape[1]
            face_area = face_width * face_height
            quality_ratio = (face_area / image_area) * 100
            quality_text = (
                "Excellent"
                if quality_ratio > 15
                else (
                    "Good"
                    if quality_ratio > 10
                    else "Fair" if quality_ratio > 5 else "Poor"
                )
            )

            return JsonResponse(
                {
                    "status": "success",
                    "message": f"Face angle '{angle}' enrolled successfully. ({angles_count}/{total_required})",
                    "face_width": face_width,
                    "face_height": face_height,
                    "quality": quality_text,
                    "quality_score": quality_ratio,
                    "progress": progress,
                    "angles_count": angles_count,
                    "total_required": total_required,
                    "complete": angles_count >= total_required,
                }
            )
        except Exception as e:
            import traceback

            print("Face enrollment error:", str(e))
            print(traceback.format_exc())
            return JsonResponse({"status": "error", "message": f"Error: {str(e)}"})

    return render(request, "face_enrollment.html")


@login_required
def student_dashboard(request):
    """Handles the student dashboard access with bus location tracking."""
    if request.user.is_superuser:
        return render(request, "student_dashboard.html", {
            "student": None,
            "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY
        })

    try:
        student = request.user.student_profile
        buses = Bus.objects.all()
        
        # Get cached bus locations
        bus_locations = {}
        for bus in buses:
            cache_key = f'bus_location_{bus.id}'
            location = cache.get(cache_key)
            if location:
                bus_locations[bus.id] = location

        return render(request, "student_dashboard.html", {
            "student": student,
            "buses": buses,
            "bus_locations": bus_locations,
            "google_maps_api_key": settings.GOOGLE_MAPS_API_KEY
        })
    except Student.DoesNotExist:
        return redirect("admin_dashboard")


@login_required
def get_bus_location(request, bus_id):
    """API endpoint to get real-time bus location."""
    try:
        bus = Bus.objects.get(id=bus_id)
        cache_key = f'bus_location_{bus_id}'
        
        # Try to get cached location first
        cached_location = cache.get(cache_key)
        if cached_location:
            return JsonResponse(cached_location)

        if bus.current_stop:
            try:
                # Using OpenStreetMap Nominatim API for geocoding
                # Add a unique user agent as required by Nominatim's terms
                headers = {
                    'User-Agent': 'FareSystem/1.0'
                }
                response = requests.get(
                    f"https://nominatim.openstreetmap.org/search",
                    params={
                        'q': bus.current_stop,
                        'format': 'json',
                        'limit': 1
                    },
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        location = {
                            'status': 'success',
                            'location': {
                                'lat': float(data[0]['lat']),
                                'lng': float(data[0]['lon']),
                                'address': bus.current_stop
                            }
                        }
                        # Cache the location for 1 minute
                        cache.set(cache_key, location, 60)
                        return JsonResponse(location)

            except Exception as e:
                print(f"Geocoding error: {str(e)}")

        # Return default location if geocoding fails
        return JsonResponse({
            'status': 'error',
            'message': 'Location not available'
        })

    except Bus.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Bus not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=500)


@login_required
def approve_payment(request, transaction_id):
    """Handles payment approval for students."""
    transaction = get_object_or_404(Transaction, id=transaction_id)
    transaction.save()

    return redirect("student_dashboard")
