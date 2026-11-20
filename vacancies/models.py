from django.conf import settings
from django.db import models

class Building(models.Model):
    name = models.CharField(max_length=100, unique=True)
    is_active = models.BooleanField(default=True)   # False for NGE, Gymnasium, renovations

    def __str__(self):
        return self.name

class Room(models.Model):
    class RoomType(models.TextChoices):
        AIRCON = "aircon", "Air-conditioned"
        OPEN = "open", "Open-windowed"

    building = models.ForeignKey(Building, on_delete=models.CASCADE, related_name="rooms")
    floor = models.PositiveSmallIntegerField()
    name = models.CharField(max_length=50)
    room_type = models.CharField(max_length=10, choices=RoomType.choices)
    is_accessible = models.BooleanField(default=True)

    class Meta:
        unique_together = ("building", "name")
        ordering = ["building__name", "floor", "name"]

    def __str__(self):
        return f"{self.building.name} {self.name}"

class VacancyReport(models.Model):
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="reports")
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name="vacancy_reports")
    is_vacant = models.BooleanField(default=True)
    slot_start = models.TimeField()
    slot_end = models.TimeField()
    notes = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.room} ({'vacant' if self.is_vacant else 'occupied'})"