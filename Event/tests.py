from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from datetime import datetime, timedelta
import json
from .models import Event, EventSchedule, EventRegistration
from .forms import EventForm, EventScheduleForm

User = get_user_model()


# ==================== MODEL TESTS ====================
class EventModelTest(TestCase):
    """Test Event model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Basketball Event',
            sport_type='basketball',
            description='Test description',
            city='Jakarta',
            full_address='Jl. Test No. 123',
            entry_price=Decimal('100000.00'),
            activities='Court, Shower, Locker',
            rating=Decimal('4.50'),
            category='category 1',
            status='available',
            organizer=self.user
        )
    
    def test_event_creation(self):
        """Test event is created correctly"""
        self.assertEqual(self.event.name, 'Test Basketball Event')
        self.assertEqual(self.event.sport_type, 'basketball')
        self.assertEqual(self.event.city, 'Jakarta')
        self.assertEqual(self.event.entry_price, Decimal('100000.00'))
        self.assertEqual(self.event.status, 'available')
        self.assertEqual(self.event.organizer, self.user)
    
    def test_event_str_method(self):
        """Test event string representation"""
        expected = f"{self.event.name} - {self.event.sport_type}"
        self.assertEqual(str(self.event), expected)
    
    def test_get_activities_list(self):
        """Test get_activities_list method"""
        activities = self.event.get_activities_list()
        self.assertEqual(len(activities), 3)
        self.assertIn('Court', activities)
        self.assertIn('Shower', activities)
        self.assertIn('Locker', activities)
    
    def test_get_activities_list_empty(self):
        """Test get_activities_list with empty activities"""
        event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('50000.00'),
            activities='',
            organizer=self.user
        )
        self.assertEqual(event.get_activities_list(), [])
    
    def test_get_status_display_badge(self):
        """Test get_status_display_badge method"""
        self.assertEqual(
            self.event.get_status_display_badge(),
            'badge-available'
        )
        
        self.event.status = 'unavailable'
        self.assertEqual(
            self.event.get_status_display_badge(),
            'badge-unavailable'
        )
    
    def test_event_ordering(self):
        """Test events are ordered by created_at descending"""
        event2 = Event.objects.create(
            name='Newer Event',
            sport_type='soccer',
            city='Bandung',
            full_address='Test Address',
            entry_price=Decimal('75000.00'),
            activities='Field',
            organizer=self.user
        )
        
        events = Event.objects.all()
        self.assertEqual(events[0], event2)  # Newer event first
        self.assertEqual(events[1], self.event)
    
    def test_rating_validation(self):
        """Test rating validators"""
        # Valid rating
        event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Test',
            entry_price=Decimal('50000'),
            activities='Test',
            rating=Decimal('5.00'),
            organizer=self.user
        )
        self.assertEqual(event.rating, Decimal('5.00'))


class EventScheduleModelTest(TestCase):
    """Test EventSchedule model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.schedule = EventSchedule.objects.create(
            event=self.event,
            date=datetime.now().date() + timedelta(days=1),
            is_available=True
        )
    
    def test_schedule_creation(self):
        """Test schedule is created correctly"""
        self.assertEqual(self.schedule.event, self.event)
        self.assertTrue(self.schedule.is_available)
    
    def test_schedule_str_method(self):
        """Test schedule string representation"""
        expected = f"{self.event.name} - {self.schedule.date}"
        self.assertEqual(str(self.schedule), expected)
    
    def test_schedule_ordering(self):
        """Test schedules are ordered by date"""
        schedule2 = EventSchedule.objects.create(
            event=self.event,
            date=datetime.now().date() + timedelta(days=2),
            is_available=True
        )
        
        schedules = EventSchedule.objects.all()
        self.assertEqual(schedules[0], self.schedule)
        self.assertEqual(schedules[1], schedule2)


