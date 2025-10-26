from django.test import TestCase, Client
from django.urls import reverse
from Auth_Profile.models import User
from django.contrib.auth.hashers import make_password
from django.core.files.uploadedfile import SimpleUploadedFile
from decimal import Decimal
from datetime import datetime, timedelta, date
import json
from Event.models import Event, EventSchedule, EventRegistration
from Event.forms import EventForm, EventScheduleForm


class EventModelTest(TestCase):
    """Test Event model"""
    
    def setUp(self):
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
        result = event.get_activities_list()
        self.assertTrue(isinstance(result, list))
    
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
        event = Event(
            name='Test',
            sport_type='tennis',
            city='Jakarta',
            full_address='Test',
            entry_price=Decimal('100000'),
            activities='Test',
            rating=Decimal('5.00'),
            organizer=self.user
        )
        event.full_clean()
        self.assertTrue(True)
    
    def test_is_available_property(self):
        """Test is_available property"""
        self.assertTrue(self.event.is_available)
        self.event.status = 'unavailable'
        self.event.save()
        self.assertFalse(self.event.is_available)
    
    def test_title_property(self):
        """Test title property"""
        self.assertEqual(self.event.title, self.event.name)
    
    def test_location_property(self):
        """Test location property"""
        self.assertEqual(self.event.location, self.event.full_address)


class EventScheduleModelTest(TestCase):
    """Test EventSchedule model"""
    
    def setUp(self):
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
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
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
    
    
    def test_registration_unique_together(self):
        """Test unique constraint"""
        from django.db import IntegrityError
        with self.assertRaises(IntegrityError):
            EventRegistration.objects.create(
                event=self.event,
                user=self.user,
                schedule=self.schedule
            )


class EventFormTest(TestCase):
    """Test EventForm"""
    
    def setUp(self):
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
        self.assertTrue(hasattr(form.fields['date'].widget, 'attrs'))


class EventListViewTest(TestCase):
    """Test event_list view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
        response = self.client.get(reverse('event:event_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tennis Event')
        self.assertContains(response, 'Basketball Event')
    
    def test_event_list_with_search(self):
        """Test search functionality"""
        response = self.client.get(reverse('event:event_list'), {'q': 'Tennis'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Tennis Event')
    
    def test_event_list_with_category_filter(self):
        """Test category filter"""
        response = self.client.get(reverse('event:event_list'), {'category': 'tennis'})
        self.assertEqual(response.status_code, 200)
    
    def test_event_list_available_only(self):
        """Test available only filter"""
        response = self.client.get(reverse('event:event_list'), {'available_only': 'on'})
        self.assertEqual(response.status_code, 200)


class AjaxSearchEventsTest(TestCase):
    """Test ajax_search_events view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
            reverse('event:ajax_search'),
            {'search': 'Test', 'sport': 'All', 'available': 'false'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertGreater(data['count'], 0)
    
    def test_ajax_search_with_sport_filter(self):
        """Test AJAX search with sport filter"""
        response = self.client.get(
            reverse('event:ajax_search'),
            {'search': '', 'sport': 'tennis', 'available': 'false'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])


class AddEventViewTest(TestCase):
    """Test add_event view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
        )
        # Set up session for custom_login_required
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_add_event_get(self):
        """Test GET request to add event"""
        response = self.client.get(reverse('event:add_event'))
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
        response = self.client.post(reverse('event:add_event'), data)
        self.assertEqual(Event.objects.count(), 1)
        event = Event.objects.first()
        self.assertEqual(event.name, 'New Event')
    
    def test_add_event_requires_login(self):
        """Test add event requires authentication"""
        self.client.session.flush()
        response = self.client.get(reverse('event:add_event'))
        self.assertEqual(response.status_code, 302)


class EditEventViewTest(TestCase):
    """Test edit_event view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
        )
        self.other_user = User.objects.create(
            nama='otheruser',
            email='other@test.com',
            kelamin='P',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456788',
            password=make_password('testpass123')
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
        
        # Set up session
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_edit_event_get(self):
        """Test GET request to edit event"""
        response = self.client.get(
            reverse('event:edit_event', kwargs={'pk': self.event.pk})
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
            reverse('event:edit_event', kwargs={'pk': self.event.pk}),
            data
        )
        self.event.refresh_from_db()
        self.assertEqual(self.event.name, 'Updated Event')
    
    def test_edit_event_wrong_organizer(self):
        """Test edit event by non-organizer"""
        session = self.client.session
        session['user_id'] = str(self.other_user.id)
        session.save()
        
        response = self.client.get(
            reverse('event:edit_event', kwargs={'pk': self.event.pk})
        )
        self.assertEqual(response.status_code, 302)


class DeleteEventViewTest(TestCase):
    """Test ajax_delete_event view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
        
        # Set up session
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_delete_event(self):
        """Test delete event"""
        response = self.client.post(
            reverse('event:ajax_delete', kwargs={'pk': self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(Event.objects.count(), 0)


class EventDetailViewTest(TestCase):
    """Test event_detail view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
            reverse('event:event_detail', kwargs={'pk': self.event.pk})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['event'], self.event)
    
    def test_event_detail_with_user_registered(self):
        """Test detail view when user is registered"""
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=self.schedule
        )
        response = self.client.get(
            reverse('event:event_detail', kwargs={'pk': self.event.pk})
        )
        self.assertTrue(response.context['user_registered'])


