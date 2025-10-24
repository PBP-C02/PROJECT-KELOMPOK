from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.hashers import make_password
from datetime import date, time
from Auth_Profile.models import User
from Sport_Partner.models import PartnerPost, PostParticipants
import json


class PartnerPostModelTest(TestCase):
    """Test untuk PartnerPost Model"""
    
    def setUp(self):
        """Setup data untuk testing"""
        self.user = User.objects.create(
            nama="Tester",
            email="tester@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567890",
            password=make_password("password123")
        )
        
        self.post = PartnerPost.objects.create(
            creator=self.user,
            title="Main Futsal",
            description="Cari teman main futsal sore",
            category="futsal",
            tanggal=date.today(),
            jam_mulai=time(14, 0),
            jam_selesai=time(16, 0),
            lokasi="GOR Senayan"
        )
    
    def test_post_creation(self):
        """Test apakah post berhasil dibuat"""
        self.assertEqual(self.post.title, "Main Futsal")
        self.assertEqual(self.post.creator, self.user)
        self.assertEqual(self.post.category, "futsal")
    
    def test_post_str(self):
        """Test __str__ method"""
        self.assertEqual(str(self.post), "Main Futsal")
    
    def test_total_participants_initial(self):
        """Test total participants awal harus 0"""
        self.assertEqual(self.post.total_participants, 0)
    
    def test_add_participant_success(self):
        """Test tambah participant berhasil"""
        other_user = User.objects.create(
            nama="Budi",
            email="budi@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        added = self.post.add_participant(other_user)
        self.assertTrue(added)
        self.assertEqual(self.post.total_participants, 1)
    
    def test_add_participant_duplicate(self):
        """Test tambah participant yang sama 2x harus return False"""
        other_user = User.objects.create(
            nama="Budi",
            email="budi@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        self.post.add_participant(other_user)
        added_again = self.post.add_participant(other_user)
        
        self.assertFalse(added_again)
        self.assertEqual(self.post.total_participants, 1)
    
    def test_remove_participant(self):
        """Test remove participant"""
        other_user = User.objects.create(
            nama="Budi",
            email="budi@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        self.post.add_participant(other_user)
        self.assertEqual(self.post.total_participants, 1)
        
        self.post.remove_participant(other_user)
        self.assertEqual(self.post.total_participants, 0)
    
    def test_is_participant_true(self):
        """Test is_participant return True jika user sudah join"""
        other_user = User.objects.create(
            nama="Budi",
            email="budi@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        self.post.add_participant(other_user)
        self.assertTrue(self.post.is_participant(other_user))
    
    def test_is_participant_false(self):
        """Test is_participant return False jika user belum join"""
        other_user = User.objects.create(
            nama="Budi",
            email="budi@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        self.assertFalse(self.post.is_participant(other_user))
    
    def test_participants_list(self):
        """Test participants_list property"""
        other_user = User.objects.create(
            nama="Budi",
            email="budi@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        self.post.add_participant(other_user)
        participants = self.post.participants_list
        
        self.assertEqual(len(participants), 1)
        self.assertEqual(participants[0].participant, other_user)


class PostParticipantsModelTest(TestCase):
    """Test untuk PostParticipants Model"""
    
    def setUp(self):
        self.user = User.objects.create(
            nama="Tester",
            email="tester@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567890",
            password=make_password("password123")
        )
        
        self.post = PartnerPost.objects.create(
            creator=self.user,
            title="Main Basket",
            description="Cari partner basket",
            category="basketball",
            tanggal=date.today(),
            jam_mulai=time(9, 0),
            jam_selesai=time(10, 0),
            lokasi="Lapangan UI"
        )
        
        self.participant = User.objects.create(
            nama="Budi",
            email="budi@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
    
    def test_participant_creation(self):
        """Test pembuatan participant"""
        pp = PostParticipants.objects.create(
            post_id=self.post,
            participant=self.participant
        )
        
        self.assertEqual(pp.post_id, self.post)
        self.assertEqual(pp.participant, self.participant)
    
    def test_participant_str(self):
        """Test __str__ method"""
        pp = PostParticipants.objects.create(
            post_id=self.post,
            participant=self.participant
        )
        
        expected = f"{self.participant.nama} joined {self.post.title}"
        self.assertEqual(str(pp), expected)
    
    def test_unique_together_constraint(self):
        """Test unique_together mencegah duplicate"""
        PostParticipants.objects.create(
            post_id=self.post,
            participant=self.participant
        )
        
        # Coba buat lagi harus error
        with self.assertRaises(Exception):
            PostParticipants.objects.create(
                post_id=self.post,
                participant=self.participant
            )


class ShowPostViewTest(TestCase):
    """Test untuk show_post view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama="Tester",
            email="tester@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567890",
            password=make_password("password123")
        )
    
    def test_show_post_requires_login(self):
        """Test show_post redirect ke login jika belum login"""
        response = self.client.get(reverse('Sport_Partner:show_post'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_show_post_success(self):
        """Test show_post berhasil jika sudah login"""
        # Simulasi login
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        response = self.client.get(reverse('Sport_Partner:show_post'))
        self.assertEqual(response.status_code, 200)
        self.assertIn('user_now', response.context)
        self.assertIn('post_list', response.context)


class CreatePostViewTest(TestCase):
    """Test untuk create_post view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama="Tester",
            email="tester@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567890",
            password=make_password("password123")
        )
        
        # Simulasi login
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_create_post_requires_login(self):
        """Test create_post redirect ke login jika belum login"""
        client = Client()  # Client baru tanpa session
        response = client.get(reverse('Sport_Partner:create_post'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_create_post_get_success(self):
        """Test GET create_post berhasil"""
        response = self.client.get(reverse('Sport_Partner:create_post'))
        self.assertEqual(response.status_code, 200)
    
    def test_create_post_missing_field(self):
        """Test create post dengan field kosong"""
        response = self.client.post(
            reverse('Sport_Partner:create_post'),
            data=json.dumps({
                'title': '',  # Title kosong
                'description': 'Desc',
                'category': 'futsal',
                'tanggal': '2025-10-10',
                'jam_mulai': '10:00',
                'jam_selesai': '12:00',
                'lokasi': 'Jakarta'
            }),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('field harus diisi', data['message'].lower())
    
    def test_create_post_invalid_date(self):
        """Test create post dengan format tanggal salah"""
        response = self.client.post(
            reverse('Sport_Partner:create_post'),
            data=json.dumps({
                'title': 'Main Bola',
                'description': 'Desc',
                'category': 'soccer',
                'tanggal': '10-10-2025',  # Format salah
                'jam_mulai': '10:00',
                'jam_selesai': '12:00',
                'lokasi': 'Jakarta'
            }),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('tanggal', data['message'].lower())
    
    def test_create_post_invalid_time(self):
        """Test create post dengan format waktu salah"""
        response = self.client.post(
            reverse('Sport_Partner:create_post'),
            data=json.dumps({
                'title': 'Main Bola',
                'description': 'Desc',
                'category': 'soccer',
                'tanggal': '2025-10-10',
                'jam_mulai': '25:00',  # Format salah
                'jam_selesai': '12:00',
                'lokasi': 'Jakarta'
            }),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('waktu', data['message'].lower())
    
    def test_create_post_success(self):
        """Test create post berhasil"""
        response = self.client.post(
            reverse('Sport_Partner:create_post'),
            data=json.dumps({
                'title': 'Main Bola',
                'description': 'Cari teman bola',
                'category': 'soccer',
                'tanggal': '2025-10-10',
                'jam_mulai': '10:00',
                'jam_selesai': '12:00',
                'lokasi': 'Jakarta'
            }),
            content_type='application/json'
        )
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('redirect_url', data)
        
        # Cek post berhasil dibuat di database
        post_count = PartnerPost.objects.filter(title='Main Bola').count()
        self.assertEqual(post_count, 1)


class PostDetailViewTest(TestCase):
    """Test untuk post_detail view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama="Tester",
            email="tester@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567890",
            password=make_password("password123")
        )
        
        self.post = PartnerPost.objects.create(
            creator=self.user,
            title="Main Basket",
            description="Cari partner basket",
            category="basketball",
            tanggal=date.today(),
            jam_mulai=time(9, 0),
            jam_selesai=time(10, 0),
            lokasi="Lapangan UI"
        )
        
        # Simulasi login
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_post_detail_requires_login(self):
        """Test post_detail redirect ke login jika belum login"""
        client = Client()
        response = client.get(
            reverse('Sport_Partner:post-detail', args=[self.post.post_id])
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/', response.url)
    
    def test_post_detail_success(self):
        """Test post_detail berhasil"""
        response = self.client.get(
            reverse('Sport_Partner:post-detail', args=[self.post.post_id])
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertIn('post', response.context)
        self.assertEqual(response.context['post'], self.post)
    
    def test_post_detail_404(self):
        """Test post_detail dengan ID tidak ada"""
        import uuid
        fake_id = uuid.uuid4()
        
        response = self.client.get(
            reverse('Sport_Partner:post-detail', args=[fake_id])
        )
        self.assertEqual(response.status_code, 404)


class GetParticipantsJsonViewTest(TestCase):
    """Test untuk get_participants_json view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama="Tester",
            email="tester@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567890",
            password=make_password("password123")
        )
        
        self.post = PartnerPost.objects.create(
            creator=self.user,
            title="Main Basket",
            description="Cari partner basket",
            category="basketball",
            tanggal=date.today(),
            jam_mulai=time(9, 0),
            jam_selesai=time(10, 0),
            lokasi="Lapangan UI"
        )
    
    def test_get_participants_empty(self):
        """Test get participants ketika belum ada"""
        response = self.client.get(
            reverse('Sport_Partner:get_participants', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 0)
        self.assertEqual(len(data['participants']), 0)
    
    def test_get_participants_with_data(self):
        """Test get participants ketika ada data"""
        other_user = User.objects.create(
            nama="Budi",
            email="budi@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        self.post.add_participant(other_user)
        
        response = self.client.get(
            reverse('Sport_Partner:get_participants', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total'], 1)
        self.assertEqual(data['participants'][0]['nama'], 'Budi')


class JoinPostViewTest(TestCase):
    """Test untuk join_post view"""
    
    def setUp(self):
        self.client = Client()
        self.creator = User.objects.create(
            nama="Creator",
            email="creator@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567890",
            password=make_password("password123")
        )
        
        self.user = User.objects.create(
            nama="User",
            email="user@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        self.post = PartnerPost.objects.create(
            creator=self.creator,
            title="Main Basket",
            description="Cari partner basket",
            category="basketball",
            tanggal=date.today(),
            jam_mulai=time(9, 0),
            jam_selesai=time(10, 0),
            lokasi="Lapangan UI"
        )
    
    def test_join_post_requires_login(self):
        """Test join post tanpa login"""
        response = self.client.post(
            reverse('Sport_Partner:join_post', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('login', data['message'].lower())
    
    def test_join_post_as_creator(self):
        """Test creator tidak bisa join post sendiri"""
        session = self.client.session
        session['user_id'] = str(self.creator.id)
        session.save()
        
        response = self.client.post(
            reverse('Sport_Partner:join_post', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('creator', data['message'].lower())
    
    def test_join_post_success(self):
        """Test join post berhasil"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        response = self.client.post(
            reverse('Sport_Partner:join_post', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_participants'], 1)
    
    def test_join_post_twice(self):
        """Test join post 2x harus gagal"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Join pertama
        self.client.post(
            reverse('Sport_Partner:join_post', args=[self.post.post_id])
        )
        
        # Join kedua
        response = self.client.post(
            reverse('Sport_Partner:join_post', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('sudah', data['message'].lower())


class LeavePostViewTest(TestCase):
    """Test untuk leave_post view"""
    
    def setUp(self):
        self.client = Client()
        self.creator = User.objects.create(
            nama="Creator",
            email="creator@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567890",
            password=make_password("password123")
        )
        
        self.user = User.objects.create(
            nama="User",
            email="user@example.com",
            kelamin="L",
            tanggal_lahir=date(2000, 1, 1),
            nomor_handphone="081234567891",
            password=make_password("password123")
        )
        
        self.post = PartnerPost.objects.create(
            creator=self.creator,
            title="Main Basket",
            description="Cari partner basket",
            category="basketball",
            tanggal=date.today(),
            jam_mulai=time(9, 0),
            jam_selesai=time(10, 0),
            lokasi="Lapangan UI"
        )
    
    def test_leave_post_requires_login(self):
        """Test leave post tanpa login"""
        response = self.client.post(
            reverse('Sport_Partner:leave_post', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('login', data['message'].lower())
    
    def test_leave_post_success(self):
        """Test leave post berhasil"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Join dulu
        self.post.add_participant(self.user)
        self.assertEqual(self.post.total_participants, 1)
        
        # Leave
        response = self.client.post(
            reverse('Sport_Partner:leave_post', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['total_participants'], 0)
    
    def test_leave_post_not_participant(self):
        """Test leave post ketika belum join (tetap sukses)"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        # Leave tanpa join dulu
        response = self.client.post(
            reverse('Sport_Partner:leave_post', args=[self.post.post_id])
        )
        
        data = response.json()
        self.assertTrue(data['success'])  # Tetap sukses meski belum join