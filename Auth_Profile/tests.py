
import json
from datetime import date
from django.test import TestCase, Client
from django.urls import reverse, resolve
from django.contrib.auth.hashers import make_password
from Auth_Profile.models import User
from Auth_Profile import views


class AuthProfileURLTests(TestCase):
    def test_url_names_resolve(self):
        self.assertEqual(resolve(reverse("Auth_Profile:homepage")).func, views.homepage_view)
        self.assertEqual(resolve(reverse("Auth_Profile:login")).func, views.login_view)
        self.assertEqual(resolve(reverse("Auth_Profile:register")).func, views.register_view)
        self.assertEqual(resolve(reverse("Auth_Profile:logout")).func, views.logout_view)
        self.assertEqual(resolve(reverse("Auth_Profile:profile_display")).func, views.profile_display_view)
        self.assertEqual(resolve(reverse("Auth_Profile:profile_edit")).func, views.profile_edit_view)


class UserModelTests(TestCase):
    def test_str_returns_email(self):
        u = User.objects.create(
            nama="Elliot",
            email="elliot@example.com",
            kelamin="L",
            tanggal_lahir="2004-01-02",
            nomor_handphone="08123456789",
            password=make_password("supersecret"),
        )
        self.assertEqual(str(u), "elliot@example.com")


class BaseAuthTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.password_plain = "verystrongpassword"
        self.user = User.objects.create(
            nama="Tester",
            email="tester@example.com",
            kelamin="L",
            tanggal_lahir="2000-12-31",
            nomor_handphone="0811223344",
            password=make_password(self.password_plain),
        )

    def login_session(self):
        """Simulate an authenticated session by setting session keys."""
        session = self.client.session
        session["user_id"] = str(self.user.id)
        session["email"] = self.user.email
        session["nama"] = self.user.nama
        session["kelamin"] = self.user.kelamin
        session["tanggal_lahir"] = str(self.user.tanggal_lahir)
        session["nomor_handphone"] = self.user.nomor_handphone
        session.save()


class HomepageViewTests(BaseAuthTestCase):
    def test_redirect_to_login_if_not_logged_in(self):
        url = reverse("Auth_Profile:homepage")
        res = self.client.get(url, follow=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse("Auth_Profile:login"))

    def test_homepage_renders_when_logged_in(self):
        self.login_session()
        res = self.client.get(reverse("Auth_Profile:homepage"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("user", res.context)
        self.assertEqual(res.context["user"].email, self.user.email)

    def test_homepage_invalid_user_in_session_flushes_and_redirects(self):
        session = self.client.session
        session["user_id"] = "00000000-0000-0000-0000-000000000000"  # non-existent UUID
        session.save()
        res = self.client.get(reverse("Auth_Profile:homepage"))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse("Auth_Profile:login"))
        # session should be flushed (no user_id key)
        self.assertNotIn("user_id", self.client.session)


class ProfileDisplayViewTests(BaseAuthTestCase):
    def test_redirect_to_login_if_not_logged_in(self):
        res = self.client.get(reverse("Auth_Profile:profile_display"))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse("Auth_Profile:login"))

    def test_profile_display_ok_when_logged_in(self):
        self.login_session()
        res = self.client.get(reverse("Auth_Profile:profile_display"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("user", res.context)
        self.assertEqual(res.context["user"].id, self.user.id)


class ProfileEditViewTests(BaseAuthTestCase):
    def test_redirect_to_login_if_not_logged_in(self):
        res = self.client.get(reverse("Auth_Profile:profile_edit"))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse("Auth_Profile:login"))

    def test_get_profile_edit_when_logged_in(self):
        self.login_session()
        res = self.client.get(reverse("Auth_Profile:profile_edit"))
        self.assertEqual(res.status_code, 200)
        self.assertIn("user", res.context)

    def test_post_missing_fields(self):
        self.login_session()
        res = self.client.post(reverse("Auth_Profile:profile_edit"), data={})
        self.assertEqual(res.status_code, 200)  # renders with error
        self.assertContains(res, "Semua field harus diisi")

    def test_post_invalid_date(self):
        self.login_session()
        payload = {
            "nama": "Baru",
            "kelamin": "L",
            "tanggal_lahir": "31-12-2000",  # wrong format
            "nomor_handphone": "08123",
        }
        res = self.client.post(reverse("Auth_Profile:profile_edit"), data=payload)
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, "Format tanggal lahir tidak valid")

    def test_post_valid_updates_and_session_refreshed(self):
        self.login_session()
        payload = {
            "nama": "Nama Update",
            "kelamin": "P",
            "tanggal_lahir": "2001-01-01",
            "nomor_handphone": "081234567000",
        }
        res = self.client.post(reverse("Auth_Profile:profile_edit"), data=payload, follow=False)
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, reverse("Auth_Profile:profile_display"))
        # reload from DB
        self.user.refresh_from_db()
        self.assertEqual(self.user.nama, "Nama Update")
        self.assertEqual(self.user.kelamin, "P")
        self.assertEqual(str(self.user.tanggal_lahir), "2001-01-01")
        self.assertEqual(self.user.nomor_handphone, "081234567000")
        # session updated
        s = self.client.session
        self.assertEqual(s["nama"], "Nama Update")
        self.assertEqual(s["kelamin"], "P")
        self.assertEqual(s["tanggal_lahir"], "2001-01-01")
        self.assertEqual(s["nomor_handphone"], "081234567000")


