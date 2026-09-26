from datetime import datetime, timedelta
import os
import threading

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, send_mail
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone

from .forms import AppointmentForm
from .models import Appointment


# =========================================================
# EMAIL WORKER (RUNS IN BACKGROUND VIA THREAD)
# =========================================================

def send_booking_emails(appointment, appointment_date_text, appointment_time_text, concern_text):
    """
    Sends confirmation email to the patient and alert email to the clinic.
    Running this in a separate thread eliminates loading delays on form submission.
    """
    # 1. SEND CONFIRMATION EMAIL TO PATIENT
    if appointment.email:
        try:
            patient_subject = (
                "Your Appointment is Confirmed | Dr. Shadiya's Dental Clinic"
            )

            text_content = f"""
Dear {appointment.name},

Your appointment has been successfully confirmed.

APPOINTMENT DETAILS

Date: {appointment_date_text}
Time: {appointment_time_text}
Concern: {concern_text}

Thank you for choosing Dr. Shadiya's Dental Clinic and Implant Centre.

If you need to reschedule or cancel your appointment,
please contact our clinic in advance.

Dr. Shadiya's Dental Clinic and Implant Centre
Haya Tower, Sastha Temple Road, Manapattiparambu, Kaloor, Kochi - 682018
"""

            html_content = f"""
<!DOCTYPE html>
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

<!-- HEADER -->
<tr>
<td style="background:#263a35;padding:40px 30px;text-align:center;">
<div style="color:#c6a36a;font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;">
DR. SHADIYA'S
</div>
<div style="color:#ffffff;font-family:Georgia, 'Times New Roman', serif;font-size:28px;line-height:1.35;">
Dental Clinic &<br>Implant Centre
</div>
</td>
</tr>

<!-- MAIN CONTENT -->
<tr>
<td style="padding:42px 35px;">
<div style="color:#a4865b;font-size:10px;letter-spacing:3px;text-transform:uppercase;margin-bottom:12px;">
APPOINTMENT CONFIRMATION
</div>
<h1 style="margin:0 0 20px 0;color:#263a35;font-family:Georgia, 'Times New Roman', serif;font-size:30px;line-height:1.3;font-weight:normal;">
Your appointment is confirmed.
</h1>
<p style="margin:0 0 28px 0;color:#666666;font-size:15px;line-height:1.8;">
Dear <strong>{appointment.name}</strong>,<br><br>
Thank you for choosing Dr. Shadiya's Dental Clinic.
Your appointment has been successfully confirmed.
</p>

<!-- APPOINTMENT DETAILS BOX -->
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f7f5ef;border-left:4px solid #a4865b;margin:25px 0;">
<tr>
<td style="padding:26px;">
<div style="color:#a4865b;font-size:10px;letter-spacing:2px;text-transform:uppercase;margin-bottom:18px;">
YOUR APPOINTMENT
</div>
<table width="100%" cellpadding="0" cellspacing="0" border="0">
<tr>
<td style="padding:9px 0;color:#888888;font-size:12px;width:35%;">DATE</td>
<td style="padding:9px 0;color:#263a35;font-size:15px;font-weight:bold;">{appointment_date_text}</td>
</tr>
<tr>
<td style="padding:9px 0;color:#888888;font-size:12px;">TIME</td>
<td style="padding:9px 0;color:#263a35;font-size:15px;font-weight:bold;">{appointment_time_text}</td>
</tr>
<tr>
<td style="padding:9px 0;color:#888888;font-size:12px;">CONCERN</td>
<td style="padding:9px 0;color:#263a35;font-size:15px;">{concern_text}</td>
</tr>
<tr>
<td style="padding:9px 0;color:#888888;font-size:12px;">DURATION</td>
<td style="padding:9px 0;color:#263a35;font-size:15px;">1 Hour</td>
</tr>
</table>
</td>
</tr>
</table>

<!-- NOTE -->
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-top:25px;">
<tr>
<td style="padding:18px;background:#faf9f6;border:1px solid #ebe7dd;color:#666666;font-size:13px;line-height:1.7;">
<strong style="color:#263a35;">Please note</strong><br>
If you need to reschedule or cancel your appointment, please contact our clinic in advance.
</td>
</tr>
</table>

<p style="color:#777777;font-size:13px;line-height:1.8;margin-top:28px;">
We look forward to welcoming you and helping you take the next step towards a healthier, confident smile.
</p>
</td>
</tr>

<!-- FOOTER -->
<tr>
<td style="padding:32px 35px;background:#263a35;text-align:center;">
<div style="color:#c6a36a;font-size:10px;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px;">VISIT US</div>
<div style="color:#ffffff;font-family:Georgia, 'Times New Roman', serif;font-size:20px;line-height:1.5;margin-bottom:12px;">
Dr. Shadiya's Dental Clinic<br>& Implant Centre
</div>
<div style="color:rgba(255,255,255,.68);font-size:12px;line-height:1.8;">
Haya Tower,<br>Sastha Temple Road,<br>Manapattiparambu, Kaloor,<br>Kochi - 682018
</div>
</td>
</tr>

<tr>
<td style="padding:20px;text-align:center;background:#f7f5ef;">
<div style="color:#999999;font-size:10px;line-height:1.7;">
This is an automated appointment confirmation from Dr. Shadiya's Dental Clinic and Implant Centre.
</div>
</td>
</tr>

</table>
</td>
</tr>
</table>
</body>
</html>
"""

            email = EmailMultiAlternatives(
                subject=patient_subject,
                body=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[appointment.email],
            )
            email.attach_alternative(html_content, "text/html")
            email.send(fail_silently=True)

        except Exception as email_error:
            print("PATIENT EMAIL ERROR:", email_error)

    # 2. SEND NEW APPOINTMENT ALERT TO CLINIC
    try:
        clinic_subject = f"🔔 New Appointment | {appointment.name}"
        clinic_message = f"""
NEW APPOINTMENT BOOKED

Patient Details
-------------------------
Name: {appointment.name}
Phone: {appointment.phone}
Email: {appointment.email or 'Not provided'}

Appointment Details
-------------------------
Date: {appointment_date_text}
Time: {appointment_time_text}
Concern: {concern_text}

This appointment has been successfully booked through the clinic website.

Dr. Shadiya's Dental Clinic and Implant Centre
Haya Tower, Sastha Temple Road,
Manapattiparambu, Kaloor,
Kochi - 682018
"""

        send_mail(
            subject=clinic_subject,
            message=clinic_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=["dr.shadiya.shareef@gmail.com"],
            fail_silently=True,
        )

    except Exception as clinic_email_error:
        print("CLINIC EMAIL ERROR:", clinic_email_error)


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


