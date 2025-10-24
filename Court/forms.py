from decimal import Decimal

from django import forms

from .models import Court


class CourtForm(forms.ModelForm):
    maps_link = forms.URLField(
        required=False,
        label='Google Maps link',
        help_text='Paste a Google Maps link to automatically fill coordinates.',
    )
<<<<<<< HEAD

=======
    #Uji push
>>>>>>> 2421d735e02c9f7b3b1461aea5bd2fc3c8dbc5e4
    class Meta:
        model = Court
        fields = [
            'name',
            'sport_type',
            'location',
            'address',
            'price_per_hour',
            'facilities',
            'rating',
            'description',
            'image',
        ]
        field_classes = {
            'image': forms.FileField,
        }
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'name': forms.TextInput(attrs={'placeholder': 'Court name'}),
            'location': forms.TextInput(attrs={'placeholder': 'City'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Complete address'}),
            'price_per_hour': forms.NumberInput(attrs={'placeholder': 'Price per hour (IDR)', 'step': '0.01'}),
            'facilities': forms.TextInput(attrs={'placeholder': 'Facilities (comma separated)'}),
            'rating': forms.NumberInput(attrs={'placeholder': 'Rating (optional)', 'step': '0.1', 'min': '0', 'max': '5'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        optional_fields = ['facilities', 'rating', 'description', 'image']
        for field in optional_fields:
            self.fields[field].required = False
        self.fields['maps_link'].widget.attrs.update({
            'placeholder': 'https://maps.google.com/?q=-6.2,106.8'
        })

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        return rating if rating is not None else Decimal('0')

    def clean_facilities(self):
        return self.cleaned_data.get('facilities') or ''

    def clean_description(self):
        return self.cleaned_data.get('description') or ''
