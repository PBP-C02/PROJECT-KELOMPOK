from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from datetime import datetime, timedelta, date
import json
from .models import Event, EventSchedule, EventRegistration
from .forms import EventForm, EventScheduleForm

User = get_user_model()


# ==================== HELPER FUNCTION ====================
def create_test_user(username='testuser', email='test@example.com', password='testpass123'):
    """Helper function to create test user"""
    return User.objects.create_user(
        username=username,
        email=email,
        password=password,
    )


def create_test_image():
    """Helper function to create test image file"""
    from io import BytesIO
    from PIL import Image
    
    # Create a simple image
    image = Image.new('RGB', (100, 100), color='red')
    image_file = BytesIO()
    image.save(image_file, format='JPEG')
    image_file.seek(0)
    
    return SimpleUploadedFile(
        name='test_image.jpg',
        content=image_file.read(),
        content_type='image/jpeg'
    )


# ==================== MODEL TESTS ====================
class EventModelTest(TestCase):
    """Test Event model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = create_test_user()
        
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
    
    def test_event_with_photo(self):
        """Test event creation with photo"""
        event = Event.objects.create(
            name='Event with Photo',
            sport_type='tennis',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user,
            photo=create_test_image()
        )
        self.assertTrue(event.photo)
        self.assertIn('events/', event.photo.name)


class EventScheduleModelTest(TestCase):
    """Test EventSchedule model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = create_test_user()
        
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
        self.assertIsNotNone(self.schedule.pk_event_sched)
    
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
    
    def test_schedule_unique_together(self):
        """Test unique_together constraint for event and date"""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            EventSchedule.objects.create(
                event=self.event,
                date=self.schedule.date,
                is_available=True
            )


class EventRegistrationModelTest(TestCase):
    """Test EventRegistration model"""
    
    def setUp(self):
        """Set up test data"""
        self.user = create_test_user()
        self.organizer = create_test_user(username='organizer', email='organizer@example.com')
        
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
        self.assertIsNotNone(self.registration.pk_event_regis)
    
    def test_registration_str_method(self):
        """Test registration string representation"""
        expected = f"{self.user.username} - {self.event.name} ({self.schedule.date})"
        self.assertEqual(str(self.registration), expected)
    
    def test_registration_unique_together(self):
        """Test unique_together constraint for event, user, and schedule"""
        from django.db import IntegrityError
        
        with self.assertRaises(IntegrityError):
            EventRegistration.objects.create(
                event=self.event,
                user=self.user,
                schedule=self.schedule
            )
    
    def test_registration_ordering(self):
        """Test registrations are ordered by registered_at descending"""
        user2 = create_test_user(username='user2', email='user2@example.com')
        registration2 = EventRegistration.objects.create(
            event=self.event,
            user=user2,
            schedule=self.schedule
        )
        
        registrations = EventRegistration.objects.all()
        self.assertEqual(registrations[0], registration2)  # Newer first
        self.assertEqual(registrations[1], self.registration)


# ==================== FORM TESTS ====================
class EventFormTest(TestCase):
    """Test EventForm"""
    
    def setUp(self):
        """Set up test data"""
        self.user = create_test_user()
    
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
            'activities': 'Court',
            'status': 'available',
            'category': 'category 1'
        }
        form = EventForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_event_form_with_photo(self):
        """Test form with photo upload"""
        form_data = {
            'name': 'Test Event',
            'sport_type': 'basketball',
            'city': 'Jakarta',
            'full_address': 'Test Address',
            'entry_price': '100000',
            'activities': 'Court',
            'status': 'available',
            'category': 'category 1'
        }
        file_data = {'photo': create_test_image()}
        form = EventForm(data=form_data, files=file_data)
        self.assertTrue(form.is_valid())
    
    def test_event_form_widgets(self):
        """Test form widgets are properly configured"""
        form = EventForm()
        self.assertIn('class', form.fields['name'].widget.attrs)
        self.assertEqual(form.fields['name'].widget.attrs['class'], 'form-input')
    
    def test_event_form_labels(self):
        """Test form labels"""
        form = EventForm()
        self.assertEqual(form.fields['name'].label, 'Event Name')
        self.assertEqual(form.fields['photo'].label, 'Event Photo (optional)')


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
    
    def test_schedule_form_missing_date(self):
        """Test form with missing date"""
        form_data = {
            'is_available': True
        }
        form = EventScheduleForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('date', form.errors)


