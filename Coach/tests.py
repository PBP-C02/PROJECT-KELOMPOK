import json
import uuid
import datetime as dt
from decimal import Decimal
from io import BytesIO

from django.test import TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in
from django.db import models as djm
from django.contrib.auth.hashers import make_password

from PIL import Image

from Coach.models import Coach
from Coach.forms import CoachForm
from Coach.views import _to_int, _parse_time, _parse_dt_local, _to_decimal, validate_image


# ---------- Helpers ----------

def make_png_file(name: str = "test.png", size=(10, 10)):
    """Create a tiny valid PNG file as if uploaded by a user."""
    bio = BytesIO()
    img = Image.new("RGB", size)
    img.save(bio, format="PNG")
    bio.seek(0)
    return SimpleUploadedFile(name, bio.read(), content_type="image/png")


def make_future_datetime(days=1, hour=9, minute=0):
    now = timezone.now()
    base = now + dt.timedelta(days=days)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)


def make_user(nama: str = "Nama", phone: str = "081234567890", email: str | None = None,
              kelamin: str = "L", tanggal_lahir: dt.date | None = None):
    """
    Create a test user compatible with Coach.user ForeignKey.
    Works with custom User model from Auth_Profile.
    """
    from Auth_Profile.models import User
    
    if email is None:
        email = f"{uuid.uuid4().hex[:8]}@example.com"
    if tanggal_lahir is None:
        tanggal_lahir = dt.date(2000, 1, 1)

    user = User.objects.create(
        nama=nama,
        email=email,
        kelamin=kelamin,
        tanggal_lahir=tanggal_lahir,
        nomor_handphone=phone,
        password=make_password("xpass123") 
    )
    
    return user


def manual_login(client, user):
    """
    Manually log in a user by setting session variables.
    Compatible with custom User model and custom auth system.
    """

    session = client.session
    session['user_id'] = str(user.id)
    session.save()


# ---------- Unit tests for small helpers ----------

class HelperFunctionTests(TestCase):
    def test__to_int(self):
        self.assertEqual(_to_int("1.000"), 1000)
        self.assertEqual(_to_int("Rp 12.345"), 12345)
        self.assertIsNone(_to_int("abc"))
        self.assertIsNone(_to_int(None))

    def test__parse_time(self):
        self.assertEqual(_parse_time("14:30"), dt.time(14, 30))
        self.assertIsNone(_parse_time("25:00"))
        self.assertIsNone(_parse_time(None))

    def test__parse_dt_local(self):
        fut = make_future_datetime(days=10, hour=9, minute=15)
        s = fut.strftime("%Y-%m-%dT%H:%M")
        parsed = _parse_dt_local(s)
        self.assertIsNotNone(parsed)
        self.assertFalse(timezone.is_naive(parsed))
        self.assertEqual(
            parsed.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%dT%H:%M"),
            s,
        )
        self.assertIsNone(_parse_dt_local("invalid"))
        self.assertIsNone(_parse_dt_local(None))

    def test__to_decimal(self):
        self.assertEqual(_to_decimal("4.5"), Decimal("4.5"))
        self.assertEqual(_to_decimal("not_a_number"), Decimal("0"))
        self.assertEqual(_to_decimal(None), Decimal("0"))


class ImageValidationTests(TestCase):
    def test_validate_image_accepts_valid_png(self):
        f = make_png_file()
        cleaned = validate_image(f)
        self.assertIsNotNone(cleaned)

    def test_validate_image_rejects_large_file(self):
        big = SimpleUploadedFile("big.png", b"0" * (5 * 1024 * 1024 + 100), content_type="image/png")
        with self.assertRaises(ValidationError):
            validate_image(big)

    def test_validate_image_rejects_wrong_extension(self):
        f = make_png_file(name="test.txt")
        with self.assertRaises(ValidationError) as ctx:
            validate_image(f)
        self.assertIn("Invalid file type", str(ctx.exception))

    def test_validate_image_rejects_invalid_content(self):
        bad = SimpleUploadedFile("bad.png", b"notanimage", content_type="image/png")
        with self.assertRaises(ValidationError) as ctx:
            validate_image(bad)
        self.assertIn("Invalid image file", str(ctx.exception))


# ---------- Model tests ----------

