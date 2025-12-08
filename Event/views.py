from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q, Min
from datetime import datetime, date
import json

from .models import Event, EventSchedule, EventRegistration
from .forms import EventForm

# ==================== CUSTOM LOGIN DECORATOR ====================
def custom_login_required(view_func):
    """Custom decorator that checks session instead of Django auth"""
    from Auth_Profile.models import User

    def wrapper(request, *args, **kwargs):
        # Check if this is a JSON endpoint (for Flutter)
        is_json_endpoint = '/json/' in request.path or request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if 'user_id' not in request.session:
            if is_json_endpoint:
                return JsonResponse({
                    'success': False,
                    'message': 'Please login first',
                    'redirect_url': '/login/'
                }, status=401)
            return redirect('/login/')
        
        try:
            request.user = User.objects.get(id=request.session['user_id'])
        except User.DoesNotExist:
            request.session.flush()
            if is_json_endpoint:
                return JsonResponse({
                    'success': False,
                    'message': 'Session expired. Please login again',
                    'redirect_url': '/login/'
                }, status=401)
            return redirect('/login/')
        
        return view_func(request, *args, **kwargs)
    return wrapper

# ==================== HELPER FUNCTIONS ====================
def _to_decimal(s):
    from decimal import Decimal
    if not s:
        return Decimal('0')
    try:
        return Decimal(s)
    except:
        return Decimal('0')

# ==================== EVENT LIST ====================
def event_list(request):
    try:
        from Auth_Profile.models import User
        request.user = User.objects.get(id=request.session['user_id'])
    except:
        request.user = None

    events = Event.objects.annotate(
        next_schedule_date=Min(
            'schedules__date',
            filter=Q(
                schedules__is_available=True,
                schedules__date__gte=datetime.now().date()
            )
        )
    )
    query = request.GET.get("q", "")
    selected_category = request.GET.get("category", "")
    available_only = request.GET.get("available_only") == "on"

    if query:
        events = events.filter(
            Q(name__icontains=query)
            | Q(city__icontains=query)
            | Q(full_address__icontains=query)
            | Q(sport_type__icontains=query)
        )

    if selected_category and selected_category.lower() != "all":
        events = events.filter(sport_type__iexact=selected_category)

    if available_only:
        events = events.filter(status__iexact="Available")

    events = events.order_by("-created_at")

    sport_choices = [
        "All", "Tennis", "Basketball", "Soccer", "Badminton", "Volleyball",
        "Futsal", "Football", "Running", "Cycling", "Swimming", "Other"
    ]

    # Get list of event IDs that current user has registered for
    user_registered_events = []
    if request.user:
        user_registered_events = EventRegistration.objects.filter(
            user=request.user
        ).values_list('event_id', flat=True).distinct()

    context = {
        "events": events,
        "query": query,
        "sport_choices": sport_choices,
        "selected_category": selected_category,
        "available_only": available_only,
        "user": request.user,
        "user_registered_events": list(user_registered_events),
    }

    return render(request, "event/event_list.html", context)

# ==================== AJAX EVENT SEARCH ====================
@require_http_methods(["GET"])
def ajax_search_events(request):
    try:
        try:
            from Auth_Profile.models import User
            request.user = User.objects.get(id=request.session['user_id'])
        except:
            request.user = None

        search_query = request.GET.get('search', '')
        sport_filter = request.GET.get('sport', 'All')
        show_available = request.GET.get('available', 'false') == 'true'
        
        events = Event.objects.all()
        
        if sport_filter != 'All':
            events = events.filter(sport_type=sport_filter)
        
        if search_query:
            events = events.filter(
                Q(name__icontains=search_query) |
                Q(city__icontains=search_query) |
                Q(description__icontains=search_query)
            )
        
        if show_available:
            events = events.filter(status='available')
        
        events_data = []
        for event in events:
            organizer_name = getattr(event.organizer, 'username', None) or getattr(event.organizer, 'email', 'Unknown')
            events_data.append({
                'id': event.id,
                'name': event.name,
                'sport_type': event.sport_type,
                'city': event.city,
                'rating': str(event.rating),
                'entry_price': str(event.entry_price),
                'status': event.status,
                'photo_url': event.photo.url if event.photo else '/static/images/default-event.jpg',
                'organizer': organizer_name,
                'full_address': event.full_address,
                'is_organizer': request.user and request.user.id == event.organizer.id if request.user else False,
            })
        
        return JsonResponse({
            'success': True,
            'events': events_data,
            'count': len(events_data)
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error loading events: {str(e)}',
            'events': []
        }, status=500)

