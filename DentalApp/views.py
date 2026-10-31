import os
import json
import logging
import threading
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
import urllib.request
import urllib.error

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import AppointmentForm
from .models import Appointment

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


# =========================================================
# EMAIL DISPATCHER (HTTP API / SMTP FALLBACK)
# =========================================================

def _send_via_brevo_api(api_key, to_email, to_name, subject, html_content, text_content=None):
    """Sends transactional email via Brevo REST API (HTTPS port 443 - never blocked by hosts)."""
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "api-key": api_key,
        "content-type": "application/json",
    }
    payload = {
        "sender": {
            "name": "Dr. Shadiya's Dental Clinic",
            "email": getattr(settings, "EMAIL_HOST_USER", "dr.shadiyasofficial@gmail.com")
        },
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }
    if text_content:
        payload["textContent"] = text_content

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.status in (200, 201, 202)


def send_booking_emails(patient_email, patient_name, patient_phone, appointment_date_text, appointment_time_text, concern_text):
    """
    Sends confirmation email to the patient and an alert email to the clinic.
    Uses Brevo HTTP API if BREVO_API_KEY is configured (works on Render free tier),
    otherwise falls back to Django's standard SMTP backend.
    """
    brevo_api_key = os.getenv("BREVO_API_KEY")

    # ---------------------------------------------------------
    # 1. PREPARE EMAIL CONTENTS
    # ---------------------------------------------------------
    patient_subject = "Your Appointment is Confirmed | Dr. Shadiya's Dental Clinic"

    patient_text = f"""Dear {patient_name},

Your appointment has been successfully confirmed.

APPOINTMENT DETAILS
Date: {appointment_date_text}
Time: {appointment_time_text}
Concern: {concern_text}
Duration: 1 Hour

If you need to reschedule or cancel your appointment, please contact our clinic in advance.

Dr. Shadiya's Dental Clinic and Implant Centre
Haya Tower, Sastha Temple Road, Manapattiparambu, Kaloor, Kochi - 682018
"""

    patient_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Appointment Confirmation</title>
</head>
<body style="margin:0;padding:0;background:#f4f2ec;font-family:Arial, Helvetica, sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f2ec;padding:35px 15px;">
<tr>
<td align="center">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="max-width:620px;background:#ffffff;border-radius:10px;overflow:hidden;">
<tr>
<td style="background:#263a35;padding:40px 30px;text-align:center;">
<div style="color:#c6a36a;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;">DR. SHADIYA'S</div>
<div style="color:#ffffff;font-family:Georgia, 'Times New Roman', serif;font-size:28px;line-height:1.35;">Dental Clinic &<br>Implant Centre</div>
</td>
</tr>
<tr>
<td style="padding:42px 35px;">
<div style="color:#a4865b;font-size:10px;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;">APPOINTMENT CONFIRMATION</div>
<h1 style="margin:0 0 20px 0;color:#263a35;font-family:Georgia, 'Times New Roman', serif;font-size:28px;line-height:1.3;font-weight:normal;">
Your appointment is confirmed.
</h1>
<p style="margin:0 0 28px 0;color:#666666;font-size:15px;line-height:1.8;">
Dear <strong>{patient_name}</strong>,<br><br>
Thank you for choosing Dr. Shadiya's Dental Clinic. Your appointment has been successfully confirmed.
</p>
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f7f5ef;border-left:4px solid #a4865b;margin:25px 0;">
<tr>
<td style="padding:24px;">
<div style="color:#a4865b;font-size:10px;letter-spacing:2px;text-transform:uppercase;margin-bottom:16px;">YOUR APPOINTMENT</div>
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="padding:8px 0;color:#888888;font-size:12px;width:35%;">DATE</td>
<td style="padding:8px 0;color:#263a35;font-size:15px;font-weight:bold;">{appointment_date_text}</td>
</tr>
<tr>
<td style="padding:8px 0;color:#888888;font-size:12px;">TIME</td>
<td style="padding:8px 0;color:#263a35;font-size:15px;font-weight:bold;">{appointment_time_text}</td>
</tr>
<tr>
<td style="padding:8px 0;color:#888888;font-size:12px;">CONCERN</td>
<td style="padding:8px 0;color:#263a35;font-size:15px;">{concern_text}</td>
</tr>
<tr>
<td style="padding:8px 0;color:#888888;font-size:12px;">DURATION</td>
<td style="padding:8px 0;color:#263a35;font-size:15px;">1 Hour</td>
</tr>
</table>
</td>
</tr>
</table>
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:20px;">
<tr>
<td style="padding:16px;background:#faf9f6;border:1px solid #ebe7dd;color:#666666;font-size:13px;line-height:1.7;">
<strong style="color:#263a35;">Please note:</strong> If you need to reschedule or cancel your appointment, please contact our clinic in advance.
</td>
</tr>
</table>
<p style="color:#777777;font-size:13px;line-height:1.8;margin-top:24px;">
We look forward to welcoming you and helping you take the next step towards a healthier, confident smile.
</p>
</td>
</tr>
<tr>
<td style="padding:28px 30px;background:#263a35;text-align:center;">
<div style="color:#c6a36a;font-size:10px;letter-spacing:2px;text-transform:uppercase;margin-bottom:10px;">VISIT US</div>
<div style="color:#ffffff;font-family:Georgia, serif;font-size:18px;margin-bottom:10px;">Dr. Shadiya's Dental Clinic & Implant Centre</div>
<div style="color:rgba(255,255,255,.7);font-size:12px;line-height:1.6;">
Haya Tower, Sastha Temple Road, Manapattiparambu, Kaloor, Kochi - 682018
</div>
</td>
</tr>
<tr>
<td style="padding:18px;text-align:center;background:#f7f5ef;color:#999999;font-size:11px;">
Automated appointment confirmation from Dr. Shadiya's Dental Clinic.
</td>
</tr>
</table>
</td>
</tr>
</table>
</body>
</html>
"""

    clinic_subject = f"🔔 New Appointment | {patient_name}"
    clinic_message = f"""NEW APPOINTMENT BOOKED

