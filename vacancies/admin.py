from django.contrib import admin
from .models import Building, Room, VacancyReport

admin.site.register(Building)
admin.site.register(VacancyReport)

@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ("name", "building", "floor", "is_accessible")
    list_filter = ("building",)