class CoachModelTests(TestCase):
    def setUp(self):
        self.owner = make_user(nama="Owner", phone="081234567890")
        self.alice = make_user(nama="Alice", phone="082233445566")
        fut = make_future_datetime(days=5, hour=9)
        self.coach = Coach.objects.create(
            user=self.owner,
            title="Tennis 101",
            description="Intro",
            price=100000,
            category="tennis",
            location="Jakarta",
            address="Jl. Sudirman",
            mapsLink="https://maps.google.com/?q=-6.2,106.8",
            date=fut.date(),
            startTime=dt.time(9, 0),
            endTime=dt.time(10, 0),
            rating=Decimal("4.50"),
            instagram_link="https://instagram.com/coach",
        )

    def test_str(self):
        s = str(self.coach)
        self.assertIn("Tennis 101", s)

    def test_price_formatted(self):
        self.coach.price = 1500000
        self.assertEqual(self.coach.price_formatted, "Rp 1.500.000")

    def test_is_past_logic(self):
        # Future date
        future = Coach(
            user=self.owner,
            title="Future",
            description="x",
            price=1,
            category="tennis",
            location="JKT",
            address="addr",
            mapsLink="https://maps.google.com/?q=x",
            date=(timezone.now() + dt.timedelta(days=1)).date(),
            startTime=dt.time(9, 0),
            endTime=dt.time(10, 0),
        )
        future.full_clean()
        future.save()
        self.assertFalse(future.is_past)

        # Today
        today = Coach(
            user=self.owner,
            title="Today",
            description="x",
            price=1,
            category="tennis",
            location="JKT",
            address="addr",
            mapsLink="https://maps.google.com/?q=x",
            date=timezone.now().date(),
            startTime=dt.time(0, 0),
            endTime=dt.time(0, 1),
        )
        today.full_clean()
        today.save()
        self.assertIsInstance(today.is_past, bool)

    def test_get_whatsapp_link_and_phone_format(self):
        link = self.coach.get_whatsapp_link()
        self.assertIsNotNone(link)
        self.assertIn("https://wa.me/62", link)
        self.assertIn("Tennis%20101", link)
        self.assertEqual(self.coach.get_formatted_phone(), "0812-3456-7890")

    def test_clean_validations(self):
        # endTime <= startTime
        bad_time = Coach(
            user=self.owner,
            title="Bad",
            description="x",
            price=1,
            category="tennis",
            location="JKT",
            address="addr",
            mapsLink="https://maps.google.com/?q=x",
            date=(timezone.now() + dt.timedelta(days=1)).date(),
            startTime=dt.time(10, 0),
            endTime=dt.time(9, 0),
        )
        with self.assertRaises(ValidationError):
            bad_time.full_clean()

        # date in the past
        bad_date = Coach(
            user=self.owner,
            title="BadDate",
            description="x",
            price=1,
            category="tennis",
            location="JKT",
            address="adadr",
            mapsLink="https://maps.google.com/?q=x",
            date=(timezone.now() - dt.timedelta(days=1)).date(),
            startTime=dt.time(9, 0),
            endTime=dt.time(10, 0),
        )
        with self.assertRaises(ValidationError):
            bad_date.full_clean()

        # peserta == user
        same = Coach(
            user=self.owner,
            peserta=self.owner,
            title="Same",
            description="x",
            price=1,
            category="tennis",
            location="JKT",
            address="addr",
            mapsLink="https://maps.google.com/?q=x",
            date=(timezone.now() + dt.timedelta(days=1)).date(),
            startTime=dt.time(9, 0),
            endTime=dt.time(10, 0),
        )
        with self.assertRaises(ValidationError):
            same.full_clean()


# ---------- Form tests ----------