class EventRegistrationModelTest(TestCase):
    """Test EventRegistration model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.organizer = User.objects.create_user(
            username='organizer',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.organizer
        )
        
        self.schedule = EventSchedule.objects.create(
            event=self.event,
            date=datetime.now().date() + timedelta(days=1),
            is_available=True
        )
        
        self.registration = EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=self.schedule
        )
    
    def test_registration_creation(self):
        """Test registration is created correctly"""
        self.assertEqual(self.registration.event, self.event)
        self.assertEqual(self.registration.user, self.user)
        self.assertEqual(self.registration.schedule, self.schedule)
    
    def test_registration_str_method(self):
        """Test registration string representation"""
        expected = f"{self.user.username} - {self.event.name} ({self.schedule.date})"
        self.assertEqual(str(self.registration), expected)


# ==================== FORM TESTS ====================
class EventFormTest(TestCase):
    """Test EventForm"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_event_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            'name': 'Test Event',
            'sport_type': 'basketball',
            'city': 'Jakarta',
            'full_address': 'Jl. Test No. 123',
            'entry_price': '100000.00',
            'activities': 'Court, Shower',
            'rating': '4.50',
            'description': 'Test description',
            'category': 'category 1',
            'status': 'available'
        }
        form = EventForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_event_form_missing_required_field(self):
        """Test form with missing required field"""
        form_data = {
            'sport_type': 'basketball',
            # Missing 'name'
            'city': 'Jakarta',
            'full_address': 'Test Address',
            'entry_price': '100000',
            'activities': 'Court'
        }
        form = EventForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
    
    def test_event_form_invalid_sport_type(self):
        """Test form with invalid sport type"""
        form_data = {
            'name': 'Test Event',
            'sport_type': 'invalid_sport',
            'city': 'Jakarta',
            'full_address': 'Test Address',
            'entry_price': '100000',
            'activities': 'Court'
        }
        form = EventForm(data=form_data)
        self.assertFalse(form.is_valid())


class EventScheduleFormTest(TestCase):
    """Test EventScheduleForm"""
    
    def test_schedule_form_valid_data(self):
        """Test form with valid data"""
        form_data = {
            'date': datetime.now().date() + timedelta(days=1),
            'is_available': True
        }
        form = EventScheduleForm(data=form_data)
        self.assertTrue(form.is_valid())


# ==================== VIEW TESTS ====================
class EventListViewTest(TestCase):
    """Test event_list view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Basketball Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            status='available',
            organizer=self.user
        )
        
        self.url = reverse('event:event_list')
    
    def test_event_list_view_get(self):
        """Test GET request to event list"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'event/event_list.html')
        self.assertContains(response, 'Test Basketball Event')
    
    def test_event_list_search(self):
        """Test search functionality"""
        response = self.client.get(self.url, {'q': 'Basketball'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event, response.context['events'])
    
    def test_event_list_filter_category(self):
        """Test category filter"""
        response = self.client.get(self.url, {'category': 'basketball'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event, response.context['events'])
    
    def test_event_list_available_only(self):
        """Test available only filter"""
        response = self.client.get(self.url, {'available_only': 'on'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event, response.context['events'])


class AddEventViewTest(TestCase):
    """Test add_event view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.url = reverse('event:add_event')
    
    def test_add_event_view_requires_login(self):
        """Test that add event requires login"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_add_event_view_get_authenticated(self):
        """Test GET request when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'event/add_event.html')
    
    def test_add_event_view_post_valid_data(self):
        """Test POST with valid data"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'New Event',
            'sport_type': 'tennis',
            'city': 'Bandung',
            'full_address': 'Jl. New Address',
            'entry_price': '75000.00',
            'activities': 'Court, Net',
            'rating': '4.00',
            'description': 'New event description',
            'category': 'category 1',
            'status': 'available'
        }
        
        response = self.client.post(self.url, data=form_data)
        
        # Should redirect to event detail
        self.assertEqual(response.status_code, 302)
        
        # Check event was created
        self.assertTrue(Event.objects.filter(name='New Event').exists())
    
    def test_add_event_ajax_request(self):
        """Test AJAX add event request"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'AJAX Event',
            'sport_type': 'soccer',
            'city': 'Jakarta',
            'full_address': 'Test Address',
            'entry_price': '50000',
            'activities': 'Field',
            'category': 'category 1',
            'status': 'available'
        }
        
        response = self.client.post(
            self.url,
            data=form_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('event_id', data)


class EditEventViewTest(TestCase):
    """Test edit_event view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.url = reverse('event:edit_event', kwargs={'pk': self.event.pk})
    
    def test_edit_event_requires_login(self):
        """Test that edit requires login"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_edit_event_requires_organizer(self):
        """Test that only organizer can edit"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 404)  # Not found for non-organizer
    
    def test_edit_event_get_authenticated_organizer(self):
        """Test GET request as organizer"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'event/edit_event.html')
    
    def test_edit_event_post_valid_data(self):
        """Test POST with valid data"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'Updated Event',
            'sport_type': 'tennis',
            'city': 'Bandung',
            'full_address': 'Updated Address',
            'entry_price': '150000.00',
            'activities': 'Updated activities',
            'rating': '5.00',
            'description': 'Updated description',
            'category': 'category 2',
            'status': 'unavailable'
        }
        
        response = self.client.post(self.url, data=form_data)
        
        # Refresh event from database
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, 'Updated Event')
        self.assertEqual(self.event.city, 'Bandung')