# ==================== VIEW TESTS ====================
class EventListViewTest(TestCase):
    """Test event_list view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        
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
        self.assertIn(self.event, response.context['events'])
    
    def test_event_list_search(self):
        """Test search functionality"""
        response = self.client.get(self.url, {'q': 'Basketball'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event, response.context['events'])
    
    def test_event_list_search_no_results(self):
        """Test search with no results"""
        response = self.client.get(self.url, {'q': 'NonExistentEvent'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['events']), 0)
    
    def test_event_list_filter_category(self):
        """Test category filter"""
        response = self.client.get(self.url, {'category': 'basketball'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event, response.context['events'])
    
    def test_event_list_available_only(self):
        """Test available only filter"""
        # Create unavailable event
        Event.objects.create(
            name='Unavailable Event',
            sport_type='tennis',
            city='Bandung',
            full_address='Test',
            entry_price=Decimal('50000'),
            activities='Court',
            status='unavailable',
            organizer=self.user
        )
        
        response = self.client.get(self.url, {'available_only': 'on'})
        self.assertEqual(response.status_code, 200)
        self.assertIn(self.event, response.context['events'])
        self.assertEqual(len(response.context['events']), 1)


class AddEventViewTest(TestCase):
    """Test add_event view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        self.url = reverse('event:add_event')
    
    def test_add_event_view_requires_login(self):
        """Test that add event requires login"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)  # Redirect to login
        self.assertIn('login', response.url)
    
    def test_add_event_view_get_authenticated(self):
        """Test GET request when authenticated"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'event/add_event.html')
        self.assertIsInstance(response.context['form'], EventForm)
    
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
        event = Event.objects.get(name='New Event')
        self.assertEqual(event.organizer, self.user)
        self.assertEqual(event.city, 'Bandung')
    
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
        self.assertIn('redirect_url', data)
    
    def test_add_event_ajax_invalid_data(self):
        """Test AJAX request with invalid data"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            # Missing required fields
            'name': 'Invalid Event'
        }
        
        response = self.client.post(
            self.url,
            data=form_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('errors', data)


class EditEventViewTest(TestCase):
    """Test edit_event view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        self.other_user = create_test_user(username='otheruser', email='other@example.com')
        
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
        self.assertEqual(response.context['event'], self.event)
    
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
    
    def test_edit_event_ajax_request(self):
        """Test AJAX edit request"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'AJAX Updated',
            'sport_type': 'soccer',
            'city': 'Surabaya',
            'full_address': 'AJAX Address',
            'entry_price': '120000',
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
        
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, 'AJAX Updated')


class EventDetailViewTest(TestCase):
    """Test event_detail view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court, Locker, Shower',
            organizer=self.user
        )
        
        # Create future schedule
        self.schedule = EventSchedule.objects.create(
            event=self.event,
            date=datetime.now().date() + timedelta(days=1),
            is_available=True
        )
        
        self.url = reverse('event:event_detail', kwargs={'pk': self.event.pk})
    
    def test_event_detail_view_get(self):
        """Test GET request to event detail"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'event/event_detail.html')
        self.assertEqual(response.context['event'], self.event)
        self.assertIn(self.schedule, response.context['schedules'])
    
    def test_event_detail_404_invalid_pk(self):
        """Test 404 for invalid event pk"""
        url = reverse('event:event_detail', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)
    
    def test_event_detail_user_registered_check(self):
        """Test user_registered context variable"""
        self.client.login(username='testuser', password='testpass123')
        
        # Create registration
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=self.schedule
        )
        
        response = self.client.get(self.url)
        self.assertTrue(response.context['user_registered'])
    
    def test_event_detail_activities_list(self):
        """Test activities are split into list"""
        response = self.client.get(self.url)
        activities = response.context['activities']
        self.assertEqual(len(activities), 3)
        self.assertIn('Court', activities)


class AjaxSearchEventsTest(TestCase):
    """Test ajax_search_events view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        
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
    
    def test_ajax_search_combined_filters(self):
        """Test combined filters"""
        response = self.client.get(self.url, {
            'search': 'Game',
            'sport': 'basketball',
            'available': 'true'
        })
        data = json.loads(response.content)
        
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['events'][0]['name'], 'Basketball Game')


