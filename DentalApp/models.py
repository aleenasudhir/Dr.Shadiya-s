from django.db import models


class Appointment(models.Model):

    CONCERN_CHOICES = [
        ('aligners', 'Aligners'),
        ('whitening', 'Teeth Whitening'),
        ('implants', 'Dental Implants'),
        ('cleaning', 'Cleaning / Scaling'),
        ('general', 'Tooth Pain / General Consultation'),
        ('other', 'Other'),
    ]

    TIME_CHOICES = [
    ('09:30', '09:30 AM'),
    ('10:30', '10:30 AM'),
    ('11:30', '11:30 AM'),
    ('12:30', '12:30 PM'),
    ('13:30', '01:30 PM'),
    ('14:30', '02:30 PM'),
    ('15:30', '03:30 PM'),
    ('16:30', '04:30 PM'),
    ('17:30', '05:30 PM'),
    ('18:30', '06:30 PM'),
]

    name = models.CharField(max_length=150)

    phone = models.CharField(max_length=20)

    email = models.EmailField(
        blank=True,
        null=True
    )

    concern = models.CharField(
        max_length=30,
        choices=CONCERN_CHOICES
    )

    other_concern = models.TextField(
        blank=True,
        null=True
    )

    appointment_date = models.DateField()

    appointment_time = models.CharField(
        max_length=5,
        choices=TIME_CHOICES
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=[
                    'appointment_date',
                    'appointment_time'
                ],
                name='unique_appointment_slot'
            )
        ]

        ordering = [
            'appointment_date',
            'appointment_time'
        ]

    def __str__(self):
        return f"{self.name} - {self.appointment_date} - {self.appointment_time}"