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


class EventModelTest(TestCase):
    """Test Event model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Tennis Event',
            sport_type='tennis',
            description='A test tennis event',
            city='Jakarta',
            full_address='Jl. Test No. 1, Jakarta',
            entry_price=Decimal('100000.00'),
            activities='Court, Shower, Locker',
            rating=Decimal('4.50'),
            category='Competition',
            status='available',
            organizer=self.user
        )
    
    def test_event_creation(self):
        """Test event is created correctly"""
        self.assertEqual(self.event.name, 'Test Tennis Event')
        self.assertEqual(self.event.sport_type, 'tennis')
        self.assertEqual(self.event.organizer, self.user)
        self.assertEqual(self.event.status, 'available')
    
    def test_event_str_method(self):
        """Test __str__ method"""
        expected = 'Test Tennis Event - tennis'
        self.assertEqual(str(self.event), expected)
    
    def test_get_activities_list(self):
        """Test get_activities_list method"""
        activities = self.event.get_activities_list()
        self.assertEqual(len(activities), 3)
        self.assertIn('Court', activities)
        self.assertIn('Shower', activities)
    
    def test_get_activities_list_empty(self):
        """Test get_activities_list with empty activities"""
        event = Event.objects.create(
            name='Event No Activities',
            sport_type='soccer',
            city='Bandung',
            full_address='Jl. Test',
            entry_price=Decimal('50000'),
            activities='',
            organizer=self.user
        )
        self.assertEqual(event.get_activities_list(), [''])
    
    def test_event_ordering(self):
        """Test events are ordered by created_at descending"""
        event2 = Event.objects.create(
            name='Newer Event',
            sport_type='basketball',
            city='Surabaya',
            full_address='Jl. Test 2',
            entry_price=Decimal('75000'),
            activities='Court',
            organizer=self.user
        )
        events = Event.objects.all()
        self.assertEqual(events[0], event2)
        self.assertEqual(events[1], self.event)
    
    def test_event_rating_validation(self):
        """Test rating validators"""
        # This will be caught by form validation in real usage
        event = Event(
            name='Test',
            sport_type='tennis',
            city='Jakarta',
            full_address='Test',
            entry_price=Decimal('100000'),
            activities='Test',
            rating=Decimal('5.00'),  # Max valid
            organizer=self.user
        )
        event.full_clean()  # Should not raise


class EventScheduleModelTest(TestCase):
    """Test EventSchedule model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.schedule = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
            is_available=True
        )
    
    def test_schedule_creation(self):
        """Test schedule is created correctly"""
        self.assertEqual(self.schedule.event, self.event)
        self.assertTrue(self.schedule.is_available)
    
    def test_schedule_str_method(self):
        """Test __str__ method"""
        expected = f"{self.event.name} - {self.schedule.date}"
        self.assertEqual(str(self.schedule), expected)
    
    def test_schedule_unique_together(self):
        """Test unique constraint on event and date"""
        with self.assertRaises(Exception):
            EventSchedule.objects.create(
                event=self.event,
                date=self.schedule.date,
                is_available=True
            )
    
    def test_schedule_ordering(self):
        """Test schedules are ordered by date"""
        schedule2 = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=14),
            is_available=True
        )
        schedules = EventSchedule.objects.all()
        self.assertEqual(schedules[0], self.schedule)
        self.assertEqual(schedules[1], schedule2)


class EventRegistrationModelTest(TestCase):
    """Test EventRegistration model"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.schedule = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
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
        """Test __str__ method"""
        expected = f"{self.user.username} - {self.event.name} ({self.schedule.date})"
        self.assertEqual(str(self.registration), expected)
    
    def test_registration_unique_together(self):
        """Test unique constraint"""
        with self.assertRaises(Exception):
            EventRegistration.objects.create(
                event=self.event,
                user=self.user,
                schedule=self.schedule
            )


class EventFormTest(TestCase):
    """Test EventForm"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
    
    def test_valid_form(self):
        """Test form with valid data"""
        form_data = {
            'name': 'Test Event',
            'sport_type': 'tennis',
            'city': 'Jakarta',
            'full_address': 'Jl. Test No. 1',
            'entry_price': '100000.00',
            'activities': 'Court, Shower',
            'rating': '4.5',
            'description': 'Test description',
            'category': 'Competition',
            'status': 'available'
        }
        form = EventForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_invalid_form_missing_required(self):
        """Test form with missing required fields"""
        form_data = {
            'name': 'Test Event',
            # Missing sport_type, city, etc.
        }
        form = EventForm(data=form_data)
        self.assertFalse(form.is_valid())
    
    def test_form_field_widgets(self):
        """Test form widgets are configured"""
        form = EventForm()
        self.assertIn('form-input', form.fields['name'].widget.attrs['class'])
        self.assertIn('form-select', form.fields['sport_type'].widget.attrs['class'])


