from django import forms
from .models import Event

class EventForm(forms.ModelForm):
    class Meta:
        model = Event
        fields = ['title', 'description', 'category', 'date', 'time', 
                  'location', 'max_participants', 'image']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Enter event title'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-input',
                'rows': 4,
                'placeholder': 'Describe your event...'
            }),
            'category': forms.Select(attrs={
                'class': 'form-input'
            }),
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-input'
            }),
            'time': forms.TimeInput(attrs={
                'type': 'time',
                'class': 'form-input'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'Event location'
            }),
            'max_participants': forms.NumberInput(attrs={
                'class': 'form-input',
                'min': 2,
                'placeholder': 'Maximum participants'
            }),
            'image': forms.FileInput(attrs={
                'class': 'form-input',
                'accept': 'image/*'
            })
        }
        labels = {
            'title': 'Event Title',
            'description': 'Description',
            'category': 'Sport Category',
            'date': 'Event Date',
            'time': 'Event Time',
            'location': 'Location',
            'max_participants': 'Max Participants',
            'image': 'Event Image'
        }