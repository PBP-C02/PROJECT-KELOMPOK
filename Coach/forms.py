from django import forms
from django.forms import ModelForm
from Coach.models import Coach
from django.utils.html import strip_tags

class CoachForm(ModelForm):
    class Meta: 
        model = Coach
        fields = ["title", "price", "image", "description", "category", "location", "address", "date", "startTime", "endTime", "rating", "instagram_link", "mapsLink"]  
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'startTime': forms.TimeInput(attrs={'type': 'time'}),
            'endTime': forms.TimeInput(attrs={'type': 'time'}),
            'rating': forms.NumberInput(attrs={'step': '0.1', 'min': '0', 'max': '5'}),
            'instagram_link': forms.URLInput(attrs={'placeholder': 'https://instagram.com/username'}),
            'mapsLink': forms.URLInput(attrs={'placeholder': 'https://maps.google.com/?q=-6.2,106.8'}), 
        }

    def clean_title(self):
        title = strip_tags(self.cleaned_data.get("title", "")).strip()
        if not title:
            raise forms.ValidationError("Judul tidak boleh kosong.")
        return title

    def clean_description(self):
        desc = strip_tags(self.cleaned_data.get("description", "")).strip()
        if not desc:
            raise forms.ValidationError("Deskripsi tidak boleh kosong.")
        return desc

    def clean_price(self):
        price = self.cleaned_data.get("price")
        if price is None or price < 1:
            raise forms.ValidationError("Harga harus >= 1.")
        return price
    
    def clean_rating(self):
        rating = self.cleaned_data.get("rating")
        if rating is not None:
            if rating < 0 or rating > 5:
                raise forms.ValidationError("Rating harus antara 0 dan 5.")
        return rating or 0
    
    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('startTime')
        end = cleaned_data.get('endTime')
        
        if start and end and end <= start:
            raise forms.ValidationError("Waktu selesai harus lebih besar dari waktu mulai.")
        
        return cleaned_data