class EventScheduleFormTest(TestCase):
    """Test EventScheduleForm"""
    
    def test_valid_form(self):
        """Test form with valid data"""
        form_data = {
            'date': date.today() + timedelta(days=7),
            'is_available': True
        }
        form = EventScheduleForm(data=form_data)
        self.assertTrue(form.is_valid())
    
    def test_form_widgets(self):
        """Test form widgets"""
        form = EventScheduleForm()
        self.assertEqual(form.fields['date'].widget.attrs['type'], 'date')


class EventListViewTest(TestCase):
    """Test event_list view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event1 = Event.objects.create(
            name='Tennis Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test 1',
            entry_price=Decimal('100000'),
            activities='Court',
            status='available',
            organizer=self.user
        )
        
        self.event2 = Event.objects.create(
            name='Basketball Event',
            sport_type='basketball',
            city='Bandung',
            full_address='Jl. Test 2',
            entry_price=Decimal('75000'),
            activities='Court',
            status='unavailable',
            organizer=self.user
        )
    
    def test_event_list_view_get(self):
        """Test GET request to event list"""
        response = self.client.get(reverse('Event:event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tennis Event')
        self.assertContains(response, 'Basketball Event')
    
    def test_event_list_with_search(self):
        """Test search functionality"""
        response = self.client.get(reverse('Event:event_list'), {'q': 'Tennis'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tennis Event')
        self.assertNotContains(response, 'Basketball Event')
    
    def test_event_list_with_category_filter(self):
        """Test category filter"""
        response = self.client.get(reverse('Event:event_list'), {'category': 'tennis'})
        self.assertEqual(response.status_code, 200)
    
    def test_event_list_available_only(self):
        """Test available only filter"""
        response = self.client.get(reverse('Event:event_list'), {'available_only': 'on'})
        self.assertEqual(response.status_code, 200)


class AjaxSearchEventsTest(TestCase):
    """Test ajax_search_events view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
    
    def test_ajax_search(self):
        """Test AJAX search endpoint"""
        response = self.client.get(
            reverse('Event:ajax_search'),
            {'search': 'Test', 'sport': 'All', 'available': 'false'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertGreater(data['count'], 0)
    
    def test_ajax_search_with_sport_filter(self):
        """Test AJAX search with sport filter"""
        response = self.client.get(
            reverse('Event:ajax_search'),
            {'search': '', 'sport': 'tennis', 'available': 'false'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])


class AddEventViewTest(TestCase):
    """Test add_event view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.client.login(username='testuser', password='testpass123')
    
    def test_add_event_get(self):
        """Test GET request to add event"""
        response = self.client.get(reverse('Event:add_event'))
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], EventForm)
    
    def test_add_event_post_valid(self):
        """Test POST with valid data"""
        data = {
            'name': 'New Event',
            'sport_type': 'tennis',
            'city': 'Jakarta',
            'full_address': 'Jl. Test',
            'entry_price': '100000',
            'activities': 'Court',
            'rating': '4.5',
            'category': 'Competition',
            'status': 'available'
        }
        response = self.client.post(reverse('Event:add_event'), data)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertEqual(event.name, 'New Event')
    
    def test_add_event_requires_login(self):
        """Test add event requires authentication"""
        self.client.logout()
        response = self.client.get(reverse('Event:add_event'))
        self.assertEqual(response.status_code, 302)  # Redirect to login


class EditEventViewTest(TestCase):
    """Test edit_event view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        self.other_user = User.objects.create_user(
            username='otheruser',
            email='other@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_edit_event_get(self):
        """Test GET request to edit event"""
        response = self.client.get(
            reverse('Event:edit_event', kwargs={'pk': self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.context['form'], EventForm)
    
    def test_edit_event_post_valid(self):
        """Test POST with valid data"""
        data = {
            'name': 'Updated Event',
            'sport_type': 'basketball',
            'city': 'Bandung',
            'full_address': 'Jl. Updated',
            'entry_price': '150000',
            'activities': 'Court, Shower',
            'rating': '4.8',
            'category': 'Training',
            'status': 'available'
        }
        response = self.client.post(
            reverse('Event:edit_event', kwargs={'pk': self.event.pk}),
            data
        )
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, 'Updated Event')
    
    def test_edit_event_wrong_organizer(self):
        """Test edit event by non-organizer"""
        self.client.logout()
        self.client.login(username='otheruser', password='testpass123')
        response = self.client.get(
            reverse('Event:edit_event', kwargs={'pk': self.event.pk})
        )
        self.assertEqual(response.status_code, 404)


class DeleteEventViewTest(TestCase):
    """Test ajax_delete_event view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_delete_event(self):
        """Test delete event"""
        response = self.client.post(
            reverse('Event:ajax_delete', kwargs={'pk': self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(Event.objects.count(), 0)


class EventDetailViewTest(TestCase):
    """Test event_detail view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.schedule = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
            is_available=True
        )
    
    def test_event_detail_get(self):
        """Test GET request to event detail"""
        response = self.client.get(
            reverse('Event:event_detail', kwargs={'pk': self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['event'], self.event)
    
    def test_event_detail_with_user_registered(self):
        """Test detail view when user is registered"""
        self.client.login(username='testuser', password='testpass123')
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=self.schedule
        )
        response = self.client.get(
            reverse('Event:event_detail', kwargs={'pk': self.event.pk})
        )
        self.assertTrue(response.context['user_registered'])


class JoinEventViewTest(TestCase):
    """Test ajax_join_event view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_join_event_success(self):
        """Test successful event join"""
        future_date = date.today() + timedelta(days=7)
        data = {
            'date': future_date.strftime('%m / %d / %Y')
        }
        response = self.client.post(
            reverse('Event:ajax_join', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
    
    def test_join_event_without_date(self):
        """Test join event without date"""
        response = self.client.post(
            reverse('Event:ajax_join', kwargs={'pk': self.event.pk}),
            json.dumps({}),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
    
    def test_join_event_already_registered(self):
        """Test joining event when already registered"""
        schedule = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
            is_available=True
        )
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=schedule
        )
        
        data = {
            'date': schedule.date.strftime('%m / %d / %Y')
        }
        response = self.client.post(
            reverse('Event:ajax_join', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class ToggleAvailabilityViewTest(TestCase):
    """Test ajax_toggle_availability view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            status='available',
            organizer=self.user
        )
        
        self.client.login(username='testuser', password='testpass123')
    
    def test_toggle_to_unavailable(self):
        """Test toggling event to unavailable"""
        data = {'status': 'unavailable'}
        response = self.client.post(
            reverse('Event:ajax_toggle_availability', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'unavailable')
    
    def test_toggle_invalid_status(self):
        """Test toggling with invalid status"""
        data = {'status': 'invalid'}
        response = self.client.post(
            reverse('Event:ajax_toggle_availability', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class GetSchedulesViewTest(TestCase):
    """Test ajax_get_schedules view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
            is_available=True
        )
        EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=14),
            is_available=True
        )
    
    def test_get_schedules(self):
        """Test getting event schedules"""
        response = self.client.get(
            reverse('Event:ajax_schedules', kwargs={'pk': self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['schedules']), 2)


class FilterSportViewTest(TestCase):
    """Test ajax_filter_sport view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@test.com',
            password='testpass123'
        )
        
        Event.objects.create(
            name='Tennis Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test 1',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
        
        Event.objects.create(
            name='Basketball Event',
            sport_type='basketball',
            city='Bandung',
            full_address='Jl. Test 2',
            entry_price=Decimal('75000'),
            activities='Court',
            organizer=self.user
        )
    
    def test_filter_by_sport(self):
        """Test filtering by sport type"""
        response = self.client.get(
            reverse('Event:ajax_filter'),
            {'sport': 'tennis'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['events']), 1)
        self.assertEqual(data['events'][0]['sport_type'], 'tennis')
    
    def test_filter_all_sports(self):
        """Test filtering with 'All' option"""
        response = self.client.get(
            reverse('Event:ajax_filter'),
            {'sport': 'All'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['events']), 2)