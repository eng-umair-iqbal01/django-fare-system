from django.urls import path
from .views import bus_dashboard, update_location, recognize_face

urlpatterns = [
    path("dashboard/", bus_dashboard, name="bus_dashboard"),
    path("update-location/", update_location, name="update_location"),
    path("recognize-face/", recognize_face, name="recognize_face"),
]
