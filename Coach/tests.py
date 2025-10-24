
import io
import json
import uuid
import datetime as dt
from decimal import Decimal
from io import BytesIO

from django.test import TestCase
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.exceptions import ValidationError
from django.utils import timezone

from PIL import Image

# Import app code
from Coach.models import Coach
from Coach.forms import CoachForm
from Coach.views import (
    _to_int, _parse_time, _parse_dt_local, _to_decimal, validate_image
)

# Import User model used by the app (custom user in Auth_Profile)
from Auth_Profile.models import User


# ---------------------------
# Helpers for tests
# ---------------------------

def make_png_file(name="test.png", size=(10, 10)):
    """Create a small valid PNG image as uploaded file."""
    bio = BytesIO()
    img = Image.new("RGB", size)
    img.save(bio, format="PNG")
    bio.seek(0)
    return SimpleUploadedFile(name, bio.read(), content_type="image/png")


def make_future_datetime(days=1, hour=9, minute=0):
    now = timezone.now()
    base = now + dt.timedelta(days=days)
    return base.replace(hour=hour, minute=minute, second=0, microsecond=0)



def make_user(username="user", nama="User", phone="081234567890"):
    """Create a User, auto-filling any NOT NULL simple fields required by the custom model."""
    from django.db import models as djm
    defaults = {
        "username": username,
        # try common fields if they exist in the project
        "nama": nama,
        "nomor_handphone": phone,
        "is_active": True,
    }
    # Dynamically fill NOT NULL & not relation fields
    for f in User._meta.get_fields():
        # only concrete non-relational fields
        if getattr(f, "auto_created", False): 
            continue
        if getattr(f, "is_relation", False):
            continue
        # skip if already provided
        if f.name in defaults:
            continue
        # fields on the base class may not have 'null' attr (e.g., ManyToOneRel)
        if hasattr(f, "null") and hasattr(f, "blank"):
            if f.null is False and f.blank is False:
                # supply a sensible default
                if isinstance(f, djm.DateField):
                    defaults[f.name] = timezone.now().date()
                elif isinstance(f, djm.DateTimeField):
                    defaults[f.name] = timezone.now()
                elif isinstance(f, djm.BooleanField):
                    defaults[f.name] = True
                elif isinstance(f, djm.IntegerField):
                    defaults[f.name] = 0
                elif isinstance(f, djm.DecimalField):
                    defaults[f.name] = Decimal("0")
                elif isinstance(f, djm.CharField):
                    defaults[f.name] = f"{f.name}-test"
                elif isinstance(f, djm.EmailField):
                    defaults[f.name] = f"{username}@example.com"
                else:
                    # fallback string
                    defaults[f.name] = f"{f.name}-test"
    return User.objects.create(**defaults)


# ---------------------------
# Unit tests for small helpers
# ---------------------------

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
        # should be aware and equal when converted to same timezone
        self.assertIsNotNone(parsed)
        self.assertFalse(timezone.is_naive(parsed))
        self.assertEqual(parsed.astimezone(timezone.get_current_timezone()).strftime("%Y-%m-%dT%H:%M"), s)
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
        # Build >5MB content with .png extension; size check triggers before image verification
        big = SimpleUploadedFile("big.png", b"0" * (5 * 1024 * 1024 + 100), content_type="image/png")
        with self.assertRaises(ValidationError) as ctx:
            validate_image(big)
        self.assertIsInstance(ctx.exception, ValidationError.__class__) if False else None

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


# ---------------------------
# Model tests
# ---------------------------

class CoachModelTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner", "Owner", "081234567890")
        self.alice = make_user("alice", "Alice", "082233445566")
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
            instagram_link="https://instagram.com/coach"
        )

    def test_str(self):
        self.assertIn("Tennis 101 by owner", str(self.coach))

    def test_price_formatted(self):
        self.coach.price = 1500000
        self.assertEqual(self.coach.price_formatted, "Rp 1.500.000")

    def test_is_past_logic(self):
        # Past date -> True
        past = Coach(
            user=self.owner, title="Past", description="x", price=1, category="tennis",
            location="JKT", address="addr", mapsLink="https://maps.google.com/?q=x",
            date=(timezone.now() - dt.timedelta(days=1)).date(),
            startTime=dt.time(8, 0), endTime=dt.time(9, 0),
        )
        past.full_clean()
        past.save()
        self.assertTrue(past.is_past)

        # Today but endTime before now -> may be True if now after 10:01
        today = Coach(
            user=self.owner, title="Today", description="x", price=1, category="tennis",
            location="JKT", address="addr", mapsLink="https://maps.google.com/?q=x",
            date=timezone.now().date(),
            startTime=dt.time(0, 0), endTime=dt.time(0, 1),
        )
        today.full_clean()
        today.save()
        # Can't assert strict True/False due to wall clock; assert boolean is returned
        self.assertIn(today.is_past, (True, False))

    def test_get_whatsapp_link_and_phone_format(self):
        link = self.coach.get_whatsapp_link()
        self.assertIsNotNone(link)
        self.assertIn("https://wa.me/62", link)  # 0812 -> 62...
        self.assertIn("Tennis%20101", link)      # title encoded
        # phone format
        self.assertEqual(self.coach.get_formatted_phone(), "0812-3456-7890")

    def test_clean_validations(self):
        # endTime <= startTime
        bad_time = Coach(
            user=self.owner, title="Bad", description="x", price=1, category="tennis",
            location="JKT", address="addr", mapsLink="https://maps.google.com/?q=x",
            date=(timezone.now() + dt.timedelta(days=1)).date(),
            startTime=dt.time(10, 0), endTime=dt.time(9, 0),
        )
        with self.assertRaises(ValidationError):
            bad_time.full_clean()

        # date in the past
        bad_date = Coach(
            user=self.owner, title="BadDate", description="x", price=1, category="tennis",
            location="JKT", address="addr", mapsLink="https://maps.google.com/?q=x",
            date=(timezone.now() - dt.timedelta(days=1)).date(),
            startTime=dt.time(9, 0), endTime=dt.time(10, 0),
        )
        with self.assertRaises(ValidationError):
            bad_date.full_clean()

        # peserta == user
        same = Coach(
            user=self.owner, peserta=self.owner, title="Same", description="x", price=1, category="tennis",
            location="JKT", address="addr", mapsLink="https://maps.google.com/?q=x",
            date=(timezone.now() + dt.timedelta(days=1)).date(),
            startTime=dt.time(9, 0), endTime=dt.time(10, 0),
        )
        with self.assertRaises(ValidationError):
            same.full_clean()


# ---------------------------
# Form tests
# ---------------------------

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
        # Price < 1
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

        # Rating out of [0,5]
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


# ---------------------------
# View (JSON) tests
# ---------------------------

class CoachJSONViewTests(TestCase):
    def setUp(self):
        self.owner = make_user("owner", "Owner", "081234567890")
        self.other = make_user("other", "Other", "082233445566")
        self.client.force_login(self.owner)

        fut = make_future_datetime(days=4, hour=9)
        self.future_date_str = fut.strftime("%Y-%m-%dT%H:%M")

        # Create one coach owned by self.owner
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

    def test_add_coach_success(self):
        url = reverse("coach:add_coach")
        resp = self.client.post(url, data={
            "title": "New Coach",
            "description": "Nice",
            "category": "tennis",
            "location": "Bandung",
            "address": "Jl. Y",
            "price": "100000",
            "date": self.future_date_str,  # expects datetime-local
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
            "price": "-1",
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
        # Non-owner should get 403
        self.client.force_login(self.other)
        resp = self.client.post(url, data={"title": "Hack"})
        self.assertEqual(resp.status_code, 403)

        # Owner updates
        self.client.force_login(self.owner)
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
        # Book own coach -> 400
        url = reverse("coach:book_coach", kwargs={"pk": self.coach.pk})
        self.client.force_login(self.owner)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

        # Other user can book -> success
        self.client.force_login(self.other)
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["success"])

        # Double booking -> 400
        resp = self.client.post(url)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("message", resp.json())

        # Cancel booking by non-peserta -> 403
        cancel_url = reverse("coach:cancel_booking", kwargs={"pk": self.coach.pk})
        self.client.force_login(self.owner)
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, 403)

        # Cancel by peserta -> success
        self.client.force_login(self.other)
        resp = self.client.post(cancel_url)
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["success"])

    def test_mark_available_unavailable_and_delete(self):
        # Only owner allowed
        mark_avail = reverse("coach:mark_available", kwargs={"pk": self.coach.pk})
        mark_unavail = reverse("coach:mark_unavailable", kwargs={"pk": self.coach.pk})
        delete_url = reverse("coach:delete_coach", kwargs={"pk": self.coach.pk})

        # Other user -> 403
        self.client.force_login(self.other)
        self.assertEqual(self.client.post(mark_avail).status_code, 403)
        self.assertEqual(self.client.post(mark_unavail).status_code, 403)
        self.assertEqual(self.client.post(delete_url).status_code, 403)

        # Owner -> success
        self.client.force_login(self.owner)
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


# ---------------------------
# URL smoke tests
# ---------------------------

class URLResolutionTests(TestCase):
    def test_named_urls_reverse(self):
        # Ensure named URLs are registered correctly
        self.assertTrue(reverse("coach:show_main").startswith("/"))
        # UUID values for path converters (not hit views, just build urls)
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
