from django import forms
from .models import Appointment


class AppointmentForm(forms.ModelForm):

    CONCERN_CHOICES = [
        ('aligners', 'Aligners'),
        ('braces', 'Braces'),
        ('whitening', 'Teeth Whitening'),
        ('implants', 'Dental Implants'),
        ('cleaning', 'Cleaning / Scaling'),
        ('general', 'Tooth Pain / General Consultation'),
        ('other', 'Other'),
    ]

    concern = forms.ChoiceField(
        choices=CONCERN_CHOICES,
        widget=forms.RadioSelect
    )

    # Use CharField so Django keeps it as exact text '13:30' (no seconds added)
    appointment_time = forms.CharField(
        widget=forms.HiddenInput(attrs={'id': 'id_appointment_time'})
    )

    class Meta:
        model = Appointment
        fields = [
            'name',
            'phone',
            'email',
            'concern',
            'other_concern',
            'appointment_date',
            'appointment_time',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Your full name',
                'class': 'form-control'
            }),
            'phone': forms.TextInput(attrs={
                'placeholder': 'WhatsApp / Phone number',
                'class': 'form-control'
            }),
            'email': forms.EmailInput(attrs={
                'placeholder': 'Email address',
                'class': 'form-control'
            }),
            'other_concern': forms.Textarea(attrs={
                'placeholder': 'Please tell us briefly about your concern...',
                'class': 'form-control',
                'rows': 4
            }),
            'appointment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
        }

    # Clean function placed directly inside the form class
    def clean_appointment_time(self):
        time = self.cleaned_data.get("appointment_time")
        if time:
            # Strips any extra seconds down to "HH:MM"
            return str(time)[:5]
        return time

    def clean(self):
        cleaned_data = super().clean()
        concern = cleaned_data.get('concern')
        other_concern = cleaned_data.get('other_concern')

        if concern == 'other' and not other_concern:
            self.add_error(
                'other_concern',
                'Please tell us briefly about your concern.'
            )

        return cleaned_data