from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            print(f"User '{username}' logged in successfully.")

            # Check user role and redirect accordingly
            if user.is_superuser:
                print("Redirecting to admin dashboard")
                return redirect("admin_dashboard")
            elif hasattr(user, "student_profile"):
                print("Redirecting to student dashboard")
                return redirect("student_dashboard")
            elif user.groups.filter(name="Drivers").exists():
                print("Redirecting to bus dashboard")
                return redirect("bus_dashboard")
            else:
                print("Redirecting to home")
                return redirect("home")
        else:
            print(f"Failed login attempt for '{username}'")
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, "users/login.html")


def logout_view(request):
    logout(request)
    return redirect("home")


@login_required
def dashboard(request):
    user = request.user

    # Check user role and redirect accordingly
    if user.is_superuser:
        return redirect("admin_dashboard")  # SuperAdmin sees everything
    elif user.groups.filter(name="Students").exists():
        return redirect("student_dashboard")  # Student Dashboard
    elif user.groups.filter(name="Drivers").exists():
        return redirect("driver_dashboard")  # Driver Dashboard
    else:
        messages.error(request, "Unauthorized access.")
        return redirect("home")  # Fallback for unauthorized access