# =========================================================
# BOOK APPOINTMENT
# =========================================================

def booking(request):

    if request.method == "POST":
        form = AppointmentForm(request.POST)

        if form.is_valid():

            appointment_date = form.cleaned_data["appointment_date"]
            appointment_time = form.cleaned_data["appointment_time"]

            today = timezone.localdate()
            current_time_str = timezone.localtime().strftime("%H:%M")
            selected_time_str = str(appointment_time)[:5]

            # -------------------------------------------------
            # 1. PREVENT BOOKING A DATE IN THE PAST
            # -------------------------------------------------

            if appointment_date < today:

                form.add_error(
                    "appointment_date",
                    "Please select a future date."
                )

            # -------------------------------------------------
            # 2. PREVENT BOOKING AN ELAPSED TIME ON TODAY'S DATE
            # -------------------------------------------------

            elif appointment_date == today and selected_time_str <= current_time_str:

                form.add_error(
                    "appointment_time",
                    "This time slot has already passed today. Please choose an upcoming time."
                )

            # -------------------------------------------------
            # 3. SUNDAY = HOLIDAY
            # -------------------------------------------------

            elif appointment_date.weekday() == 6:

                form.add_error(
                    "appointment_date",
                    "Sunday is a holiday. Please select another date."
                )

            else:

                # -------------------------------------------------
                # 4. CHECK WHETHER SLOT IS ALREADY BOOKED
                # -------------------------------------------------

                already_booked = Appointment.objects.filter(
                    appointment_date=appointment_date,
                    appointment_time=appointment_time,
                ).exists()

                if already_booked:

                    form.add_error(
                        "appointment_time",
                        "This time slot is already booked. Please choose another time."
                    )

                else:

                    try:

                        # -------------------------------------------------
                        # 5. SAVE APPOINTMENT ATOMICALLY (AVOIDS DOUBLE BOOKING)
                        # -------------------------------------------------

                        with transaction.atomic():
                            appointment = form.save()

                        # -------------------------------------------------
                        # SAVE APPOINTMENT ID IN SESSION
                        # -------------------------------------------------

                        request.session["appointment_id"] = appointment.id

                        # =================================================
                        # PREPARE FORMATTED TEXT DETAILS
                        # =================================================

                        appointment_date_text = (
                            appointment.appointment_date.strftime("%d %B %Y")
                        )

                        appointment_time_text = dict(
                            Appointment.TIME_CHOICES
                        ).get(
                            appointment.appointment_time,
                            str(appointment.appointment_time)
                        )

                        concern_text = appointment.get_concern_display()

                        # =================================================
                        # ASYNCHRONOUS EMAIL SENDING (NO USER LATENCY)
                        # =================================================

                        email_thread = threading.Thread(
                            target=send_booking_emails,
                            args=(
                                appointment,
                                appointment_date_text,
                                appointment_time_text,
                                concern_text,
                            ),
                        )
                        email_thread.daemon = True
                        email_thread.start()

                        # -------------------------------------------------
                        # REDIRECT TO SUCCESS PAGE IMMEDIATELY
                        # -------------------------------------------------

                        return redirect("booking_success")

                    except IntegrityError:

                        form.add_error(
                            "appointment_time",
                            "This time slot was just booked by another patient. Please select another time."
                        )

    else:

        form = AppointmentForm()

    return render(
        request,
        "booking.html",
        {"form": form}
    )


