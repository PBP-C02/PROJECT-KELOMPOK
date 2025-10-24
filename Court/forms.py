from decimal import Decimal

from django import forms

from .models import Court


BASE_INPUT_CLASSES = (
    "w-full rounded-2xl border border-slate-200 bg-white/90 px-4 py-3 text-sm "
    "text-slate-800 shadow-inner outline-none transition focus:border-lime-300 "
    "focus:ring-4 focus:ring-lime-200/60"
)
TEXTAREA_CLASSES = BASE_INPUT_CLASSES + " min-h-[8rem] resize-y"
FILE_INPUT_CLASSES = (
    "block w-full text-sm text-slate-700 file:mr-4 file:rounded-full file:border-0 "
    "file:bg-lime-200/80 file:px-4 file:py-2 file:text-sm file:font-semibold "
    "file:text-slate-900 hover:file:bg-lime-200"
)


def sanitize_phone_input(value):
    """Normalize phone number string to digits only."""
    if value in (None, '', 'null'):
        return ''
    digits = ''.join(ch for ch in str(value).strip() if ch.isdigit())
    return digits


class CourtForm(forms.ModelForm):
    maps_link = forms.URLField(
        required=False,
        label='Google Maps link',
        help_text='Paste a Google Maps link to automatically fill coordinates.',
    )
    #Uji push
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
            'owner_phone',
            'image',
        ]
        field_classes = {
            'image': forms.FileField,
        }
        widgets = {
            'name': forms.TextInput(attrs={
                'placeholder': 'Nama lapangan',
                'class': BASE_INPUT_CLASSES,
            }),
            'sport_type': forms.Select(attrs={
                'class': BASE_INPUT_CLASSES,
            }),
            'location': forms.TextInput(attrs={
                'placeholder': 'Kota',
                'class': BASE_INPUT_CLASSES,
            }),
            'address': forms.Textarea(attrs={
                'placeholder': 'Alamat lengkap',
                'class': TEXTAREA_CLASSES,
            }),
            'price_per_hour': forms.NumberInput(attrs={
                'placeholder': 'Harga per jam (IDR)',
                'min': '0',
                'step': '0.01',
                'class': BASE_INPUT_CLASSES,
            }),
            'facilities': forms.TextInput(attrs={
                'placeholder': 'Lapangan indoor, Ruang ganti, Parkir luas',
                'class': BASE_INPUT_CLASSES,
            }),
            'rating': forms.NumberInput(attrs={
                'placeholder': 'Nilai 1 - 5',
                'step': '0.1',
                'min': '1',
                'max': '5',
                'class': BASE_INPUT_CLASSES,
            }),
            'description': forms.Textarea(attrs={
                'placeholder': 'Deskripsi singkat, keunggulan, dsb.',
                'class': TEXTAREA_CLASSES,
            }),
            'owner_phone': forms.TextInput(attrs={
                'placeholder': 'Contoh: 081234567890',
                'type': 'tel',
                'inputmode': 'numeric',
                'class': BASE_INPUT_CLASSES,
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': FILE_INPUT_CLASSES,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        optional_fields = ['facilities', 'rating', 'description', 'image']
        for field in optional_fields:
            self.fields[field].required = False
        self.fields['maps_link'].widget.attrs.update({
            'placeholder': 'https://maps.google.com/?q=-6.2,106.8',
            'class': BASE_INPUT_CLASSES,
        })

    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating in (None, ''):
            return Decimal('0')
        if rating < Decimal('1') or rating > Decimal('5'):
            raise forms.ValidationError('Rating harus berada di antara 1 dan 5.')
        return rating

    def clean_price_per_hour(self):
        price = self.cleaned_data.get('price_per_hour')
        if price is None:
            return price
        if price < Decimal('0'):
            raise forms.ValidationError('Harga per jam tidak boleh bernilai negatif.')
        return price

    def clean_owner_phone(self):
        phone_raw = self.cleaned_data.get('owner_phone', '')
        phone = sanitize_phone_input(phone_raw)
        if not phone:
            raise forms.ValidationError('Nomor kontak wajib diisi.')
        if len(phone) < 8:
            raise forms.ValidationError('Nomor telepon terlalu pendek.')
        if len(phone) > 20:
            raise forms.ValidationError('Nomor telepon terlalu panjang.')
        return phone

    def clean_facilities(self):
        return self.cleaned_data.get('facilities') or ''

    def clean_description(self):
        return self.cleaned_data.get('description') or ''
