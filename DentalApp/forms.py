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
                'class': 'form-control',
                'placeholder': 'Enter your full name',
            }),

            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your WhatsApp / phone number',
            }),

            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter your email address (optional)',
            }),

            'other_concern': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Please tell us what you need help with',
            }),

            'appointment_date': forms.DateInput(
                attrs={
                    'class': 'date-input',
                    'type': 'date',
                }
            ),

            'appointment_time': forms.Select(
                attrs={
                    'class': 'form-control',
                }
            ),
        }

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

            'concern': forms.RadioSelect(),

            'other_concern': forms.Textarea(attrs={
                'placeholder': 'Please tell us briefly about your concern...',
                'class': 'form-control',
                'rows': 4
            }),

            'appointment_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),

            'appointment_time': forms.Select(attrs={
                'class': 'form-control'
            }),
        }

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