# =========================================================
# BOOKING SUCCESS
# =========================================================

def booking_success(request):

    appointment_id = request.session.get("appointment_id")

    if not appointment_id:
        return redirect("booking")

    try:

        appointment = Appointment.objects.get(
            id=appointment_id
        )

    except Appointment.DoesNotExist:

        return redirect("booking")

    return render(
        request,
        "booking_success.html",
        {"appointment": appointment}
    )


# =========================================================
# AVAILABLE APPOINTMENT TIMES
# =========================================================

def available_times(request):

    date_string = request.GET.get("date")

    if not date_string:

        return JsonResponse(
            {
                "available_times": [],
                "booked_times": [],
                "is_holiday": False,
                "message": "Date is required.",
            }
        )

    try:

        selected_date = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        ).date()

    except ValueError:

        return JsonResponse(
            {
                "available_times": [],
                "booked_times": [],
                "is_holiday": False,
                "message": "Invalid date.",
            }
        )

    today = timezone.localdate()
    now_time = timezone.localtime().time()

    # ---------------------------------------------------------
    # PREVENT PAST DATES
    # ---------------------------------------------------------

    if selected_date < today:

        return JsonResponse(
            {
                "available_times": [],
                "booked_times": [],
                "is_holiday": False,
                "message": "Please select a future date.",
            }
        )

    # ---------------------------------------------------------
    # SUNDAY = HOLIDAY
    # ---------------------------------------------------------

    if selected_date.weekday() == 6:

        return JsonResponse(
            {
                "available_times": [],
                "booked_times": [],
                "is_holiday": True,
                "message": "Sunday is a holiday. Please select another date.",
            }
        )

    # ---------------------------------------------------------
    # CREATE TIME SLOTS (09:30 AM to 06:30 PM)
    # ---------------------------------------------------------

    start_time = datetime.strptime(
        "09:30",
        "%H:%M"
    ).time()

    last_start_time = datetime.strptime(
        "18:30",
        "%H:%M"
    ).time()

    current_datetime = datetime.combine(
        selected_date,
        start_time
    )

    last_datetime = datetime.combine(
        selected_date,
        last_start_time
    )

    slots = []

    while current_datetime <= last_datetime:

        slot_time = current_datetime.time()

        # If date is today, exclude times that have already passed
        if selected_date == today:
            if slot_time > now_time:
                slots.append(slot_time)
        else:
            slots.append(slot_time)

        current_datetime += timedelta(
            hours=1
        )

    # ---------------------------------------------------------
    # GET BOOKED APPOINTMENTS
    # ---------------------------------------------------------

    booked_appointments = Appointment.objects.filter(
        appointment_date=selected_date
    )

    booked_times = []
    for app in booked_appointments:
        if app.appointment_time:
            if hasattr(app.appointment_time, "strftime"):
                booked_times.append(app.appointment_time.strftime("%H:%M"))
            else:
                booked_times.append(str(app.appointment_time)[:5])

    # ---------------------------------------------------------
    # GET AVAILABLE TIMES
    # ---------------------------------------------------------

    available_times_list = [
        {
            "value": slot.strftime("%H:%M"),
            "label": slot.strftime("%I:%M %p"),
        }
        for slot in slots
        if slot.strftime("%H:%M") not in booked_times
    ]

    return JsonResponse(
        {
            "available_times": available_times_list,
            "booked_times": booked_times,
            "is_holiday": False,
            "message": "",
        }
    )


# =========================================================
# TESTIMONIALS
# =========================================================

def testimonials(request):
    return render(
        request,
        "testimonial.html"
    )