# ==================== ADD EVENT ====================
@custom_login_required
def add_event(request):
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        form = EventForm(request.POST, request.FILES if request.FILES else None)
        
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user

            event.save()
            
            # Process schedule_dates
            schedule_dates_json = request.POST.get('schedule_dates', '[]')
            
            try:
                schedule_dates = json.loads(schedule_dates_json)
                
                # Create EventSchedule objects for each date
                for date_str in schedule_dates:
                    try:
                        # Parse date string (format: YYYY-MM-DD)
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                        
                        # Create or get schedule
                        EventSchedule.objects.get_or_create(
                            event=event,
                            date=date_obj,
                            defaults={'is_available': True}
                        )
                            
                    except ValueError:
                        continue
                        
            except json.JSONDecodeError:
                pass
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Event created successfully!',
                    'event_id': event.id,
                    'redirect_url': f'/event/{event.id}/'
                })
            return redirect(f'/event/{event.id}/')
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = EventForm()
    
    return render(request, 'event/add_event.html', {'form': form})

# ==================== EDIT EVENT ====================
@custom_login_required
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
        return redirect('/event/')

    schedules = EventSchedule.objects.filter(event=event).order_by('date')

    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        form = EventForm(request.POST, request.FILES if request.FILES else None, instance=event)
        
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            
            # Handle clear photo
            if request.POST.get('clear_photo'):
                event.photo.delete(save=False)
                event.photo = None

            event.save()

            # Update schedules from JSON list
            schedule_dates_json = request.POST.get('schedule_dates', '[]')
            try:
                schedule_dates = json.loads(schedule_dates_json)
                new_dates = set()
                for date_str in schedule_dates:
                    try:
                        new_dates.add(datetime.strptime(date_str, '%Y-%m-%d').date())
                    except ValueError:
                        continue

                # Remove schedules not in new list
                EventSchedule.objects.filter(event=event).exclude(date__in=new_dates).delete()

                # Add or keep schedules in new list
                for d in new_dates:
                    EventSchedule.objects.get_or_create(
                        event=event,
                        date=d,
                        defaults={'is_available': True}
                    )
            except json.JSONDecodeError:
                pass
            
            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Event updated successfully!',
                    'event_id': event.id,
                    'redirect_url': f'/event/{event.id}/'
                })
            return redirect(f'/event/{event.id}/')
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = EventForm(instance=event)
    
    return render(request, 'event/edit_event.html', {
        'form': form,
        'event': event,
        'schedules': schedules
    })

# ==================== DELETE EVENT ====================
@custom_login_required
@require_http_methods(["POST"])
def ajax_delete_event(request, pk):
    try:
        event = get_object_or_404(Event, pk=pk)
        
        if event.organizer != request.user:
            return JsonResponse({
                'success': False, 
                'message': 'You are not authorized to delete this event'
            }, status=403)
        
        event_name = event.name
        event.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Event "{event_name}" deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# ==================== EVENT DETAIL ====================
def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    try:
        from Auth_Profile.models import User
        user = User.objects.get(id=request.session['user_id'])
    except:
        user = None
    
    schedules = EventSchedule.objects.filter(
        event=event, 
        is_available=True, 
        date__gte=datetime.now().date()
    ).order_by('date')
    
    user_registered = False
    user_registrations = []
    if user:
        user_registrations = EventRegistration.objects.filter(
            event=event, 
            user=user
        ).select_related('schedule').order_by('schedule__date')
        user_registered = user_registrations.exists()
    
    context = {
        'event': event,
        'schedules': schedules,
        'user_registered': user_registered,
        'user_registrations': user_registrations,
        'organizer': event.organizer,
        'activities': getattr(event, 'get_activities_list', lambda: [])(),
        'user': user
    }
    return render(request, 'event/event_detail.html', context)

