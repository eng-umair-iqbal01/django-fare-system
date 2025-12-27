from django.contrib.auth.models import User
from django.db import models

# from tensorflow.keras.models import load_model
# import os

# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# MODEL_PATH = os.path.join(BASE_DIR, "facenet_keras.h5")

# try:
#     facenet_model = load_model(MODEL_PATH)
# except Exception as e:
#     print("Error loading FaceNet model:", e)
#     facenet_model = None


class Student(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="student_profile"
    )
    full_name = models.CharField(max_length=100)
    student_id = models.PositiveIntegerField(
        unique=True
    )  # Numeric student ID (used as username)
    balance = models.FloatField(default=0.0)
    face_encoding = models.TextField(blank=True, null=True)
    face_encodings = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.full_name} ({self.student_id})"

    def credit_balance(self, amount):
        self.balance += amount
        self.save()

    def deduct_balance(self, amount):
        if self.balance >= amount:
            self.balance -= amount
            self.save()
            return True
        return False


class Transaction(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    amount = models.FloatField(default=20.0)
    timestamp = models.DateTimeField(auto_now_add=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ("Pending", "Pending"),
            ("Approved", "Approved"),
            ("Declined", "Declined"),
        ],
        default="Pending",
    )

    def save(self, *args, **kwargs):
        # Automatically approve and deduct balance if sufficient
        if self.status == "Pending" and self.student.balance >= self.amount:
            self.student.balance -= self.amount
            self.student.save()
            self.status = "Approved"
        elif self.status == "Pending":
            self.status = "Declined"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.user.username} - {self.amount} - {self.status}"
