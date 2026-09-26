from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('navbar', views.base, name='base'),
    path('about', views.about, name='about'),
    path('treatments', views.treatments, name='treatments'),
    path('contact', views.contact, name='contact'),
    path(
        'book-appointment/',
        views.booking,
        name='booking'
    ),

    path(
        'booking-success/',
        views.booking_success,
        name='booking_success'
    ),

    path(
        'available-times/',
        views.available_times,
        name='available_times'
    ),

    path('testimonials/', views.testimonials, name='testimonial'),

    
]