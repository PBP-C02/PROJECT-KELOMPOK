from django import forms
from .models import EventRegistration, EventReview, Event


class EventSearchForm(forms.Form):
    """Form untuk search dan filter events"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cari event mabar...'
        })
    )
    
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pilih Kota'
        })
    )
    
    category = forms.ChoiceField(
        required=False,
        choices=[('', 'Semua Olahraga')] + Event.CATEGORY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    level = forms.ChoiceField(
        required=False,
        choices=[('', 'Semua Level')] + Event.LEVEL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    sort = forms.ChoiceField(
        required=False,
        choices=[
            ('date', 'Waktu dan Tanggal'),
            ('price_low', 'Harga Terendah'),
            ('price_high', 'Harga Tertinggi'),
            ('participants', 'Paling Ramai'),
        ],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class EventRegistrationForm(forms.ModelForm):
    """Form untuk pendaftaran event"""
    class Meta:
        model = EventRegistration
        fields = ['notes', 'payment_proof']
        widgets = {
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Catatan tambahan (opsional)',
                'rows': 3
            }),
            'payment_proof': forms.FileInput(attrs={
                'class': 'form-control'
            })
        }
        labels = {
            'notes': 'Catatan',
            'payment_proof': 'Bukti Transfer (jika sudah bayar)'
        }


class EventReviewForm(forms.ModelForm):
    """Form untuk review event"""
    class Meta:
        model = EventReview
        fields = ['rating', 'comment']
        widgets = {
            'rating': forms.Select(
                choices=[(i, f"{i} ★") for i in range(1, 6)],
                attrs={'class': 'form-control'}
            ),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'placeholder': 'Bagikan pengalaman kamu...',
                'rows': 4
            })
        }
        labels = {
            'rating': 'Rating',
            'comment': 'Review'
        }