Patient Details
-------------------------
Name: {patient_name}
Phone: {patient_phone}
Email: {patient_email or 'Not provided'}

Appointment Details
-------------------------
Date: {appointment_date_text}
Time: {appointment_time_text}
Concern: {concern_text}

Booked via clinic website.
"""

    clinic_email_recipient = "dr.shadiya.shareef@gmail.com"

    # ---------------------------------------------------------
    # 2. DISPATCH PATIENT EMAIL
    # ---------------------------------------------------------
    if patient_email:
        try:
            if brevo_api_key:
                _send_via_brevo_api(brevo_api_key, patient_email, patient_name, patient_subject, patient_html, patient_text)
            else:
                email = EmailMultiAlternatives(
                    subject=patient_subject,
                    body=patient_text,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=[patient_email],
                )
                email.attach_alternative(patient_html, "text/html")
                email.send(fail_silently=False)
        except Exception as e:
            logger.error("Patient email delivery failed: %s", e)

    # ---------------------------------------------------------
    # 3. DISPATCH CLINIC ALERT EMAIL
    # ---------------------------------------------------------
    try:
        if brevo_api_key:
            clinic_html = f"<pre style='font-family:sans-serif;'>{clinic_message}</pre>"
            _send_via_brevo_api(brevo_api_key, clinic_email_recipient, "Dr. Shadiya Clinic", clinic_subject, clinic_html, clinic_message)
        else:
            send_mail(
                subject=clinic_subject,
                message=clinic_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[clinic_email_recipient],
                fail_silently=False,
            )
    except Exception as e:
        logger.error("Clinic alert email delivery failed: %s", e)


# =========================================================
# BASIC PAGES
# =========================================================

def home(request):
    return render(request, "home.html")


def base(request):
    return render(request, "base.html")


def about(request):
    return render(request, "about.html")


def treatments(request):
    return render(request, "treatments.html")


def contact(request):
    return render(request, "contact.html")


def testimonials(request):
    return render(request, "testimonial.html")


# =========================================================
# BOOK APPOINTMENT
# =========================================================

def booking(request):
    now_ist = timezone.now().astimezone(IST)
    today = now_ist.date()
    current_time_str = now_ist.strftime("%H:%M")

    if request.method == "POST":
        form = AppointmentForm(request.POST)

        if form.is_valid():
            appointment_date = form.cleaned_data["appointment_date"]
            appointment_time_val = form.cleaned_data["appointment_time"]
            selected_time_str = str(appointment_time_val)[:5]

            # 1. Past Date Check
            if appointment_date < today:
                form.add_error("appointment_date", "Please select today or a future date.")

            # 2. Sunday Holiday Check
            elif appointment_date.weekday() == 6:
                form.add_error("appointment_date", "Sunday is a holiday. Please select another date.")

            # 3. Elapsed Time on Today's Date Check
            elif appointment_date == today and selected_time_str <= current_time_str:
                form.add_error("appointment_time", "This time slot has already passed today. Please choose an upcoming time.")

            else:
                # 4. Existing Booking Check
                already_booked = Appointment.objects.filter(
                    appointment_date=appointment_date,
                    appointment_time=selected_time_str,
                ).exists()

                if already_booked:
                    form.add_error("appointment_time", "This time slot is already booked. Please choose another time.")
                else:
                    try:
                        with transaction.atomic():
                            appointment = form.save(commit=False)
                            appointment.appointment_time = selected_time_str
                            appointment.save()

                        request.session["appointment_id"] = appointment.id

                        # Format texts for confirmation
                        appointment_date_text = appointment.appointment_date.strftime("%d %B %Y")
                        appointment_time_text = dict(Appointment.TIME_CHOICES).get(
                            selected_time_str, selected_time_str
                        )
                        concern_text = appointment.get_concern_display()
                        if appointment.concern == "other" and appointment.other_concern:
                            concern_text = f"Other: {appointment.other_concern}"

                        # Run email sending in background thread
                        email_thread = threading.Thread(
                            target=send_booking_emails,
                            args=(
                                appointment.email,
                                appointment.name,
                                appointment.phone,
                                appointment_date_text,
                                appointment_time_text,
                                concern_text,
                            ),
                            daemon=True,
                        )
                        email_thread.start()

                        return redirect("booking_success")

                    except IntegrityError:
                        form.add_error("appointment_time", "This time slot was just booked by another patient. Please select another time.")

    else:
        form = AppointmentForm()

    return render(request, "booking.html", {"form": form})


# =========================================================
# BOOKING SUCCESS
# =========================================================

def booking_success(request):
    appointment_id = request.session.get("appointment_id")
    if not appointment_id:
        return redirect("booking")

    try:
        appointment = Appointment.objects.get(id=appointment_id)
    except Appointment.DoesNotExist:
        return redirect("booking")

    return render(request, "booking_success.html", {"appointment": appointment})


# =========================================================
# AVAILABLE APPOINTMENT TIMES (AJAX / JSON)
# =========================================================

def available_times(request):
    date_string = request.GET.get("date")
    if not date_string:
        return JsonResponse({
            "available_times": [],
            "booked_times": [],
            "is_holiday": False,
            "message": "Date is required.",
        })

    try:
        selected_date = datetime.strptime(date_string, "%Y-%m-%d").date()
    except ValueError:
        return JsonResponse({
            "available_times": [],
            "booked_times": [],
            "is_holiday": False,
            "message": "Invalid date format. Use YYYY-MM-DD.",
        })

    now_ist = timezone.now().astimezone(IST)
    today = now_ist.date()
    current_time_str = now_ist.strftime("%H:%M")

    # Past Date Check
    if selected_date < today:
        return JsonResponse({
            "available_times": [],
            "booked_times": [],
            "is_holiday": False,
            "message": "Please select today or a future date.",
        })

    # Sunday Holiday Check
    if selected_date.weekday() == 6:
        return JsonResponse({
            "available_times": [],
            "booked_times": [],
            "is_holiday": True,
            "message": "Sunday is a holiday. Please select another date.",
        })

    # Fixed Clinic Slots: 09:30 AM to 06:30 PM (Hourly)
    clinic_slots = [
        ("09:30", "09:30 AM"),
        ("10:30", "10:30 AM"),
        ("11:30", "11:30 AM"),
        ("12:30", "12:30 PM"),
        ("13:30", "01:30 PM"),
        ("14:30", "02:30 PM"),
        ("15:30", "03:30 PM"),
        ("16:30", "04:30 PM"),
        ("17:30", "05:30 PM"),
        ("18:30", "06:30 PM"),
    ]

    # Fetch already booked times for the chosen date
    booked_records = Appointment.objects.filter(
        appointment_date=selected_date
    ).values_list("appointment_time", flat=True)

    booked_times = [str(t)[:5] for t in booked_records]

    # Filter out booked slots and past slots for today
    available_times_list = []
    for slot_val, slot_label in clinic_slots:
        if selected_date == today and slot_val <= current_time_str:
            continue
        if slot_val in booked_times:
            continue
        available_times_list.append({
            "value": slot_val,
            "label": slot_label,
        })

    return JsonResponse({
        "available_times": available_times_list,
        "booked_times": booked_times,
        "is_holiday": False,
        "message": "",
    })