from django.urls import path
from .views import student_dashboard, approve_payment, face_enrollment, change_password, get_bus_location

urlpatterns = [
    path("dashboard/", student_dashboard, name="student_dashboard"),
    path(
        "approve-payment/<int:transaction_id>/", approve_payment, name="approve_payment"
    ),
    path("face-enrollment/", face_enrollment, name="face_enrollment"),
    path("change_password/", change_password, name="change_password"),
    # Add both URL patterns for the bus location API
    path("api/bus-location/<int:bus_id>/", get_bus_location, name="get_student_bus_location"),
    path("bus-location/<int:bus_id>/", get_bus_location, name="get_student_bus_location_alt"),
]
