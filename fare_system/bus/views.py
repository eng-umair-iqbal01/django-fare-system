import base64
import io
import json
from django.contrib import messages
import cv2
import numpy as np
import face_recognition
from django.shortcuts import render, redirect
from students.models import Student, Transaction
from .models import Bus, BusDriver
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import models


@login_required
def bus_dashboard(request):
    try:
        driver = BusDriver.objects.get(user=request.user)
        bus = driver.bus
        return render(
            request,
            "bus_dashboard.html",
            {"driver": driver, "bus": bus},
        )
    except BusDriver.DoesNotExist:
        messages.error(request, "Driver not found.")
        return redirect("login")


@login_required
def update_location(request):
    try:
        driver = BusDriver.objects.get(user=request.user)
        bus = driver.bus

        if request.method == "POST":
            try:
                data = json.loads(request.body)
                current_stop = data.get("location")

                if current_stop:
                    bus.current_stop = current_stop
                    bus.save()
                    return JsonResponse({
                        "success": True,
                        "message": f"Bus location updated to: {current_stop}",
                        "current_stop": current_stop
                    })
                else:
                    return JsonResponse({
                        "success": False,
                        "error": "Invalid location data"
                    })

            except json.JSONDecodeError:
                return JsonResponse({
                    "success": False,
                    "error": "Invalid JSON data"
                })

        return render(request, "update_location.html", {"bus": bus})

    except BusDriver.DoesNotExist:
        return JsonResponse({
            "success": False,
            "error": "Driver not found. Please log in with a valid driver account."
        })


