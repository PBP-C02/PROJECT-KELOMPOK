import json
from datetime import date, datetime, timedelta

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from Auth_Profile.models import User
from .models import Court, TimeSlot


class CourtViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            nama='Owner',
            email='owner@example.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password='hashed',
        )
        self.other_user = User.objects.create(
            nama='Other',
            email='other@example.com',
            kelamin='P',
            tanggal_lahir='2001-02-02',
            nomor_handphone='0811111111',
            password='hashed',
        )

        self.client = Client()
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()

        self.other_client = Client()
        other_session = self.other_client.session
        other_session['user_id'] = str(self.other_user.id)
        other_session.save()

        self.court = Court.objects.create(
            name='Lapangan A',
            sport_type='basketball',
            location='Jakarta',
            address='Jl. Kenangan 1',
            price_per_hour=100000,
            facilities='Parkir, Toilet',
            rating=4.5,
            description='Deskripsi awal',
            owner_name=self.user.nama,
            owner_phone=self.user.nomor_handphone,
            created_by=self.user,
        )
        self.other_court = Court.objects.create(
            name='Lapangan B',
            sport_type='futsal',
            location='Depok',
            address='Jl. Kenangan 2',
            price_per_hour=120000,
            facilities='Parkir',
            rating=4.0,
            description='Deskripsi lain',
            owner_name=self.other_user.nama,
            owner_phone=self.other_user.nomor_handphone,
            created_by=self.other_user,
        )

    def test_show_main_requires_login(self):
        anon_client = Client()
        response = anon_client.get(reverse('Court:show_main'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)

    def test_show_main_success(self):
        response = self.client.get(reverse('Court:show_main'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'main.html')

    def test_search_court_filters(self):
        response = self.client.get(reverse('Court:api_search_court'), {
            'sport': 'basketball',
            'location': 'Jakarta',
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()['court']
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Lapangan A')
        self.assertTrue(data[0]['owned_by_user'])

    def test_get_court_detail(self):
        url = reverse('Court:get_court_detail', args=[self.court.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['court']['name'], 'Lapangan A')

    def test_get_court_detail_not_found(self):
        url = reverse('Court:get_court_detail', args=[9999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_add_court_via_view(self):
        response = self.client.post(
            reverse('Court:add_court'),
            data={
                'name': 'Lapangan Baru',
                'sport_type': 'futsal',
                'location': 'Depok',
                'address': 'Jl. Baru',
                'price_per_hour': '150000',
                'facilities': 'Parkir',
                'rating': '4.0',
                'description': 'Lapangan baru',
                'maps_link': 'https://maps.google.com/?q=-6.2,106.8',
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertTrue(Court.objects.filter(name='Lapangan Baru').exists())

    def test_add_court_view_get(self):
        response = self.client.get(reverse('Court:add_court'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'add_court.html')

    def test_api_add_court(self):
        response = self.client.post(
            reverse('Court:api_add_court'),
            data={
                'name': 'Lapangan API',
                'sport_type': 'tennis',
                'location': 'Bandung',
                'address': 'Jl. API',
                'price_per_hour': '170000',
                'facilities': 'Parkir, Kantin',
                'rating': '4.3',
                'description': 'Via API',
                'maps_link': 'https://maps.google.com/?q=-6.21,106.81',
                'image': SimpleUploadedFile('test.jpg', b'filecontent', content_type='image/jpeg'),
            },
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertTrue(Court.objects.filter(name='Lapangan API').exists())

    def test_api_add_court_requires_auth(self):
        client = Client()
        response = client.post(reverse('Court:api_add_court'), data={})
        self.assertEqual(response.status_code, 401)

    def test_get_availability_default_true(self):
        url = reverse('Court:get_availability', args=[self.court.id])
        response = self.client.get(url, {'date': date.today().isoformat()})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['available'])

    def test_get_availability_missing_date(self):
        url = reverse('Court:get_availability', args=[self.court.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 400)

    def test_set_availability(self):
        url = reverse('Court:set_availability', args=[self.court.id])
        payload = {
            'date': timezone.now().date().isoformat(),
            'is_available': False,
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data['available'])
        slot = TimeSlot.objects.get(court=self.court)
        self.assertFalse(slot.is_available)

    def test_create_booking(self):
        url = reverse('Court:create_booking')
        booking_date = timezone.now().date()
        payload = {
            'court_id': self.court.id,
            'date': booking_date.isoformat(),
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        slot = TimeSlot.objects.get(court=self.court, date=booking_date)
        self.assertFalse(slot.is_available)

    def test_create_booking_missing_fields(self):
        url = reverse('Court:create_booking')
        response = self.client.post(url, json.dumps({}), content_type='application/json')
        self.assertEqual(response.status_code, 400)

    def test_get_all_court(self):
        response = self.client.get(reverse('Court:get_all_Court'))
        self.assertEqual(response.status_code, 200)
        data = response.json()['Court']
        self.assertEqual(len(data), 2)

    def test_api_search_requires_login(self):
        anon_client = Client()
        response = anon_client.get(reverse('Court:api_search_court'))
        self.assertEqual(response.status_code, 401)

    def test_api_court_whatsapp(self):
        url = reverse('Court:api_court_whatsapp')
        payload = {
            'court_id': self.court.id,
            'date': 'Senin, 1 Januari',
            'time': '10:00 - 11:00',
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_get_whatsapp_link(self):
        url = reverse('Court:get_whatsapp_link')
        payload = {
            'court_id': self.court.id,
            'date': 'Selasa, 2 Januari',
            'time': '09:00 - 10:00',
        }
        response = self.client.post(url, json.dumps(payload), content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])

    def test_delete_court(self):
        url = reverse('Court:delete_court', args=[self.court.id])
        response = self.client.post(url, content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Court.objects.filter(id=self.court.id).exists())

    def test_delete_court_requires_owner(self):
        url = reverse('Court:delete_court', args=[self.court.id])
        response = self.other_client.post(url, content_type='application/json')
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Court.objects.filter(id=self.court.id).exists())

    def test_edit_court_get_and_post(self):
        url = reverse('Court:edit_court', args=[self.court.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'edit_court.html')

        response = self.client.post(url, {
            'name': 'Lapangan Update',
            'sport_type': 'tennis',
            'price_per_hour': '200000',
            'maps_link': 'https://maps.google.com/maps/@-6.3,107.0,17z',
        })
        self.assertEqual(response.status_code, 302)
        self.court.refresh_from_db()
        self.assertEqual(self.court.name, 'Lapangan Update')
        self.assertEqual(self.court.sport_type, 'tennis')
        self.assertEqual(float(self.court.price_per_hour), 200000.0)
        self.assertEqual(self.court.owner_phone, self.user.nomor_handphone)

    def test_edit_court_rejects_non_owner(self):
        url = reverse('Court:edit_court', args=[self.court.id])
        response = self.other_client.get(url)
        self.assertEqual(response.status_code, 404)


class CourtModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            nama='Owner',
            email='owner@example.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password='hashed',
        )
        self.court = Court.objects.create(
            name='Lapangan Model',
            sport_type='basketball',
            location='Jakarta',
            address='Jl. Model',
            price_per_hour=100000,
            facilities='Parkir, Toilet, Kantin',
            rating=4.2,
            description='Model test',
            owner_name=self.user.nama,
            owner_phone=self.user.nomor_handphone,
            created_by=self.user,
        )

    def test_get_facilities_list(self):
        self.assertEqual(
            self.court.get_facilities_list(),
            ['Parkir', 'Toilet', 'Kantin']
        )

    def test_get_whatsapp_link(self):
        link = self.court.get_whatsapp_link(date='2024-01-01', time='09:00')
        self.assertIn('wa.me', link)
        self.assertIn(self.user.nomor_handphone, link)

    def test_is_available(self):
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

    def test_time_slot_label(self):
        slot = TimeSlot.objects.create(
            court=self.court,
            date=timezone.now().date(),
            start_time=datetime.strptime('10:00', '%H:%M').time(),
            end_time=datetime.strptime('11:00', '%H:%M').time(),
        )
        self.assertEqual(slot.get_time_label(), '10:00 - 11:00')