class AjaxDeleteEventTest(TestCase):
    """Test ajax_delete_event view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        self.other_user = create_test_user(username='otheruser', email='other@example.com')
        
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
    
    def test_delete_event_requires_organizer(self):
        """Test only organizer can delete"""
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 404)
    
    def test_delete_event_success(self):
        """Test successful event deletion"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.post(self.url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Check event is deleted
        self.assertFalse(Event.objects.filter(pk=self.event.pk).exists())
    
    def test_delete_event_get_method_not_allowed(self):
        """Test GET method is not allowed"""
        self.client.login(username='testuser', password='testpass123')
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)  # Method not allowed


class AjaxToggleAvailabilityTest(TestCase):
    """Test ajax_toggle_availability view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        
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
    
    def test_toggle_to_available(self):
        """Test toggling to available"""
        self.event.status = 'unavailable'
        self.event.save()
        
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            self.url,
            data=json.dumps({'status': 'available'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'available')
    
    def test_toggle_invalid_status(self):
        """Test toggling with invalid status"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            self.url,
            data=json.dumps({'status': 'invalid'}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


class AjaxJoinEventTest(TestCase):
    """Test ajax_join_event view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        self.organizer = create_test_user(username='organizer', email='organizer@example.com')
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.organizer
        )
        
        self.url = reverse('event:ajax_join', kwargs={'pk': self.event.pk})
    
    def test_join_event_requires_login(self):
        """Test join requires login"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
    
    def test_join_event_success(self):
        """Test successful event join"""
        self.client.login(username='testuser', password='testpass123')
        
        future_date = datetime.now().date() + timedelta(days=1)
        date_str = future_date.strftime('%m / %d / %Y')
        
        response = self.client.post(
            self.url,
            data=json.dumps({'date': date_str}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('registration_id', data)
        
        # Check registration was created
        self.assertTrue(
            EventRegistration.objects.filter(
                event=self.event,
                user=self.user
            ).exists()
        )
    
    def test_join_event_missing_date(self):
        """Test join without date"""
        self.client.login(username='testuser', password='testpass123')
        
        response = self.client.post(
            self.url,
            data=json.dumps({}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
    
    def test_join_event_already_registered(self):
        """Test joining event already registered"""
        self.client.login(username='testuser', password='testpass123')
        
        future_date = datetime.now().date() + timedelta(days=1)
        schedule = EventSchedule.objects.create(
            event=self.event,
            date=future_date,
            is_available=True
        )
        
        # Create existing registration
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=schedule
        )
        
        date_str = future_date.strftime('%m / %d / %Y')
        
        response = self.client.post(
            self.url,
            data=json.dumps({'date': date_str}),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


class AjaxGetSchedulesTest(TestCase):
    """Test ajax_get_schedules view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test Address',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        # Create future schedules
        self.schedule1 = EventSchedule.objects.create(
            event=self.event,
            date=datetime.now().date() + timedelta(days=1),
            is_available=True
        )
        
        self.schedule2 = EventSchedule.objects.create(
            event=self.event,
            date=datetime.now().date() + timedelta(days=2),
            is_available=True
        )
        
        # Create past schedule (should not be returned)
        EventSchedule.objects.create(
            event=self.event,
            date=datetime.now().date() - timedelta(days=1),
            is_available=True
        )
        
        self.url = reverse('event:ajax_schedules', kwargs={'pk': self.event.pk})
    
    def test_get_schedules_success(self):
        """Test getting schedules"""
        response = self.client.get(self.url)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['schedules']), 2)  # Only future schedules
    
    def test_get_schedules_invalid_event(self):
        """Test getting schedules for invalid event"""
        url = reverse('event:ajax_schedules', kwargs={'pk': 99999})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class AjaxFilterSportTest(TestCase):
    """Test ajax_filter_sport view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        
        self.event1 = Event.objects.create(
            name='Basketball Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.event2 = Event.objects.create(
            name='Tennis Event',
            sport_type='tennis',
            city='Bandung',
            full_address='Test',
            entry_price=Decimal('75000'),
            activities='Court',
            organizer=self.user
        )
        
        self.url = reverse('event:ajax_filter')
    
    def test_filter_by_sport(self):
        """Test filtering by specific sport"""
        response = self.client.get(self.url, {'sport': 'basketball'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['events']), 1)
        self.assertEqual(data['events'][0]['sport_type'], 'basketball')
    
    def test_filter_all_sports(self):
        """Test filtering with 'All'"""
        response = self.client.get(self.url, {'sport': 'All'})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['events']), 2)


class AjaxValidateEventFormTest(TestCase):
    """Test ajax_validate_event_form view"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        self.url = reverse('event:ajax_validate')
    
    def test_validate_requires_login(self):
        """Test validation requires login"""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, 302)
    
    def test_validate_valid_data(self):
        """Test validation with valid data"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            'name': 'Test Event',
            'sport_type': 'basketball',
            'city': 'Jakarta',
            'full_address': 'Test Address',
            'entry_price': '100000',
            'activities': 'Court',
            'status': 'available',
            'category': 'category 1'
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(form_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
    
    def test_validate_invalid_data(self):
        """Test validation with invalid data"""
        self.client.login(username='testuser', password='testpass123')
        
        form_data = {
            # Missing required fields
            'name': 'Test'
        }
        
        response = self.client.post(
            self.url,
            data=json.dumps(form_data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertIn('errors', data)


# ==================== URL TESTS ====================
class UrlTests(TestCase):
    """Test URL routing"""
    
    def setUp(self):
        """Set up test data"""
        self.user = create_test_user()
        
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
    
    def test_ajax_join_url_resolves(self):
        """Test AJAX join URL resolves"""
        url = reverse('event:ajax_join', kwargs={'pk': self.event.pk})
        self.assertEqual(url, f'/event/{self.event.pk}/ajax/join/')
    
    def test_ajax_toggle_availability_url_resolves(self):
        """Test AJAX toggle availability URL resolves"""
        url = reverse('event:ajax_toggle_availability', kwargs={'pk': self.event.pk})
        self.assertEqual(url, f'/event/{self.event.pk}/ajax/toggle-availability/')
    
    def test_ajax_schedules_url_resolves(self):
        """Test AJAX schedules URL resolves"""
        url = reverse('event:ajax_schedules', kwargs={'pk': self.event.pk})
        self.assertEqual(url, f'/event/{self.event.pk}/ajax/schedules/')
    
    def test_ajax_filter_url_resolves(self):
        """Test AJAX filter URL resolves"""
        url = reverse('event:ajax_filter')
        self.assertEqual(url, '/event/ajax/filter/')
    
    def test_ajax_validate_url_resolves(self):
        """Test AJAX validate URL resolves"""
        url = reverse('event:ajax_validate')
        self.assertEqual(url, '/event/ajax/validate/')


# ==================== INTEGRATION TESTS ====================
class EventWorkflowIntegrationTest(TestCase):
    """Test complete event workflow"""
    
    def setUp(self):
        """Set up test data"""
        self.client = Client()
        self.user = create_test_user()
        self.participant = create_test_user(username='participant', email='participant@example.com')
    
    def test_complete_event_workflow(self):
        """Test complete workflow: create, edit, join, toggle availability"""
        # 1. Login as organizer
        self.client.login(username='testuser', password='testpass123')
        
        # 2. Create event
        create_url = reverse('event:add_event')
        event_data = {
            'name': 'Integration Test Event',
            'sport_type': 'basketball',
            'city': 'Jakarta',
            'full_address': 'Test Address',
            'entry_price': '100000',
            'activities': 'Court, Locker',
            'status': 'available',
            'category': 'category 1'
        }
        response = self.client.post(create_url, data=event_data)
        self.assertEqual(response.status_code, 302)
        
        event = Event.objects.get(name='Integration Test Event')
        
        # 3. Edit event
        edit_url = reverse('event:edit_event', kwargs={'pk': event.pk})
        event_data['name'] = 'Updated Integration Event'
        response = self.client.post(edit_url, data=event_data)
        event.refresh_from_db()
        self.assertEqual(event.name, 'Updated Integration Event')
        
        # 4. Login as participant
        self.client.login(username='participant', password='testpass123')
        
        # 5. Join event
        join_url = reverse('event:ajax_join', kwargs={'pk': event.pk})
        future_date = (datetime.now().date() + timedelta(days=1)).strftime('%m / %d / %Y')
        response = self.client.post(
            join_url,
            data=json.dumps({'date': future_date}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        # 6. Check registration exists
        self.assertTrue(
            EventRegistration.objects.filter(
                event=event,
                user=self.participant
            ).exists()
        )
        
        # 7. Login back as organizer
        self.client.login(username='testuser', password='testpass123')
        
        # 8. Toggle availability
        toggle_url = reverse('event:ajax_toggle_availability', kwargs={'pk': event.pk})
        response = self.client.post(
            toggle_url,
            data=json.dumps({'status': 'unavailable'}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        
        event.refresh_from_db()
        self.assertEqual(event.status, 'unavailable')