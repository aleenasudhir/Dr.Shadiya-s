from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):

    list_display = (
        'name',
        'phone',
        'concern',
        'appointment_date',
        'appointment_time',
        'email',
        'created_at',
    )

    list_filter = (
        'appointment_date',
        'concern',
    )

    search_fields = (
        'name',
        'phone',
        'email',
    )

    ordering = (
        'appointment_date',
        'appointment_time',
    )