# ==================== AJAX JOIN EVENT ====================
@custom_login_required
@require_http_methods(["POST"])
def ajax_join_event(request, pk):
    try:
        data = json.loads(request.body)
        schedule_id = data.get('schedule_id')
        
        if not schedule_id:
            return JsonResponse({'success': False, 'message': 'Please select a date'}, status=400)
        
        event = get_object_or_404(Event, pk=pk)
        schedule = get_object_or_404(EventSchedule, pk_event_sched=schedule_id, event=event)

        if EventRegistration.objects.filter(event=event, user=request.user, schedule=schedule).exists():
            return JsonResponse({'success': False, 'message': 'Already registered'}, status=400)

        registration = EventRegistration.objects.create(event=event, user=request.user, schedule=schedule)
        return JsonResponse({
            'success': True, 
            'message': 'Successfully joined the event!', 
            'registration_id': str(registration.pk_event_regis)
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# ==================== AJAX CANCEL REGISTRATION ====================
@custom_login_required
@require_http_methods(["POST"])
def ajax_cancel_registration(request, pk):
    try:
        event = get_object_or_404(Event, pk=pk)
        
        # Find user's registration for this event
        registrations = EventRegistration.objects.filter(event=event, user=request.user)
        
        if not registrations.exists():
            return JsonResponse({'success': False, 'message': 'No registration found'}, status=400)
        
        # Delete all registrations (in case user registered for multiple schedules)
        count = registrations.count()
        registrations.delete()
        
        return JsonResponse({
            'success': True, 
            'message': f'Successfully cancelled {count} registration(s)!',
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# ==================== AJAX TOGGLE AVAILABILITY ====================
@custom_login_required
@require_http_methods(["POST"])
def ajax_toggle_availability(request, pk):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            is_available = data.get('is_available')

            if type(is_available) is not bool:
                return JsonResponse({'success': False, 'message': 'Invalid status'})

            event = get_object_or_404(Event, pk=pk)

            # Update field status sesuai boolean
            event.status = 'available' if is_available else 'unavailable'
            event.save()

            return JsonResponse({
                'success': True,
                'message': f'Event marked as {"available" if is_available else "unavailable"}'
            })

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method'})

@require_http_methods(["GET"])
def ajax_filter_sport(request):
    try:
        from Auth_Profile.models import User
        request.user = User.objects.get(id=request.session['user_id'])
    except:
        request.user = None

    sport = request.GET.get('sport', 'All')
    if sport == 'All':
        events = Event.objects.all()
    else:
        events = Event.objects.filter(sport_type=sport)

    events_data = []
    for event in events:
        organizer_name = getattr(event.organizer, 'username', None) or getattr(event.organizer, 'email', 'Unknown')
        events_data.append({
            'id': event.id,
            'name': event.name,
            'sport_type': event.sport_type,
            'city': event.city,
            'rating': str(event.rating),
            'entry_price': str(event.entry_price),
            'status': event.status,
            'photo_url': event.photo.url if event.photo else '/static/images/default-event.jpg',
            'organizer': organizer_name,
            'full_address': event.full_address,
            'is_organizer': request.user and request.user.id == event.organizer.id if request.user else False,
        })

    return JsonResponse({
        'success': True,
        'events': events_data,
        'sport': sport
    })

@custom_login_required
@require_http_methods(["POST"])
def ajax_validate_event_form(request):
    """
    Validate event form fields via AJAX without using Django auth
    """
    try:
        data = json.loads(request.body)

        # Import EventForm hanya untuk validasi
        from .forms import EventForm
        form = EventForm(data)

        if form.is_valid():
            return JsonResponse({'success': True})
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

def ajax_get_schedules(request, pk):
    """
    Mengambil semua schedule untuk Event tertentu (berdasarkan pk) dan mengembalikannya sebagai JSON
    """
    try:
        schedules = EventSchedule.objects.filter(event_id=pk, is_available=True, date__gte=datetime.now().date())
        data = [
            {
                "id": str(schedule.pk_event_sched),
                "date": schedule.date.strftime("%Y-%m-%d"),
                "is_available": schedule.is_available,
            }
            for schedule in schedules
        ]
        return JsonResponse({"success": True, "schedules": data})
    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=404)

# ==================== MY BOOKINGS ====================
@custom_login_required
def my_bookings(request):
    # Get all registrations for current user
    registrations = EventRegistration.objects.filter(
        user=request.user
    ).select_related('event', 'schedule', 'event__organizer').order_by('-registered_at')
    
    # Group by event
    bookings = {}
    for reg in registrations:
        event_id = reg.event.id
        if event_id not in bookings:
            bookings[event_id] = {
                'event': reg.event,
                'schedules': [],
                'registered_at': reg.registered_at
            }
        bookings[event_id]['schedules'].append(reg.schedule)
    
    context = {
        'bookings': bookings.values(),
        'total_bookings': len(bookings),
        'user': request.user
    }
    
    return render(request, 'event/my_bookings.html', context)

# ==================== JSON ENDPOINTS FOR FLUTTER ====================
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def json_events(request):
    """Get all events as JSON"""
    try:
        try:
            from Auth_Profile.models import User
            user = User.objects.get(id=request.session.get('user_id')) if 'user_id' in request.session else None
        except:
            user = None
        
        events = Event.objects.all()
        
        # Get user registered events
        user_registered = []
        if user:
            user_registered = EventRegistration.objects.filter(user=user).values_list('event_id', flat=True)
        
        data = []
        for event in events:
            data.append({
                'id': event.id,
                'name': event.name,
                'sport_type': event.sport_type,
                'description': event.description or '',
                'city': event.city,
                'full_address': event.full_address,
                'google_maps_link': event.google_maps_link or '',
                'entry_price': str(event.entry_price),
                'activities': event.activities or '',
                'rating': str(event.rating),
                'photo_url': event.photo.url if event.photo else '',
                'status': event.status,
                'category': event.category,
                'organizer_id': event.organizer.id,
                'organizer_name': event.organizer.nama if hasattr(event.organizer, 'nama') else event.organizer.email,
                'created_at': event.created_at.isoformat(),
                'is_organizer': user.id == event.organizer.id if user else False,
                'is_registered': event.id in user_registered,
            })
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error loading events: {str(e)}'
        }, status=500)

@csrf_exempt
def json_event_detail(request, pk):
    """Get single event detail with schedules"""
    try:
        try:
            from Auth_Profile.models import User
            user = User.objects.get(id=request.session.get('user_id')) if 'user_id' in request.session else None
        except:
            user = None
        
        try:
            event = Event.objects.get(pk=pk)
        except Event.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Event not found'}, status=404)
        
        # Get schedules
        schedules = EventSchedule.objects.filter(
            event=event,
            is_available=True,
            date__gte=datetime.now().date()
        ).order_by('date')
        
        schedules_data = [{
            'id': str(s.pk_event_sched),
            'date': s.date.isoformat(),
        } for s in schedules]
        
        # Check if user registered
        user_schedules = []
        if user:
            registrations = EventRegistration.objects.filter(event=event, user=user)
            user_schedules = [str(r.schedule.pk_event_sched) for r in registrations]
        
        data = {
            'id': event.id,
            'name': event.name,
            'sport_type': event.sport_type,
            'description': event.description or '',
            'city': event.city,
            'full_address': event.full_address,
            'google_maps_link': event.google_maps_link or '',
            'entry_price': str(event.entry_price),
            'activities': event.activities or '',
            'rating': str(event.rating),
            'photo_url': event.photo.url if event.photo else '',
            'status': event.status,
            'category': event.category,
            'organizer_id': event.organizer.id,
            'organizer_name': event.organizer.nama if hasattr(event.organizer, 'nama') else event.organizer.email,
            'created_at': event.created_at.isoformat(),
            'is_organizer': user.id == event.organizer.id if user else False,
            'schedules': schedules_data,
            'user_schedules': user_schedules,
        }
        
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Error loading event: {str(e)}'
        }, status=500)