def recognize_face(request):
    if request.method == "GET":
        return render(request, "recognize_face.html")

    elif request.method == "POST":
        try:
            # Get the image data from the POST request
            image_data = request.POST.get("image_data")

            if not image_data:
                return JsonResponse({
                    "status": "error",
                    "message": "No image data received.",
                    "continue": True  # Tell frontend to keep scanning
                })

            # Decode the base64 image
            image_data = image_data.split(",")[1]
            image_bytes = base64.b64decode(image_data)

            # Load image file
            frame = face_recognition.load_image_file(io.BytesIO(image_bytes))

            if len(frame.shape) == 3 and frame.shape[2] == 4:  # RGBA format
                frame = frame[:, :, :3]  # Convert to RGB

            face_locations = face_recognition.face_locations(frame, model="hog")

            if not face_locations:
                return JsonResponse({
                    "status": "error",
                    "message": "No face detected. Please position your face clearly in the frame.",
                    "continue": True  # Tell frontend to keep scanning
                })

            if len(face_locations) > 1:
                return JsonResponse({
                    "status": "error", 
                    "message": "Multiple faces detected. Please ensure only your face is in the frame.",
                    "continue": True
                })

            top, right, bottom, left = face_locations[0]
            face_width = right - left
            face_height = bottom - top

            if face_width < 50 or face_height < 50:
                return JsonResponse({
                    "status": "error",
                    "message": f"Face too small in image. Please move closer to the camera. (Size: {face_width}x{face_height})",
                    "continue": True
                })

            frame_encodings = face_recognition.face_encodings(
                frame, face_locations, num_jitters=3, model="small"
            )

            if not frame_encodings:
                return JsonResponse({
                    "status": "error",
                    "message": "Could not extract facial features. Please try again with better lighting.",
                    "continue": True
                })

            frame_encoding = frame_encodings[0]  # Use the first detected face

            # Debug log for troubleshooting
            print(f"Frame encoding shape: {frame_encoding.shape}, type: {type(frame_encoding)}")

            # Get all students with face encodings
            students = Student.objects.filter(
                models.Q(face_encodings__isnull=False) | 
                models.Q(face_encoding__isnull=False)
            )
            print(f"Found {students.count()} students with face encodings")

            # Debug log - print face distances for diagnostics
            face_distances = []

            for student in students:
                try:
                    # Try to use multiple encodings first (new method)
                    known_encodings = []

                    if student.face_encodings:
                        try:
                            # Parse the JSON array of encodings
                            encodings_data = json.loads(student.face_encodings)
                            
                            for encoding_data in encodings_data:
                                encoding_bytes = base64.b64decode(encoding_data["encoding"])
                                known_encoding = np.frombuffer(encoding_bytes, dtype=np.float64)
                                
                                # Reshape if needed
                                if known_encoding.shape[0] != frame_encoding.shape[0]:
                                    known_encoding = known_encoding.reshape(frame_encoding.shape)
                                
                                known_encodings.append(known_encoding)

                        except (json.JSONDecodeError, KeyError, TypeError) as e:
                            print(f"Error parsing face_encodings for student {student.student_id}: {str(e)}")

                    # Fallback to legacy single encoding if no multiple encodings found
                    if not known_encodings and student.face_encoding:
                        known_encoding_bytes = base64.b64decode(student.face_encoding)
                        known_encoding = np.frombuffer(known_encoding_bytes, dtype=np.float64)
                        
                        # Reshape if needed
                        if known_encoding.shape[0] != frame_encoding.shape[0]:
                            known_encoding = known_encoding.reshape(frame_encoding.shape)
                        
                        known_encodings.append(known_encoding)

                    # Skip if no valid encodings found
                    if not known_encodings:
                        continue

                    # Check against each encoding and keep the best match
                    best_distance = 1.0  # Initialize with worst possible distance
                    
                    for known_encoding in known_encodings:
                        distance = face_recognition.face_distance([known_encoding], frame_encoding)[0]
                        if distance < best_distance:
                            best_distance = distance

                    # Add the best match distance
                    face_distances.append((student, best_distance))
                    print(f"Best distance for student {student.student_id}: {best_distance}")

                except Exception as e:
                    print(f"Error processing student {student.student_id}: {str(e)}")
                    continue

            # Sort by distance (lowest first) and get best match
            if face_distances:
                face_distances.sort(key=lambda x: x[1])
                best_match_student, best_distance = face_distances[0]

                # Use a threshold of 0.6 for better accuracy with multiple encodings
                if best_distance <= 0.6:
                    # Found a match
                    # Check for a recent transaction within the last 30 minutes
                    last_transaction = Transaction.objects.filter(
                        student=best_match_student
                    ).order_by("-timestamp").first()
                    
                    current_time = timezone.now()

                    if last_transaction and (current_time - last_transaction.timestamp) < timedelta(minutes=30):
                        return JsonResponse({
                            "status": "info",
                            "message": f"Already checked in within the last 30 minutes. Student: {best_match_student.full_name}",
                            "student": best_match_student.full_name,
                            "lastCheckIn": last_transaction.timestamp.isoformat(),
                            "continue": True  # Keep scanning for other faces
                        })

                    # Create a new transaction
                    transaction = Transaction.objects.create(
                        student=best_match_student,
                        amount=20,
                        status="Pending",  # Start as pending, let the save method handle status
                    )

                    # Format confidence percentage for user feedback
                    confidence = (1 - best_distance) * 100

                    if transaction.status == "Approved":
                        return JsonResponse({
                            "status": "success",
                            "message": f"Face recognized: {best_match_student.full_name} (confidence: {confidence:.1f}%). Payment successful. New balance: {best_match_student.balance}",
                            "student": best_match_student.full_name,
                            "confidence": confidence,
                            "balance": best_match_student.balance,
                            "continue": True  # Keep scanning for other faces
                        })
                    else:
                        return JsonResponse({
                            "status": "error",
                            "message": f"Face recognized: {best_match_student.full_name} (confidence: {confidence:.1f}%). Insufficient balance ({best_match_student.balance}).",
                            "student": best_match_student.full_name,
                            "confidence": confidence,
                            "balance": best_match_student.balance,
                            "continue": True
                        })
                else:
                    # Debug info for close but not matching
                    if len(face_distances) > 0:
                        closest_distance = face_distances[0][1]
                        return JsonResponse({
                            "status": "error",
                            "message": f"Face not recognized. Closest match had {(1-closest_distance)*100:.1f}% confidence which is below the threshold. Please try again or re-enroll your face.",
                            "confidence": (1-closest_distance)*100,
                            "continue": True
                        })

            return JsonResponse({
                "status": "error",
                "message": "Face not recognized. Please try again or enroll your face.",
                "continue": True
            })

        except Exception as e:
            import traceback
            print("Face recognition error:", str(e))
            print(traceback.format_exc())
            return JsonResponse({
                "status": "error", 
                "message": f"Error: {str(e)}",
                "continue": True  # Keep scanning even after errors
            })

    return JsonResponse({
        "status": "error", 
        "message": "Invalid request method.",
        "continue": False  # Stop on invalid method
    })


def driver_dashboard(request):
    driver = BusDriver.objects.get(user=request.user)
    bus = driver.bus
    return render(request, "driver_dashboard.html", {"driver": driver, "bus": bus})
