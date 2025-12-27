from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.models import User
from bus.models import Bus, BusDriver  # Import Bus and BusDriver from bus app
from students.models import Student
from django.contrib.auth.models import Group


def admin_dashboard(request):
    students = Student.objects.all()
    print("Students:", students)  # Debug print
    drivers = BusDriver.objects.all()
    buses = Bus.objects.all()
    return render(
        request,
        "admin_dashboard.html",
        {"students": students, "drivers": drivers, "buses": buses},
    )


def add_student(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        student_id = request.POST.get("student_id")
        password = request.POST.get("password")
        balance = request.POST.get("balance")

        if not full_name or not student_id or not password or not balance:
            messages.error(request, "All fields are required.")
            return redirect("add_student")

        try:
            student_id = int(student_id)
            username = str(student_id)

            if User.objects.filter(username=username).exists():
                messages.error(request, "Student ID already exists.")
                return redirect("add_student")

            user = User.objects.create_user(username=username, password=password)
            Student.objects.create(
                user=user,
                full_name=full_name,
                student_id=student_id,
                balance=float(balance),
                face_encoding="",
                face_encodings="[]",
            )

            messages.success(request, "Student added successfully!")
            return redirect("admin_dashboard")
        except ValueError:
            messages.error(request, "Invalid data entered.")
            return redirect("add_student")

    return render(request, "add_student.html")


def update_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)

    if request.method == "POST":
        student.full_name = request.POST.get("full_name")
        student.balance = float(request.POST.get("balance"))
        student.save()
        messages.success(request, "Student updated successfully!")
        return redirect("admin_dashboard")

    return render(request, "update_student.html", {"student": student})


def delete_student(request, student_id):
    student = get_object_or_404(Student, student_id=student_id)
    student.user.delete()  # Delete associated user
    student.delete()
    messages.success(request, "Student deleted successfully!")
    return redirect("admin_dashboard")


def add_bus_driver(request):
    if request.method == "POST":
        full_name = request.POST.get("full_name")
        username = request.POST.get("username")
        password = request.POST.get("password")
        bus_id = request.POST.get("bus_id")

        # Validate required fields
        if not full_name or not username or not password:
            messages.error(request, "All fields are required.")
            return redirect("add_bus_driver")

        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken.")
            return redirect("add_bus_driver")

        try:
            user = User.objects.create_user(username=username, password=password)
            bus = None

            if bus_id:
                bus = Bus.objects.filter(id=bus_id).first()
                if not bus:
                    messages.error(request, "Invalid bus selected.")
                    return redirect("add_bus_driver")

                if hasattr(bus, "busdriver"):
                    messages.error(request, f"Bus '{bus.bus_number}' already has a driver.")
                    return redirect("add_bus_driver")

            # Create the BusDriver entry
            BusDriver.objects.create(user=user, full_name=full_name, bus=bus)

            drivers_group, created = Group.objects.get_or_create(name="Drivers")
            user.groups.add(drivers_group)

            messages.success(request, "Bus driver added successfully!")
            return redirect("admin_dashboard")

        except Exception as e:
            messages.error(request, f"An error occurred: {str(e)}")
            return redirect("add_bus_driver")

    buses = Bus.objects.all()
    return render(request, "add_bus_driver.html", {"buses": buses})

def update_bus_driver(request, driver_id):
    driver = get_object_or_404(BusDriver, id=driver_id)

    if request.method == "POST":
        driver.full_name = request.POST.get("full_name")
        bus_id = request.POST.get("bus_id")
        if bus_id:
            driver.bus = Bus.objects.get(id=bus_id)
        driver.save()
        messages.success(request, "Bus driver updated successfully!")
        return redirect("admin_dashboard")

    buses = Bus.objects.all()
    return render(request, "update_bus_driver.html", {"driver": driver, "buses": buses})


def delete_bus_driver(request, driver_id):
    driver = get_object_or_404(BusDriver, id=driver_id)
    driver.user.delete()  # Delete associated user
    driver.delete()
    messages.success(request, "Bus driver deleted successfully!")
    return redirect("admin_dashboard")


def bus_list(request):
    buses = Bus.objects.all()
    return render(request, "bus_list.html", {"buses": buses})


def add_bus(request):
    if request.method == "POST":
        bus_number = request.POST.get("bus_number")
        route_name = request.POST.get("route_name")
        if not bus_number or not route_name:
            messages.error(request, "All fields are required.")
            return redirect("add_bus")

        if Bus.objects.filter(bus_number=bus_number).exists():
            messages.error(request, "Bus number already exists.")
            return redirect("add_bus")

        try:
            Bus.objects.create(bus_number=bus_number, route_name=route_name)
            messages.success(request, "Bus added successfully!")
        except Exception as e:
            messages.error(request, f"Error adding bus: {e}")

        return redirect("admin_dashboard")

    return render(request, "add_bus.html")


def update_bus(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)

    # Fetch all available bus drivers for selection
    drivers = BusDriver.objects.all()

    if request.method == "POST":
        try:
            # Update bus details
            bus.bus_number = request.POST.get("bus_number")
            bus.route_name = request.POST.get("route_name")

            # Get selected driver ID and update the driver assignment
            driver_id = request.POST.get("bus_driver")
            if driver_id:
                driver = get_object_or_404(BusDriver, id=driver_id)
                bus.drivers.clear()  # Clear existing driver assignment
                bus.drivers.add(driver)  # Assign the new driver

            bus.save()
            messages.success(request, "Bus updated successfully!")
        except Exception as e:
            messages.error(request, f"Error updating bus: {e}")

        return redirect("admin_dashboard")

    # Get the current driver assigned to the bus
    current_driver = bus.drivers.first()  # Assuming one driver per bus

    return render(
        request,
        "update_bus.html",
        {"bus": bus, "drivers": drivers, "current_driver": current_driver},
    )


def delete_bus(request, bus_id):
    bus = get_object_or_404(Bus, id=bus_id)

    try:
        bus.delete()
        messages.success(request, "Bus deleted successfully!")
    except Exception as e:
        messages.error(request, f"Error deleting bus: {e}")

    return redirect("admin_dashboard")