class LoginViewTests(BaseAuthTestCase):
    def test_get_login_renders(self):
        res = self.client.get(reverse("Auth_Profile:login"))
        self.assertEqual(res.status_code, 200)

    def test_post_login_missing_fields(self):
        data = {}
        res = self.client.post(
            reverse("Auth_Profile:login"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertJSONEqual(
            res.content,
            {"success": False, "message": "Email dan password harus diisi"},
        )

    def test_post_login_unknown_email(self):
        data = {"email": "nouser@example.com", "password": "abc"}
        res = self.client.post(
            reverse("Auth_Profile:login"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertJSONEqual(
            res.content, {"success": False, "message": "Email atau password salah"}
        )

    def test_post_login_wrong_password(self):
        data = {"email": self.user.email, "password": "wrongpassword"}
        res = self.client.post(
            reverse("Auth_Profile:login"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        self.assertJSONEqual(
            res.content, {"success": False, "message": "Email atau password salah"}
        )

    def test_post_login_success(self):
        data = {"email": self.user.email, "password": self.password_plain}
        res = self.client.post(
            reverse("Auth_Profile:login"),
            data=json.dumps(data),
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 200)
        payload = json.loads(res.content.decode())
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("redirect_url"), "/")
        # session is populated
        s = self.client.session
        self.assertIn("user_id", s)
        self.assertEqual(s["email"], self.user.email)


class RegisterViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.url = reverse("Auth_Profile:register")

    def test_get_register_renders(self):
        res = self.client.get(self.url)
        self.assertEqual(res.status_code, 200)

    def post_json(self, payload):
        return self.client.post(
            self.url, data=json.dumps(payload), content_type="application/json"
        )

    def test_missing_fields(self):
        res = self.post_json({})
        self.assertJSONEqual(res.content, {"success": False, "message": "Semua field harus diisi"})

    def test_invalid_email(self):
        payload = {
            "nama": "A", "email": "invalid", "kelamin": "L",
            "tanggal_lahir": "2000-01-01", "nomor_handphone": "0812",
            "password": "abcdefgh", "password2": "abcdefgh"
        }
        res = self.post_json(payload)
        self.assertJSONEqual(res.content, {"success": False, "message": "Format email tidak valid"})

    def test_invalid_gender(self):
        payload = {
            "nama": "A", "email": "a@example.com", "kelamin": "X",
            "tanggal_lahir": "2000-01-01", "nomor_handphone": "0812",
            "password": "abcdefgh", "password2": "abcdefgh"
        }
        res = self.post_json(payload)
        self.assertJSONEqual(res.content, {"success": False, "message": "Kelamin harus L atau P"})

    def test_invalid_date(self):
        payload = {
            "nama": "A", "email": "a@example.com", "kelamin": "L",
            "tanggal_lahir": "01-01-2000", "nomor_handphone": "0812",
            "password": "abcdefgh", "password2": "abcdefgh"
        }
        res = self.post_json(payload)
        self.assertJSONEqual(
            res.content, {"success": False, "message": "Format tanggal lahir tidak valid (gunakan YYYY-MM-DD)"}
        )

    def test_invalid_phone(self):
        payload = {
            "nama": "A", "email": "a@example.com", "kelamin": "L",
            "tanggal_lahir": "2000-01-01", "nomor_handphone": "08AB",
            "password": "abcdefgh", "password2": "abcdefgh"
        }
        res = self.post_json(payload)
        self.assertJSONEqual(
            res.content, {"success": False, "message": "Nomor handphone hanya boleh berisi angka"}
        )

    def test_password_mismatch(self):
        payload = {
            "nama": "A", "email": "a@example.com", "kelamin": "L",
            "tanggal_lahir": "2000-01-01", "nomor_handphone": "0812",
            "password": "abcdefgh", "password2": "abcdefgZ"
        }
        res = self.post_json(payload)
        self.assertJSONEqual(res.content, {"success": False, "message": "Password tidak cocok"})

    def test_password_too_short(self):
        payload = {
            "nama": "A", "email": "a@example.com", "kelamin": "L",
            "tanggal_lahir": "2000-01-01", "nomor_handphone": "0812",
            "password": "short", "password2": "short"
        }
        res = self.post_json(payload)
        self.assertJSONEqual(res.content, {"success": False, "message": "Password minimal 8 karakter"})

    def test_email_already_exists(self):
        User.objects.create(
            nama="Dup",
            email="dup@example.com",
            kelamin="P",
            tanggal_lahir="2001-02-03",
            nomor_handphone="08123",
            password=make_password("abcdefgh"),
        )
        payload = {
            "nama": "A", "email": "dup@example.com", "kelamin": "L",
            "tanggal_lahir": "2000-01-01", "nomor_handphone": "0812",
            "password": "abcdefgh", "password2": "abcdefgh"
        }
        res = self.post_json(payload)
        self.assertJSONEqual(res.content, {"success": False, "message": "Email sudah terdaftar"})

    def test_register_success(self):
        payload = {
            "nama": "User Baru", "email": "baru@example.com", "kelamin": "P",
            "tanggal_lahir": "2002-03-04", "nomor_handphone": "08129876",
            "password": "passwordku", "password2": "passwordku"
        }
        res = self.post_json(payload)
        self.assertEqual(res.status_code, 200)
        body = json.loads(res.content.decode())
        self.assertTrue(body.get("success"))
        self.assertEqual(body.get("redirect_url"), "/login/")
        # User is actually created and password hashed
        u = User.objects.get(email="baru@example.com")
        self.assertNotEqual(u.password, "passwordku")  # hashed in DB
        self.assertEqual(str(u.tanggal_lahir), "2002-03-04")


class LogoutViewTests(BaseAuthTestCase):
    def test_logout_flushes_session_and_redirects(self):
        self.login_session()
        res = self.client.get(reverse("Auth_Profile:logout"))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.url, "/login/")
        self.assertEqual(dict(self.client.session), {})  # flushed