@csrf_exempt
@custom_login_required
def json_create_event(request):
    """Create event from Flutter"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        
        # Create event
        event = Event.objects.create(
            name=data['name'],
            sport_type=data['sport_type'],
            description=data.get('description', ''),
            city=data['city'],
            full_address=data['full_address'],
            entry_price=data['entry_price'],
            activities=data.get('activities', ''),
            rating=data.get('rating', 0),
            google_maps_link=data.get('google_maps_link', ''),
            category=data.get('category', 'category 1'),
            status=data.get('status', 'available'),
            organizer=request.user
        )
        
        # Create schedules if provided
        if 'schedule_dates' in data:
            for date_str in data['schedule_dates']:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    EventSchedule.objects.get_or_create(
                        event=event,
                        date=date_obj,
                        defaults={'is_available': True}
                    )
                except ValueError:
                    continue
        
        return JsonResponse({
            'success': True,
            'message': 'Event created successfully!',
            'event_id': event.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@csrf_exempt
@custom_login_required
def json_join_event(request, pk):
    """Join event from Flutter"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        schedule_id = data.get('schedule_id')
        
        if not schedule_id:
            return JsonResponse({'success': False, 'message': 'Please select a date'}, status=400)
        
        event = get_object_or_404(Event, pk=pk)
        schedule = get_object_or_404(EventSchedule, pk_event_sched=schedule_id, event=event)
        
        # Check if already registered
        if EventRegistration.objects.filter(event=event, user=request.user, schedule=schedule).exists():
            return JsonResponse({'success': False, 'message': 'Already registered for this date'}, status=400)
        
        # Create registration
        EventRegistration.objects.create(
            event=event,
            user=request.user,
            schedule=schedule
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully joined the event!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@csrf_exempt
@custom_login_required
def json_cancel_event(request, pk):
    """Cancel registration from Flutter"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        event = get_object_or_404(Event, pk=pk)
        registrations = EventRegistration.objects.filter(event=event, user=request.user)
        
        if not registrations.exists():
            return JsonResponse({'success': False, 'message': 'No registration found'}, status=400)
        
        count = registrations.count()
        registrations.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Successfully cancelled {count} registration(s)!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@csrf_exempt
@custom_login_required
def json_my_bookings(request):
    """Get user's bookings"""
    registrations = EventRegistration.objects.filter(
        user=request.user
    ).select_related('event', 'schedule').order_by('-registered_at')
    
    # Group by event
    bookings = {}
    for reg in registrations:
        event_id = reg.event.id
        if event_id not in bookings:
            bookings[event_id] = {
                'event': {
                    'id': reg.event.id,
                    'name': reg.event.name,
                    'sport_type': reg.event.sport_type,
                    'city': reg.event.city,
                    'rating': str(reg.event.rating),
                    'entry_price': str(reg.event.entry_price),
                },
                'schedules': []
            }
        bookings[event_id]['schedules'].append({
            'id': str(reg.schedule.pk_event_sched),
            'date': reg.schedule.date.isoformat(),
        })
    
    return JsonResponse(list(bookings.values()), safe=False)

@csrf_exempt
@custom_login_required
def json_toggle_availability(request, pk):
    """Toggle event availability from Flutter"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        event = get_object_or_404(Event, pk=pk)
        
        # Check if user is the organizer
        if event.organizer.id != request.user.id:
            return JsonResponse({'success': False, 'message': 'You are not authorized'}, status=403)
        
        data = json.loads(request.body)
        is_available = data.get('is_available')
        
        if type(is_available) is not bool:
            return JsonResponse({'success': False, 'message': 'Invalid status'}, status=400)
        
        # Update event status
        event.status = 'available' if is_available else 'unavailable'
        event.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Event marked as {"available" if is_available else "unavailable"}',
            'status': event.status
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@csrf_exempt
@custom_login_required
def json_edit_event(request, pk):
    """Edit event from Flutter"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        event = get_object_or_404(Event, pk=pk)
        
        # Check if user is the organizer
        if event.organizer.id != request.user.id:
            return JsonResponse({'success': False, 'message': 'You are not authorized'}, status=403)
        
        data = json.loads(request.body)
        
        # Update event fields
        event.name = data.get('name', event.name)
        event.sport_type = data.get('sport_type', event.sport_type)
        event.description = data.get('description', event.description)
        event.city = data.get('city', event.city)
        event.full_address = data.get('full_address', event.full_address)
        event.entry_price = data.get('entry_price', event.entry_price)
        event.activities = data.get('activities', event.activities)
        event.rating = data.get('rating', event.rating)
        event.google_maps_link = data.get('google_maps_link', event.google_maps_link)
        event.category = data.get('category', event.category)
        event.status = data.get('status', event.status)
        
        event.save()
        
        # Update schedules if provided
        if 'schedule_dates' in data:
            schedule_dates = data['schedule_dates']
            new_dates = set()
            
            for date_str in schedule_dates:
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
                    new_dates.add(date_obj)
                except ValueError:
                    continue
            
            # Remove schedules not in new list
            EventSchedule.objects.filter(event=event).exclude(date__in=new_dates).delete()
            
            # Add or keep schedules in new list
            for d in new_dates:
                EventSchedule.objects.get_or_create(
                    event=event,
                    date=d,
                    defaults={'is_available': True}
                )
        
        return JsonResponse({
            'success': True,
            'message': 'Event updated successfully!',
            'event_id': event.id
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)

@csrf_exempt
@custom_login_required
def json_delete_event(request, pk):
    """Delete event from Flutter"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Method not allowed'}, status=405)
    
    try:
        event = get_object_or_404(Event, pk=pk)
        
        # Check if user is the organizer
        if event.organizer.id != request.user.id:
            return JsonResponse({'success': False, 'message': 'You are not authorized'}, status=403)
        
        event_name = event.name
        event.delete()
        
        return JsonResponse({
            'success': True,
            'message': f'Event "{event_name}" deleted successfully!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)