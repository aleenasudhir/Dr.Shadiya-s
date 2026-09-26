import requests
from django.conf import settings


def format_phone_number(phone):
    """
    Converts the patient's phone number into the format
    required by WhatsApp Cloud API.

    Example:
    +91 9895420118  -> 919895420118
    9895420118      -> 919895420118
    """

    if not phone:
        return None

    phone = (
        str(phone)
        .replace("+", "")
        .replace(" ", "")
        .replace("-", "")
        .replace("(", "")
        .replace(")", "")
    )

    # If Indian 10-digit number is entered without country code
    if len(phone) == 10:
        phone = "91" + phone

    return phone


def send_whatsapp_confirmation(appointment):

    phone_number = format_phone_number(
        appointment.phone
    )

    if not phone_number:
        return False, "Phone number is missing."

    appointment_date = (
        appointment.appointment_date.strftime(
            "%d %B %Y"
        )
    )

    appointment_time = dict(
        appointment.TIME_CHOICES
    ).get(
        appointment.appointment_time
    )

    treatment = appointment.get_concern_display()

    url = (
        f"https://graph.facebook.com/"
        f"{settings.WHATSAPP_API_VERSION}/"
        f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": (
            f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"
        ),
        "Content-Type": "application/json",
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",

        "template": {
            "name": "appointment_confirmation",

            "language": {
                "code": "en_US"
            },

            "components": [
                {
                    "type": "body",

                    "parameters": [

                        {
                            "type": "text",
                            "text": appointment.name
                        },

                        {
                            "type": "text",
                            "text": appointment_date
                        },

                        {
                            "type": "text",
                            "text": appointment_time
                        },

                        {
                            "type": "text",
                            "text": treatment
                        }

                    ]
                }
            ]
        }
    }

    try:

        response = requests.post(
            url,
            headers=headers,
            json=data,
            timeout=15
        )

        if response.ok:
            return True, "WhatsApp confirmation sent."

        return False, response.text

    except requests.RequestException as error:

        return False, str(error)