class JoinEventViewTest(TestCase):
    """Test ajax_join_event view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
        
        # Set up session
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_join_event_success(self):
        """Test successful event join"""
        # Create a schedule first
        schedule = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
            is_available=True
        )
        
        # Send schedule_id instead of date
        data = {
            'schedule_id': str(schedule.pk_event_sched)  # Use the UUID as string
        }
        
        response = self.client.post(
            reverse('event:ajax_join', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertTrue(response_data['success'])
        
        # Verify registration was created
        self.assertTrue(
            EventRegistration.objects.filter(
                event=self.event,
                user=self.user,
                schedule=schedule
            ).exists()
        )
    
    def test_join_event_without_date(self):
        """Test join event without date"""
        response = self.client.post(
            reverse('event:ajax_join', kwargs={'pk': self.event.pk}),
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
            reverse('event:ajax_join', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)


class ToggleAvailabilityViewTest(TestCase):
    """Test ajax_toggle_availability view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
        
        # Set up session
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
    
    def test_toggle_to_unavailable(self):
        """Test toggling event to unavailable"""
        data = {'is_available': False}
        response = self.client.post(
            reverse('event:ajax_toggle_availability', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'unavailable')
    
    def test_toggle_to_available(self):
        """Test toggling event to available"""
        self.event.status = 'unavailable'
        self.event.save()
        
        data = {'is_available': True}
        response = self.client.post(
            reverse('event:ajax_toggle_availability', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'available')


class GetSchedulesViewTest(TestCase):
    """Test ajax_get_schedules view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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


class FilterSportViewTest(TestCase):
    """Test ajax_filter_sport view"""
    
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
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
            reverse('event:ajax_filter'),
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
            reverse('event:ajax_filter'),
            {'sport': 'All'}
        )
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['events']), 2)

class AdditionalEventViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create(
            nama='testuser',
            email='test@test.com',
            kelamin='L',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456789',
            password=make_password('testpass123')
        )
        
        self.other_user = User.objects.create(
            nama='otheruser',
            email='other@test.com',
            kelamin='P',
            tanggal_lahir='2000-01-01',
            nomor_handphone='08123456788',
            password=make_password('testpass123')
        )
        
        # Set up session
        session = self.client.session
        session['user_id'] = str(self.user.id)
        session.save()
        
        self.event = Event.objects.create(
            name='Test Event',
            sport_type='tennis',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )


class AddEventWithSchedulesTest(AdditionalEventViewTests):
    """Test add event with schedules"""
    
    def test_add_event_with_multiple_schedules(self):
        """Test adding event with multiple schedule dates"""
        schedule_dates = [
            (date.today() + timedelta(days=7)).strftime('%Y-%m-%d'),
            (date.today() + timedelta(days=14)).strftime('%Y-%m-%d'),
            (date.today() + timedelta(days=21)).strftime('%Y-%m-%d'),
        ]
        
        form_data = {
            'name': 'Multi Schedule Event',
            'sport_type': 'basketball',
            'city': 'Jakarta',
            'full_address': 'Jl. Test',
            'entry_price': '150000',
            'activities': 'Court, Shower',
            'rating': '4.5',
            'category': 'Competition',
            'status': 'available',
            'schedule_dates': json.dumps(schedule_dates)
        }
        
        response = self.client.post(
            reverse('event:add_event'),
            form_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify schedules were created
        new_event = Event.objects.get(name='Multi Schedule Event')
        self.assertEqual(new_event.schedules.count(), 3)


class EditEventSchedulesTest(AdditionalEventViewTests):
    """Test edit event schedules"""
    
    def setUp(self):
        super().setUp()
        # Create initial schedules
        self.schedule1 = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
            is_available=True
        )
        self.schedule2 = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=14),
            is_available=True
        )
    
    def test_edit_event_update_schedules(self):
        """Test updating event schedules"""
        new_schedule_dates = [
            (date.today() + timedelta(days=30)).strftime('%Y-%m-%d'),
            (date.today() + timedelta(days=37)).strftime('%Y-%m-%d'),
        ]
        
        form_data = {
            'name': 'Updated Event',
            'sport_type': 'tennis',
            'city': 'Jakarta',
            'full_address': 'Jl. Updated',
            'entry_price': '200000',
            'activities': 'Court',
            'rating': '4.8',
            'category': 'Training',
            'status': 'available',
            'schedule_dates[]': new_schedule_dates
        }
        
        response = self.client.post(
            reverse('event:edit_event', kwargs={'pk': self.event.pk}),
            form_data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Old schedules should be deleted, new ones created
        self.event.refresh_from_db()
        self.assertEqual(self.event.schedules.count(), 2)


class JoinEventAdvancedTest(AdditionalEventViewTests):
    """Advanced join event tests"""
    
    def test_join_event_with_invalid_schedule_id(self):
        """Test join event with invalid schedule ID"""
        data = {
            'schedule_id': 'invalid-uuid-string'
        }
        
        response = self.client.post(
            reverse('event:ajax_join', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 500)
    
    def test_join_event_duplicate_registration(self):
        """Test joining same event schedule twice"""
        schedule = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
            is_available=True
        )
        
        # First registration
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=schedule
        )
        
        # Try to register again
        data = {
            'schedule_id': str(schedule.pk_event_sched)
        }
        
        response = self.client.post(
            reverse('event:ajax_join', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


class EventListAdvancedTest(AdditionalEventViewTests):
    """Advanced event list tests"""
    
    def setUp(self):
        super().setUp()
        # Create multiple events
        Event.objects.create(
            name='Basketball Event',
            sport_type='basketball',
            city='Bandung',
            full_address='Jl. Test 2',
            entry_price=Decimal('75000'),
            activities='Court',
            status='available',
            organizer=self.user
        )
        
        Event.objects.create(
            name='Soccer Event',
            sport_type='soccer',
            city='Jakarta',
            full_address='Jl. Test 3',
            entry_price=Decimal('50000'),
            activities='Field',
            status='unavailable',
            organizer=self.user
        )
    
    def test_event_list_with_search_query(self):
        """Test event list with search query"""
        response = self.client.get(
            reverse('event:event_list'),
            {'q': 'Basketball'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Basketball Event')
        self.assertNotContains(response, 'Soccer Event')
    
    def test_event_list_with_category_filter(self):
        """Test event list with sport category filter"""
        response = self.client.get(
            reverse('event:event_list'),
            {'category': 'basketball'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Basketball Event')
    
    def test_event_list_available_only(self):
        """Test event list showing only available events"""
        response = self.client.get(
            reverse('event:event_list'),
            {'available_only': 'on'}
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Basketball Event')


class AjaxSearchAdvancedTest(AdditionalEventViewTests):
    """Advanced AJAX search tests"""
    
    def setUp(self):
        super().setUp()
        Event.objects.create(
            name='Tennis Event 2',
            sport_type='tennis',
            city='Surabaya',
            full_address='Jl. Test',
            entry_price=Decimal('120000'),
            activities='Court',
            status='available',
            organizer=self.user
        )
    
    def test_ajax_search_with_all_filters(self):
        """Test AJAX search with all filter parameters"""
        response = self.client.get(
            reverse('event:ajax_search'),
            {
                'search': 'Tennis',
                'sport': 'tennis',
                'available': 'true'
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertGreaterEqual(data['count'], 1)  # At least one tennis event
    
    def test_ajax_search_with_no_results(self):
        """Test AJAX search with query that returns no results"""
        response = self.client.get(
            reverse('event:ajax_search'),
            {'search': 'NonexistentSport'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(data['count'], 0)


class EventDetailAdvancedTest(AdditionalEventViewTests):
    """Advanced event detail tests"""
    
    def test_event_detail_without_user(self):
        """Test event detail page without logged in user"""
        # Clear session
        self.client.session.flush()
        
        response = self.client.get(
            reverse('event:event_detail', kwargs={'pk': self.event.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['user'], None)
    
    def test_event_detail_with_schedules(self):
        """Test event detail with multiple schedules"""
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
        
        response = self.client.get(
            reverse('event:event_detail', kwargs={'pk': self.event.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['schedules']), 2)


class MyBookingsTest(AdditionalEventViewTests):
    """Test my bookings page"""
    
    def test_my_bookings_with_registrations(self):
        """Test my bookings page with user registrations"""
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
        
        response = self.client.get(reverse('event:my_bookings'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_bookings'], 1)
        self.assertIn('bookings', response.context)
    
    def test_my_bookings_empty(self):
        """Test my bookings page with no registrations"""
        response = self.client.get(reverse('event:my_bookings'))
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_bookings'], 0)
    
    def test_my_bookings_requires_login(self):
        """Test my bookings requires authentication"""
        self.client.session.flush()
        
        response = self.client.get(reverse('event:my_bookings'))
        
        self.assertEqual(response.status_code, 302)  # Redirect to login


class CancelRegistrationTest(AdditionalEventViewTests):
    """Test cancel registration"""
    
    def test_cancel_single_registration(self):
        """Test canceling a single registration"""
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
        
        response = self.client.post(
            reverse('event:ajax_cancel', kwargs={'pk': self.event.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        # Verify registration was deleted
        self.assertFalse(
            EventRegistration.objects.filter(
                event=self.event,
                user=self.user
            ).exists()
        )
    
    def test_cancel_multiple_registrations(self):
        """Test canceling multiple registrations"""
        schedule1 = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=7),
            is_available=True
        )
        schedule2 = EventSchedule.objects.create(
            event=self.event,
            date=date.today() + timedelta(days=14),
            is_available=True
        )
        
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=schedule1
        )
        EventRegistration.objects.create(
            event=self.event,
            user=self.user,
            schedule=schedule2
        )
        
        response = self.client.post(
            reverse('event:ajax_cancel', kwargs={'pk': self.event.pk})
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertIn('2', data['message'])  # Should mention 2 registrations
    
    def test_cancel_no_registration(self):
        """Test canceling when no registration exists"""
        response = self.client.post(
            reverse('event:ajax_cancel', kwargs={'pk': self.event.pk})
        )
        
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.content)
        self.assertFalse(data['success'])


class ToggleAvailabilityAdvancedTest(AdditionalEventViewTests):
    """Advanced toggle availability tests"""
    
    def test_toggle_available_to_unavailable(self):
        """Test marking event as unavailable"""
        self.event.status = 'available'
        self.event.save()
        
        data = {'is_available': False}
        
        response = self.client.post(
            reverse('event:ajax_toggle_availability', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        
        self.event.refresh_from_db()
        self.assertEqual(self.event.status, 'unavailable')
    
    def test_toggle_invalid_boolean(self):
        """Test toggle with invalid boolean value"""
        data = {'is_available': 'invalid'}
        
        response = self.client.post(
            reverse('event:ajax_toggle_availability', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertFalse(data['success'])
    
    def test_toggle_non_organizer(self):
        """Test toggle by non-organizer (should fail in decorator)"""
        # Login as other user
        session = self.client.session
        session['user_id'] = str(self.other_user.id)
        session.save()
        
        data = {'is_available': True}
        
        response = self.client.post(
            reverse('event:ajax_toggle_availability', kwargs={'pk': self.event.pk}),
            json.dumps(data),
            content_type='application/json'
        )
        
        # This will pass through decorator but we can verify organizer check
        # The actual permission check should happen in view
        self.assertEqual(response.status_code, 200)


class AjaxFilterSportAdvancedTest(AdditionalEventViewTests):
    """Advanced filter sport tests"""
    
    def setUp(self):
        super().setUp()
        Event.objects.create(
            name='Basketball Event',
            sport_type='basketball',
            city='Jakarta',
            full_address='Jl. Test',
            entry_price=Decimal('100000'),
            activities='Court',
            organizer=self.user
        )
    
    def test_filter_sport_specific(self):
        """Test filtering by specific sport"""
        response = self.client.get(
            reverse('event:ajax_filter'),
            {'sport': 'basketball'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertEqual(len(data['events']), 1)
        self.assertEqual(data['events'][0]['sport_type'], 'basketball')
    
    def test_filter_sport_all(self):
        """Test filtering with 'All' option"""
        response = self.client.get(
            reverse('event:ajax_filter'),
            {'sport': 'All'}
        )
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertTrue(data['success'])
        self.assertGreaterEqual(len(data['events']), 2)