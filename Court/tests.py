import json
import uuid
from datetime import date, datetime, timedelta, time
from decimal import Decimal
from urllib.parse import unquote
from unittest.mock import patch

from django.contrib.sessions.middleware import SessionMiddleware
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone

from Auth_Profile.models import User
from .forms import CourtForm
from .models import Court, TimeSlot
import Court.views as views


class CourtViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(
            nama='Owner',
            email='owner@example.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password='hashed',
        )
        cls.other_user = User.objects.create(
            nama='Other',
            email='other@example.com',
            kelamin='P',
            tanggal_lahir='2001-02-02',
            nomor_handphone='08100000000',
            password='hashed',
        )
        cls.court = Court.objects.create(
            name='Court A',
            sport_type='basketball',
            location='Jakarta',
            address='123 Memory Street',
            price_per_hour=100000,
            facilities='Parking, Restroom, Canteen',
            rating=4.5,
            description='Initial description',
            owner_name=cls.user.nama,
            owner_phone=cls.user.nomor_handphone,
            created_by=cls.user,
        )
        cls.other_court = Court.objects.create(
            name='Court B',
            sport_type='futsal',
            location='Depok',
            address='456 Memory Street',
            price_per_hour=120000,
            facilities='Parking',
            rating=4.0,
            description='Additional description',
            owner_name=cls.other_user.nama,
            owner_phone=cls.other_user.nomor_handphone,
            created_by=cls.other_user,
        )

    def setUp(self):
        self.client = self._login(self.user)
        self.other_client = self._login(self.other_user)
        self.factory = RequestFactory()

    def _login(self, user):
        client = Client()
        session = client.session
        session['user_id'] = str(user.id)
        session.save()
        return client

    def _with_session(self, request, user=None):
        middleware = SessionMiddleware(lambda req: None)
        middleware.process_request(request)
        if user:
            request.session['user_id'] = str(user.id)
        request.session.save()
        return request

    def _make_image(self, name='test.png'):
        png_bytes = (
            b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR'
            b'\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde'
            b'\x00\x00\x00\x0bIDATx\x9cc```\x00\x00\x00\x05\x00\x01'
            b'\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        )
        return SimpleUploadedFile(name, png_bytes, content_type='image/png')

    def test_login_required_routes(self):
        html_cases = [
            ('get', reverse('Court:show_main')),
            ('get', reverse('Court:add_court')),
            ('post', reverse('Court:add_court')),
            ('get', reverse('Court:court_detail', args=[self.court.id])),
            ('get', reverse('Court:edit_court', args=[self.court.id])),
        ]
        json_cases = [
            ('get', reverse('Court:get_all_Court')),
            ('get', reverse('Court:api_search_court')),
            ('get', reverse('Court:get_court_detail', args=[self.court.id])),
            ('get', reverse('Court:get_availability', args=[self.court.id])),
            ('post', reverse('Court:api_add_court')),
            ('post', reverse('Court:set_availability', args=[self.court.id])),
            ('post', reverse('Court:create_booking')),
            ('post', reverse('Court:delete_court', args=[self.court.id])),
            ('post', reverse('Court:api_court_whatsapp')),
            ('post', reverse('Court:get_whatsapp_link')),
        ]
        for method, url in html_cases:
            with self.subTest(url=url):
                self.assertEqual(getattr(Client(), method)(url).status_code, 302)
        for method, url in json_cases:
            with self.subTest(url=url):
                self.assertEqual(getattr(Client(), method)(url, content_type='application/json').status_code, 401)

    def test_show_main_and_search_api(self):
        response = self.client.get(reverse('Court:show_main'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')

        response = self.client.get(reverse('Court:api_search_court'), {'q': 'Court'})
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(len(response.json()['court']), 1)

        response = self.client.get(reverse('Court:api_search_court'), {
            'sport': 'basketball',
            'location': 'Jakarta',
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['court'][0]['name'], 'Court A')

    def test_search_Court_function(self):
        request = self._with_session(self.factory.get('/court/api/court/search/'))
        self.assertEqual(views.search_Court(request).status_code, 401)

        request = self._with_session(
            self.factory.get('/court/api/court/search/', {'q': 'Court'}),
            self.user,
        )
        response = views.search_Court(request)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Court', json.loads(response.content))

        request = self._with_session(
            self.factory.get('/court/api/court/search/', {
                'sport': 'basketball',
                'location': 'Jakarta',
            }),
            self.user,
        )
        self.assertEqual(views.search_Court(request).status_code, 200)

    def test_get_court_detail_variants(self):
        cases = [
            ('exists', self.court.id, 200),
            ('missing', 9999, 404),
        ]
        for name, cid, status in cases:
            with self.subTest(name=name):
                response = self.client.get(reverse('Court:get_court_detail', args=[cid]))
                self.assertEqual(response.status_code, status)

    def test_court_pages_render(self):
        response = self.client.get(reverse('Court:court_detail', args=[self.court.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'detail.html')

        response = self.client.get(reverse('Court:edit_court', args=[self.court.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'edit_court.html')

    def test_add_court_form_and_maps_fallback(self):
        response = self.client.get(reverse('Court:add_court'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_court.html')

        response = self.client.post(reverse('Court:add_court'), {
            'name': 'Court Form',
            'sport_type': 'futsal',
            'location': 'Depok',
            'address': 'Form Street',
            'price_per_hour': '150000',
            'facilities': 'Parking',
            'rating': '4.0',
            'description': 'Form submit',
            'maps_link': 'https://maps.google.com/?q=-6.2,106.8',
        })
        self.assertEqual(response.status_code, 302)
        new_court = Court.objects.get(name='Court Form')
        self.assertEqual(new_court.created_by, self.user)
        self.assertEqual(new_court.owner_phone, self.user.nomor_handphone)

        payload = {
            'name': 'Court Exception',
            'sport_type': 'tennis',
            'location': 'Bandung',
            'address': 'Address',
            'price_per_hour': '100000',
            'facilities': 'Parking',
            'rating': '4',
            'description': 'Exception case',
            'maps_link': 'https://maps.google.com/?q=-6.2,106.8',
        }
        with patch('Court.views.urlparse', side_effect=Exception('boom')):
            response = self.client.post(reverse('Court:add_court'), data=payload)
        self.assertEqual(response.status_code, 302)

    def test_api_add_court_variants(self):
        response = self.client.post(
            reverse('Court:api_add_court'),
            data={
                'name': 'Court API',
                'sport_type': 'tennis',
                'location': 'Bandung',
                'address': 'API Street',
                'price_per_hour': '170000',
                'facilities': 'Parking, Canteen',
                'rating': '4.3',
                'description': 'Via API',
                'maps_link': 'https://maps.google.com/?q=-6.21,106.81',
                'image': self._make_image('api.png'),
            },
        )
        self.assertTrue(response.json()['success'])

        with patch('Court.views.Court.objects.create', side_effect=Exception('boom')):
            response = self.client.post(reverse('Court:api_add_court'), data={'name': 'X'})
        self.assertEqual(response.status_code, 400)

        self.assertEqual(self.client.get(reverse('Court:api_add_court')).status_code, 405)

    def test_get_availability_variants(self):
        url = reverse('Court:get_availability', args=[self.court.id])
        today = date.today().isoformat()

        response = self.client.get(url, {'date': today})
        self.assertTrue(response.json()['available'])

        TimeSlot.objects.create(
            court=self.court,
            date=date.today(),
            start_time=datetime.strptime('10:00', '%H:%M').time(),
            end_time=datetime.strptime('11:00', '%H:%M').time(),
            is_available=False,
        )
        response = self.client.get(url, {'date': today})
        self.assertFalse(response.json()['available'])

        self.assertEqual(self.client.get(url).status_code, 400)
        self.assertEqual(self.client.get(url, {'date': 'bad'}).status_code, 400)
        self.assertEqual(
            self.client.get(reverse('Court:get_availability', args=[9999]), {'date': today}).status_code,
            404,
        )
        with patch('Court.views.Court.objects.get', side_effect=Exception('boom')):
            self.assertEqual(self.client.get(url, {'date': today}).status_code, 500)

    def test_set_availability_flow_and_errors(self):
        url = reverse('Court:set_availability', args=[self.court.id])
        today = date.today().isoformat()
        payload = {'date': today, 'is_available': False}

        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        slot = TimeSlot.objects.get(court=self.court, date=date.fromisoformat(today))
        self.assertFalse(slot.is_available)

        payload['is_available'] = True
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        slot.refresh_from_db()
        self.assertTrue(slot.is_available)

        self.assertEqual(
            Client().post(url, json.dumps(payload), content_type='application/json').status_code,
            401,
        )
        self.assertEqual(
            self.other_client.post(url, json.dumps(payload), content_type='application/json').status_code,
            403,
        )
        self.assertEqual(
            self.client.post(url, json.dumps({}), content_type='application/json').status_code,
            400,
        )
        self.assertEqual(
            self.client.post(url, 'oops', content_type='application/json').status_code,
            400,
        )
        self.assertEqual(
            self.client.post(url, json.dumps({'date': 'bad'}), content_type='application/json').status_code,
            400,
        )

    def test_create_booking_flow(self):
        url = reverse('Court:create_booking')
        today = date.today().isoformat()
        payload = {'court_id': self.court.id, 'date': today}

        self.assertEqual(
            self.client.post(url, json.dumps(payload), content_type='application/json').status_code,
            200,
        )
        self.assertFalse(TimeSlot.objects.get(court=self.court, date=date.fromisoformat(today)).is_available)
        self.assertEqual(
            self.client.post(url, json.dumps(payload), content_type='application/json').status_code,
            400,
        )

        for name, raw_payload, status in [
            ('missing-fields', {}, 400),
            ('invalid-date', {'court_id': self.court.id, 'date': 'bad'}, 400),
            ('not-found', {'court_id': 9999, 'date': today}, 404),
            ('json-error', 'oops', 400),
        ]:
            with self.subTest(name=name):
                response = self.client.post(
                    url,
                    json.dumps(raw_payload) if isinstance(raw_payload, dict) else raw_payload,
                    content_type='application/json',
                )
                self.assertEqual(response.status_code, status)

        with patch('Court.views.Court.objects.get', side_effect=Exception('boom')):
            response = self.client.post(url, json.dumps(payload), content_type='application/json')
            self.assertEqual(response.status_code, 500)

    def test_get_all_court(self):
        response = self.client.get(reverse('Court:get_all_Court'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()['Court']), 2)

    def test_is_available_today_logic(self):
        today = timezone.localdate()
        tomorrow = today + timedelta(days=1)

        # Unavailability tomorrow should not affect today's availability
        TimeSlot.objects.create(
            court=self.court,
            date=tomorrow,
            start_time=time(0, 0),
            end_time=time(23, 59),
            is_available=False,
        )
        self.assertTrue(self.court.is_available_today())
        payload = self.client.get(reverse('Court:get_all_Court')).json()['Court']
        today_entry = next(item for item in payload if item['id'] == self.court.id)
        self.assertTrue(today_entry['is_available'])

        # Mark today as unavailable, expect API & helper to follow suit
        TimeSlot.objects.create(
            court=self.court,
            date=today,
            start_time=time(0, 0),
            end_time=time(23, 59),
            is_available=False,
        )
        self.assertFalse(Court.objects.get(id=self.court.id).is_available_today())
        payload = self.client.get(reverse('Court:get_all_Court')).json()['Court']
        today_entry = next(item for item in payload if item['id'] == self.court.id)
        self.assertFalse(today_entry['is_available'])

    def test_api_court_whatsapp_variants(self):
        url = reverse('Court:api_court_whatsapp')
        payload = {'court_id': self.court.id, 'date': 'Monday', 'time': '10:00'}
        response_data = self.client.post(url, json.dumps(payload), content_type='application/json').json()
        self.assertTrue(response_data['success'])

        self.assertEqual(self.client.get(url).status_code, 400)
        self.assertEqual(self.client.post(url, 'oops', content_type='application/json').status_code, 400)
        self.assertEqual(
            self.client.post(url, json.dumps({'date': 'Monday'}), content_type='application/json').status_code,
            400,
        )
        self.assertEqual(
            self.client.post(url, json.dumps({'court_id': 9999, 'date': 'Monday'}), content_type='application/json').status_code,
            404,
        )

    def test_get_whatsapp_link_variants(self):
        url = reverse('Court:get_whatsapp_link')
        payload = {'court_id': self.court.id, 'date': 'Tuesday', 'time': '09:00'}
        response_data = self.client.post(url, json.dumps(payload), content_type='application/json').json()
        self.assertTrue(response_data['success'])
        self.assertIn('whatsapp_link', response_data)
        self.assertIn('wa.me', response_data['whatsapp_link'])

        self.assertEqual(self.client.get(url).status_code, 405)
        self.assertEqual(
            self.client.post(url, json.dumps(dict(payload, court_id=9999)), content_type='application/json').status_code,
            404,
        )
        with patch('Court.views.Court.objects.get', side_effect=Exception('boom')):
            self.assertEqual(self.client.post(url, json.dumps(payload), content_type='application/json').status_code, 500)

    def test_delete_court(self):
        url = reverse('Court:delete_court', args=[self.court.id])
        self.assertEqual(self.client.post(url, content_type='application/json').status_code, 200)
        self.assertFalse(Court.objects.filter(id=self.court.id).exists())
        self.assertEqual(self.other_client.post(url, content_type='application/json').status_code, 403)

    def test_edit_court_workflow(self):
        self.assertEqual(
            self.client.get(reverse('Court:edit_court', args=[self.other_court.id])).status_code,
            404,
        )

        self.user.nama = 'Updated Name'
        self.user.nomor_handphone = '08111111111'
        self.user.save()

        url = reverse('Court:edit_court', args=[self.court.id])
        response = self.client.post(url, {
            'name': self.court.name,
            'sport_type': self.court.sport_type,
            'location': self.court.location,
            'address': self.court.address,
            'facilities': 'Parking, Restroom, Canteen',
            'description': 'Updated',
            'maps_link': 'https://maps.google.com/?q=-6.2,106.8',
            'image': self._make_image('edit.png'),
            'price_per_hour': '180000',
            'rating': '4.8',
        })
        self.assertEqual(response.status_code, 302)
        self.court.refresh_from_db()
        self.assertEqual(self.court.facilities, 'Parking, Restroom, Canteen')
        self.assertEqual(self.court.owner_name, 'Updated Name')
        self.assertEqual(self.court.latitude, Decimal('-6.2'))
        self.assertEqual(self.court.longitude, Decimal('106.8'))

        request = self._with_session(self.factory.post('/court/1/edit/', {
            'name': 'Court Direct',
            'sport_type': 'basketball',
            'location': 'Jakarta',
            'address': 'Address',
            'price_per_hour': '190000',
            'facilities': 'Parking, Restroom',
            'rating': '4.9',
            'description': 'Direct edit',
            'maps_link': 'https://maps.google.com/?q=-6.3,107.1',
        }), self.user)
        self.assertEqual(views.edit_court(request, self.court.id).status_code, 302)

    def test_helper_functions(self):
        self.assertEqual(views.clean_decimal('10.5'), Decimal('10.5'))
        self.assertEqual(views.clean_decimal('bad', default=Decimal('2')), Decimal('2'))
        self.assertEqual(views.clean_decimal('-1', min_value=Decimal('0')), Decimal('0'))
        self.assertEqual(views.clean_decimal('12', max_value=Decimal('10')), Decimal('10'))

        coordinate_cases = [
            ('', None),
            ('abc', None),
            ('200', None),
            ('1.23', Decimal('1.23')),
        ]
        for value, expected in coordinate_cases:
            result = views.sanitize_coordinate(value, 'latitude')
            if expected is None:
                self.assertIsNone(result)
            else:
                self.assertEqual(result, expected)
        self.assertIsNone(views.sanitize_coordinate('1', 'unknown'))

        request = self._with_session(self.factory.get('/dummy'), self.user)
        self.assertEqual(views._get_current_user(request), self.user)

        request = self._with_session(self.factory.get('/dummy'))
        request.session['user_id'] = str(uuid.uuid4())
        request.session.save()
        self.assertIsNone(views._get_current_user(request))

    def test_court_form_rating_validation(self):
        base_data = {
            'name': 'Form Court',
            'sport_type': 'tennis',
            'location': 'Bandung',
            'address': 'Alamat lengkap',
            'price_per_hour': '150000',
            'facilities': 'Parking',
            'description': 'Nice court',
            'maps_link': 'https://maps.google.com/?q=-6.2,106.8',
        }

        form = CourtForm({**base_data, 'rating': '4.5'})
        self.assertTrue(form.is_valid(), form.errors)
        self.assertEqual(form.cleaned_data['rating'], Decimal('4.5'))

        form_zero = CourtForm({**base_data, 'rating': '0'})
        self.assertFalse(form_zero.is_valid())
        self.assertIn('rating', form_zero.errors)

        form_high = CourtForm({**base_data, 'rating': '6'})
        self.assertFalse(form_high.is_valid())
        self.assertIn('rating', form_high.errors)

        form_empty = CourtForm({**base_data, 'rating': ''})
        self.assertTrue(form_empty.is_valid(), form_empty.errors)
        self.assertEqual(form_empty.cleaned_data['rating'], Decimal('0'))

        form_blank_facilities = CourtForm({**base_data, 'rating': '3', 'facilities': ''})
        self.assertTrue(form_blank_facilities.is_valid(), form_blank_facilities.errors)
        self.assertEqual(form_blank_facilities.cleaned_data['facilities'], '')

        user, response = views._require_user(self._with_session(self.factory.get('/dummy')), json_mode=True)
        self.assertIsNone(user)
        self.assertEqual(response.status_code, 401)

        request = self._with_session(self.factory.get('/dummy'))
        user, response = views._require_user(request)
        self.assertIsNone(user)
        self.assertEqual(response.status_code, 302)

        class Dummy:
            username = 'dummy'

            def get_full_name(self):
                return 'Full Name'

        self.assertEqual(views._get_user_name(Dummy()), 'Full Name')
        self.assertEqual(views._get_user_name(type('Anon', (), {'email': 'anon@example.com'})()), 'anon@example.com')
        self.assertEqual(views._get_user_name(None), '')
        self.assertEqual(views._get_user_phone(None), '')

    def test_parse_maps_link(self):
        cases = [
            ('query', 'https://maps.google.com/?q=-6.2,106.8', ('-6.2', '106.8')),
            ('at', 'https://maps.google.com/maps/@-6.3,107.0,17z', ('-6.3', '107.0')),
            ('fragment', 'https://maps.google.com/?hl=id#!3d-6.4!4d106.9', ('-6.4', '106.9')),
            ('invalid', 'https://example.com', (None, None)),
            ('none', None, (None, None)),
            ('fragment-error', 'https://maps.google.com/?hl=id#!3d-6.4', (None, None)),
        ]
        for name, link, expected in cases:
            with self.subTest(name=name):
                lat, lng = views.parse_maps_link(link)
                self.assertEqual(lat, expected[0])
                if expected[1] is None:
                    self.assertIsNone(lng)
                elif name == 'at':
                    self.assertTrue(str(lng).startswith(expected[1]))
                else:
                    self.assertEqual(lng, expected[1])

        with patch('Court.views.urlparse', side_effect=Exception('boom')):
            lat, lng = views.parse_maps_link('https://maps.google.com')
            self.assertIsNone(lat)
            self.assertIsNone(lng)

        class BadString(str):
            def split(self, sep=None, maxsplit=-1):
                if sep == '!4d':
                    raise ValueError('bad')
                return super().split(sep, maxsplit)

        with patch('Court.views.unquote', return_value=BadString('!3d-6.4!4d106.9')):
            lat, lng = views.parse_maps_link('https://maps.google.com')
            self.assertIsNone(lat)
            self.assertIsNone(lng)


class CourtModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create(
            nama='Owner',
            email='owner@example.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password='hashed',
        )
        cls.court = Court.objects.create(
            name='Court Model',
            sport_type='basketball',
            location='Jakarta',
            address='Model Street',
            price_per_hour=100000,
            facilities='Parking, Restroom, Canteen',
            rating=4.2,
            description='Model test',
            owner_name=cls.user.nama,
            owner_phone=cls.user.nomor_handphone,
            created_by=cls.user,
        )

    def test_court_helpers(self):
        self.assertEqual(str(self.court), 'Court Model')
        self.assertEqual(
            self.court.get_facilities_list(),
            ['Parking', 'Restroom', 'Canteen'],
        )

        link = self.court.get_whatsapp_link(date='2024-01-01', time='09:00')
        self.assertIn('wa.me', link)
        self.assertIn(self.user.nomor_handphone, link)
        self.assertIn('for date *2024-01-01*', unquote(self.court.get_whatsapp_link(date='2024-01-01')))
        self.assertIn(' at *09:00*', unquote(self.court.get_whatsapp_link(time='09:00')))

        self.assertTrue(self.court.is_available())
        now = timezone.now()
        TimeSlot.objects.create(
            court=self.court,
            date=now.date(),
            start_time=now.time(),
            end_time=(now + timedelta(hours=1)).time(),
            is_available=False,
        )
        self.assertFalse(self.court.is_available())

        slot = TimeSlot.objects.create(
            court=self.court,
            date=now.date(),
            start_time=datetime.strptime('10:00', '%H:%M').time(),
            end_time=datetime.strptime('11:00', '%H:%M').time(),
        )
        self.assertEqual(slot.get_time_label(), '10:00 - 11:00')
        self.assertIn('Court Model', str(slot))