class CoachFormTests(TestCase):
    def setUp(self):
        self.future = (timezone.now() + dt.timedelta(days=3)).date()

    def test_valid_form(self):
        form = CoachForm(data={
            "title": "Valid",
            "price": 1000,
            "description": "Desc",
            "category": "tennis",
            "location": "Jakarta",
            "address": "Jl. X",
            "date": self.future.strftime("%Y-%m-%d"),
            "startTime": "09:00",
            "endTime": "10:00",
            "rating": "4.0",
            "instagram_link": "",
            "mapsLink": "https://maps.google.com/?q=-6.2,106.8",
        })
        self.assertTrue(form.is_valid(), form.errors.as_json())

    def test_invalid_title_and_description(self):
        form = CoachForm(data={
            "title": "   ",
            "price": 1000,
            "description": "",
            "category": "tennis",
            "location": "Jakarta",
            "address": "Jl. X",
            "date": self.future.strftime("%Y-%m-%d"),
            "startTime": "09:00",
            "endTime": "10:00",
            "rating": "3.0",
            "mapsLink": "https://maps.google.com/?q=-6.2,106.8",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("title", form.errors)
        self.assertIn("description", form.errors)

    def test_price_and_rating_bounds(self):
        form = CoachForm(data={
            "title": "X",
            "price": 0,
            "description": "Y",
            "category": "tennis",
            "location": "Jakarta",
            "address": "Jl. X",
            "date": self.future.strftime("%Y-%m-%d"),
            "startTime": "09:00",
            "endTime": "10:00",
            "rating": "3.0",
            "mapsLink": "https://maps.google.com/?q=-6.2,106.8",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Harga harus >= 1.", form.errors.get("price", []))

        form = CoachForm(data={
            "title": "X",
            "price": 1000,
            "description": "Y",
            "category": "tennis",
            "location": "Jakarta",
            "address": "Jl. X",
            "date": self.future.strftime("%Y-%m-%d"),
            "startTime": "09:00",
            "endTime": "10:00",
            "rating": "6.0",
            "mapsLink": "https://maps.google.com/?q=-6.2,106.8",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Rating harus antara 0 dan 5.", form.errors.get("rating", []))

    def test_time_order_in_form_clean(self):
        form = CoachForm(data={
            "title": "X",
            "price": 1000,
            "description": "Y",
            "category": "tennis",
            "location": "Jakarta",
            "address": "Jl. X",
            "date": self.future.strftime("%Y-%m-%d"),
            "startTime": "10:00",
            "endTime": "09:00",
            "rating": "3.0",
            "mapsLink": "https://maps.google.com/?q=-6.2,106.8",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("Waktu selesai harus lebih besar dari waktu mulai.", form.non_field_errors())


# ---------- View (JSON) tests ----------

@override_settings(
    AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'],
    MIDDLEWARE=[m for m in __import__('django.conf', fromlist=['settings']).settings.MIDDLEWARE 
                if 'SessionMiddleware' in m or 'AuthenticationMiddleware' in m]
)
class CoachJSONViewTests(TestCase):
    def setUp(self):
        self.owner = make_user(nama="Owner", phone="081234567890", email="owner@test.com")
        self.other = make_user(nama="Other", phone="082233445566", email="other@test.com")
        
        manual_login(self.client, self.owner)

        fut = make_future_datetime(days=4, hour=9)
        self.future_date_str = fut.strftime("%Y-%m-%dT%H:%M")

        self.coach = Coach.objects.create(
            user=self.owner,
            title="Owned",
            description="Desc",
            price=50000,
            category="tennis",
            location="Jakarta",
            address="Jl. X",
            mapsLink="https://maps.google.com/?q=-6.2,106.8",
            date=fut.date(),
            startTime=dt.time(9, 0),
            endTime=dt.time(10, 0),
            rating=Decimal("4.00"),
        )
    
    def test_show_main_renders(self):
        """Test show_main returns template"""
        url = reverse("coach:show_main")
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'coach/main.html')
        self.assertIn('user', resp.context)

    def test_add_coach_success(self):
        url = reverse("coach:add_coach")
        resp = self.client.post(url, data={
            "title": "New Coach",
            "description": "Nice",
            "category": "tennis",
            "location": "Bandung",
            "address": "Jl. Y",
            "price": "100000",
            "date": self.future_date_str,
            "startTime": "09:00",
            "endTime": "10:00",
            "rating": "4.5",
            "instagram_link": "",
            "mapsLink": "https://maps.google.com/?q=-6.9,107.6",
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertTrue(data["success"])
        self.assertIn("coach_id", data)
        self.assertIn("redirect_url", data)

    def test_add_coach_rejects_bad_inputs(self):
        url = reverse("coach:add_coach")

        # Bad price
        resp = self.client.post(url, data={
            "title": "X", "description": "Y", "category": "tennis",
            "location": "Z", "address": "A",
            "price": "abc",
            "date": self.future_date_str, "startTime": "09:00", "endTime": "10:00",
            "rating": "3.0", "mapsLink": "https://maps.google.com/?q=x",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

        # Bad date
        resp = self.client.post(url, data={
            "title": "X", "description": "Y", "category": "tennis",
            "location": "Z", "address": "A",
            "price": "100", "date": "not-a-date", "startTime": "09:00", "endTime": "10:00",
            "rating": "3.0", "mapsLink": "https://maps.google.com/?q=x",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

        # Bad time
        resp = self.client.post(url, data={
            "title": "X", "description": "Y", "category": "tennis",
            "location": "Z", "address": "A",
            "price": "100", "date": self.future_date_str,
            "startTime": "aa", "endTime": "bb",
            "rating": "3.0", "mapsLink": "https://maps.google.com/?q=x",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

        # End before start
        resp = self.client.post(url, data={
            "title": "X", "description": "Y", "category": "tennis",
            "location": "Z", "address": "A",
            "price": "100", "date": self.future_date_str,
            "startTime": "10:00", "endTime": "09:00",
            "rating": "3.0", "mapsLink": "https://maps.google.com/?q=x",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

        # Rating out of bounds
        resp = self.client.post(url, data={
            "title": "X", "description": "Y", "category": "tennis",
            "location": "Z", "address": "A",
            "price": "100", "date": self.future_date_str,
            "startTime": "09:00", "endTime": "10:00",
            "rating": "6", "mapsLink": "https://maps.google.com/?q=x",
        })
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

    def test_update_coach_permissions_and_changes(self):
        url = reverse("coach:update_coach", kwargs={"pk": self.coach.pk})
        
        # Non-owner -> 403
        manual_login(self.client, self.other)
        resp = self.client.post(url, data={"title": "Hack"})
        self.assertEqual(resp.status_code, 403)

        # Owner updates
        manual_login(self.client, self.owner)
        resp = self.client.post(url, data={
            "title": "Updated",
            "price": "75000",
            "rating": "4.8",
            "startTime": "09:30",
            "mapsLink": "https://maps.google.com/?q=1,1"
        })
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertTrue(data["success"])

        self.coach.refresh_from_db()
        self.assertEqual(self.coach.title, "Updated")
        self.assertEqual(self.coach.price, 75000)
        self.assertEqual(self.coach.rating, Decimal("4.8"))
        self.assertEqual(self.coach.startTime, dt.time(9, 30))

    def test_booking_flow_and_permissions(self):
        url = reverse("coach:book_coach", kwargs={"pk": self.coach.pk})
        
        # Book own coach -> 400
        manual_login(self.client, self.owner)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

        # Other user can book
        manual_login(self.client, self.other)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["success"])

        # Double booking -> 400
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

        # Cancel by non-peserta -> 403
        cancel_url = reverse("coach:cancel_booking", kwargs={"pk": self.coach.pk})
        manual_login(self.client, self.owner)
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, 403)

        # Cancel by peserta
        manual_login(self.client, self.other)
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_mark_available_unavailable_and_delete(self):
        mark_avail = reverse("coach:mark_available", kwargs={"pk": self.coach.pk})
        mark_unavail = reverse("coach:mark_unavailable", kwargs={"pk": self.coach.pk})
        delete_url = reverse("coach:delete_coach", kwargs={"pk": self.coach.pk})

        # Other user -> 403
        manual_login(self.client, self.other)
        self.assertEqual(self.client.post(mark_avail).status_code, 403)
        self.assertEqual(self.client.post(mark_unavail).status_code, 403)
        self.assertEqual(self.client.post(delete_url).status_code, 403)

        # Owner -> success
        manual_login(self.client, self.owner)
        resp = self.client.post(mark_unavail)
        self.assertEqual(resp.status_code, 200)
        self.coach.refresh_from_db()
        self.assertTrue(self.coach.isBooked)

        resp = self.client.post(mark_avail)
        self.assertEqual(resp.status_code, 200)
        self.coach.refresh_from_db()
        self.assertFalse(self.coach.isBooked)
        self.assertIsNone(self.coach.peserta)

        resp = self.client.post(delete_url)
        self.assertEqual(resp.status_code, 200)
        self.assertFalse(Coach.objects.filter(pk=self.coach.pk).exists())


# ==================== ADD NEW TEST CLASS FOR AJAX SEARCH ====================

@override_settings(
    AUTHENTICATION_BACKENDS=['django.contrib.auth.backends.ModelBackend'],
    MIDDLEWARE=[m for m in __import__('django.conf', fromlist=['settings']).settings.MIDDLEWARE 
                if 'SessionMiddleware' in m or 'AuthenticationMiddleware' in m]
)
class AjaxSearchCoachesTests(TestCase):
    """Test ajax_search_coaches endpoint"""
    
    def setUp(self):
        self.owner = make_user(nama="Owner", phone="081234567890", email="owner@test.com")
        self.other = make_user(nama="Other", phone="082233445566", email="other@test.com")
        
        manual_login(self.client, self.owner)
        
        fut = make_future_datetime(days=4, hour=9)
        
        # Create multiple coaches for testing
        self.coach1 = Coach.objects.create(
            user=self.owner,
            title="Tennis Coach Jakarta",
            description="Professional tennis coaching",
            price=50000,
            category="tennis",
            location="Jakarta",
            address="Jl. Sudirman",
            mapsLink="https://maps.google.com/?q=-6.2,106.8",
            date=fut.date(),
            startTime=dt.time(9, 0),
            endTime=dt.time(10, 0),
            rating=Decimal("4.50"),
        )
        
        self.coach2 = Coach.objects.create(
            user=self.other,
            title="Basketball Coach",
            description="Expert basketball training",
            price=75000,
            category="basketball",
            location="Bandung",
            address="Jl. Dago",
            mapsLink="https://maps.google.com/?q=-6.9,107.6",
            date=fut.date(),
            startTime=dt.time(10, 0),
            endTime=dt.time(11, 0),
            rating=Decimal("4.20"),
            isBooked=True,
        )
        
        self.coach3 = Coach.objects.create(
            user=self.owner,
            title="Soccer Coach Jakarta",
            description="Youth soccer training",
            price=100000,
            category="soccer",
            location="Jakarta",
            address="Jl. Gatot Subroto",
            mapsLink="https://maps.google.com/?q=-6.2,106.8",
            date=fut.date(),
            startTime=dt.time(14, 0),
            endTime=dt.time(15, 0),
            rating=Decimal("3.80"),
        )
    
    def test_ajax_search_all_coaches(self):
        """Test search without filters returns all coaches"""
        url = reverse("coach:ajax_search")
        resp = self.client.get(url)
        
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 3)
        self.assertEqual(len(data['coaches']), 3)
    
    def test_ajax_search_by_query(self):
        """Test search by text query"""
        url = reverse("coach:ajax_search")
        
        # Search by title
        resp = self.client.get(url, {'q': 'Tennis'})
        data = resp.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['coaches'][0]['title'], 'Tennis Coach Jakarta')
        
        # Search by location
        resp = self.client.get(url, {'q': 'Bandung'})
        data = resp.json()
        self.assertEqual(data['count'], 1)
        
        # Search by description
        resp = self.client.get(url, {'q': 'Expert'})
        data = resp.json()
        self.assertEqual(data['count'], 1)
    
    def test_ajax_search_by_location(self):
        """Test filter by location"""
        url = reverse("coach:ajax_search")
        resp = self.client.get(url, {'location': 'Jakarta'})
        
        data = resp.json()
        self.assertEqual(data['count'], 2)
        for coach in data['coaches']:
            self.assertEqual(coach['location'], 'Jakarta')
    
    def test_ajax_search_by_category(self):
        """Test filter by category"""
        url = reverse("coach:ajax_search")
        resp = self.client.get(url, {'category': 'tennis'})
        
        data = resp.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['coaches'][0]['category'], 'tennis')
    
    def test_ajax_search_by_price_range(self):
        """Test filter by price range"""
        url = reverse("coach:ajax_search")
        
        # Min price only
        resp = self.client.get(url, {'min_price': '60000'})
        data = resp.json()
        self.assertEqual(data['count'], 2)
        
        # Max price only
        resp = self.client.get(url, {'max_price': '60000'})
        data = resp.json()
        self.assertEqual(data['count'], 1)
        
        # Both min and max
        resp = self.client.get(url, {'min_price': '50000', 'max_price': '80000'})
        data = resp.json()
        self.assertEqual(data['count'], 2)
    
    def test_ajax_search_available_only(self):
        """Test filter available only"""
        url = reverse("coach:ajax_search")
        resp = self.client.get(url, {'available': 'true'})
        
        data = resp.json()
        self.assertEqual(data['count'], 2)
        for coach in data['coaches']:
            self.assertFalse(coach['is_booked'])
    
    def test_ajax_search_view_mode_my_bookings(self):
        """Test view mode: my bookings"""
        # Owner books coach2
        self.coach2.peserta = self.owner
        self.coach2.save()
        
        url = reverse("coach:ajax_search")
        resp = self.client.get(url, {'view': 'my_bookings'})
        
        data = resp.json()
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['coaches'][0]['id'], str(self.coach2.pk))
    
    def test_ajax_search_view_mode_my_coaches(self):
        """Test view mode: my coaches"""
        url = reverse("coach:ajax_search")
        resp = self.client.get(url, {'view': 'my_coaches'})
        
        data = resp.json()
        self.assertEqual(data['count'], 2)
        for coach in data['coaches']:
            self.assertTrue(coach['is_owner'])
    
    def test_ajax_search_sorting(self):
        """Test sorting"""
        url = reverse("coach:ajax_search")
        
        # Sort by price ascending
        resp = self.client.get(url, {'sort': 'price_asc'})
        data = resp.json()
        prices = [coach['price'] for coach in data['coaches']]
        self.assertEqual(prices, sorted(prices))
        
        # Sort by price descending
        resp = self.client.get(url, {'sort': 'price_desc'})
        data = resp.json()
        prices = [coach['price'] for coach in data['coaches']]
        self.assertEqual(prices, sorted(prices, reverse=True))
    
    def test_ajax_search_combined_filters(self):
        """Test multiple filters combined"""
        url = reverse("coach:ajax_search")
        resp = self.client.get(url, {
            'location': 'Jakarta',
            'category': 'tennis',
            'available': 'true',
            'max_price': '60000'
        })
        
        data = resp.json()
        self.assertEqual(data['count'], 1)
        coach = data['coaches'][0]
        self.assertEqual(coach['location'], 'Jakarta')
        self.assertEqual(coach['category'], 'tennis')
        self.assertFalse(coach['is_booked'])
        self.assertLessEqual(coach['price'], 60000)
    
    def test_ajax_search_no_results(self):
        """Test search with no matching results"""
        url = reverse("coach:ajax_search")
        resp = self.client.get(url, {'q': 'NonexistentCoach'})
        
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 0)
        self.assertEqual(len(data['coaches']), 0)
    
    def test_ajax_search_response_structure(self):
        """Test response data structure"""
        url = reverse("coach:ajax_search")
        resp = self.client.get(url)
        
        data = resp.json()
        self.assertIn('success', data)
        self.assertIn('coaches', data)
        self.assertIn('count', data)
        
        # Check coach object structure
        coach = data['coaches'][0]
        required_fields = [
            'id', 'title', 'description', 'category', 'category_display',
            'location', 'address', 'price', 'price_formatted', 'date',
            'date_formatted', 'start_time', 'end_time', 'rating',
            'is_booked', 'image_url', 'user_name', 'user_id',
            'is_owner', 'detail_url', 'edit_url'
        ]
        for field in required_fields:
            self.assertIn(field, coach)


# ==================== URL RESOLUTION TESTS ====================

class URLResolutionTests(TestCase):
    def test_named_urls_reverse(self):
        self.assertTrue(reverse("coach:show_main").startswith("/"))
        self.assertTrue(reverse("coach:ajax_search").startswith("/"))
        
        fake_pk = uuid.uuid4()
        reverse("coach:create_coach_page")
        reverse("coach:add_coach")
        reverse("coach:edit_coach_page", kwargs={"pk": fake_pk})
        reverse("coach:update_coach", kwargs={"pk": fake_pk})
        reverse("coach:book_coach", kwargs={"pk": fake_pk})
        reverse("coach:cancel_booking", kwargs={"pk": fake_pk})
        reverse("coach:mark_available", kwargs={"pk": fake_pk})
        reverse("coach:mark_unavailable", kwargs={"pk": fake_pk})
        reverse("coach:delete_coach", kwargs={"pk": fake_pk})
        reverse("coach:coach_detail", kwargs={"pk": fake_pk})