class EventDetailViewTest(TestCase):
    """Test event_detail view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.url = reverse('event:event_detail', kwargs={'pk': self.event.pk})
    
    def test_event_detail_view_get(self):
        """Test GET request to event detail"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'event/event_detail.html')
        self.assertEqual(response.context['event'], self.event)
    
    def test_event_detail_404_invalid_pk(self):
        """Test 404 for invalid event pk"""
        url = reverse('event:event_detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class AjaxSearchEventsTest(TestCase):
    """Test ajax_search_events view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.event1 = Event.objects.create(
            name='Basketball Game',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            status='available',
            organizer=self.user
        )
        
        self.event2 = Event.objects.create(
            name='Tennis Match',
            sport_type='tennis',
            city='Bandung',
            full_address='Test Address',
            entry_price=Decimal('75000'),
            activities='Court',
            status='unavailable',
            organizer=self.user
        )
        
        self.url = reverse('event:ajax_search')
    
    def test_ajax_search_all_events(self):
        """Test searching all events"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 2)
    
    def test_ajax_search_by_query(self):
        """Test searching by query"""
        response = self.client.get(self.url, {'search': 'Basketball'})
        data = json.loads(response.content)
        
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['events'][0]['name'], 'Basketball Game')
    
    def test_ajax_search_by_sport(self):
        """Test filtering by sport"""
        response = self.client.get(self.url, {'sport': 'tennis'})
        data = json.loads(response.content)
        
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['events'][0]['sport_type'], 'tennis')
    
    def test_ajax_search_available_only(self):
        """Test filtering available only"""
        response = self.client.get(self.url, {'available': 'true'})
        data = json.loads(response.content)
        
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['events'][0]['status'], 'available')


class AjaxDeleteEventTest(TestCase):
    """Test ajax_delete_event view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.url = reverse('event:ajax_delete', kwargs={'pk': self.event.pk})
    
    def test_delete_event_requires_login(self):
        """Test delete requires login"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
    
    def test_delete_event_success(self):
        """Test successful event deletion"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check event is deleted
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())


class AjaxToggleAvailabilityTest(TestCase):
    """Test ajax_toggle_availability view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            status='available',
            organizer=self.user
        )
        
        self.url = reverse('event:ajax_toggle_availability', kwargs={'pk': self.event.pk})
    
    def test_toggle_availability_requires_login(self):
        """Test toggle requires login"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
    
    def test_toggle_to_unavailable(self):
        """Test toggling to unavailable"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            self.url,
            data=json.dumps({'status': 'unavailable'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'unavailable')


# ==================== URL TESTS ====================
class UrlTests(TestCase):
    """Test URL routing"""
    
    def setUp(self):
        """Set up test data"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
    
    def test_event_list_url_resolves(self):
        """Test event list URL resolves"""
        url = reverse('event:event_list')
        self.assertEqual(url, '/event/')
    
    def test_event_detail_url_resolves(self):
        """Test event detail URL resolves"""
        url = reverse('event:event_detail', kwargs={'pk': self.event.pk})
        self.assertEqual(url, f'/event/{self.event.pk}/')
    
    def test_add_event_url_resolves(self):
        """Test add event URL resolves"""
        url = reverse('event:add_event')
        self.assertEqual(url, '/event/add/')
    
    def test_edit_event_url_resolves(self):
        """Test edit event URL resolves"""
        url = reverse('event:edit_event', kwargs={'pk': self.event.pk})
        self.assertEqual(url, f'/event/{self.event.pk}/edit/')
    
    def test_ajax_search_url_resolves(self):
        """Test AJAX search URL resolves"""
        url = reverse('event:ajax_search')
        self.assertEqual(url, '/event/ajax/search/')
    
    def test_ajax_delete_url_resolves(self):
        """Test AJAX delete URL resolves"""
        url = reverse('event:ajax_delete', kwargs={'pk': self.event.pk})
        self.assertEqual(url, f'/event/{self.event.pk}/ajax/delete/')