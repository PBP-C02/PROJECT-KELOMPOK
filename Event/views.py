from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from datetime import datetime
import json

from .models import Event, EventSchedule, EventRegistration
from .forms import EventForm

# ==================== CUSTOM LOGIN DECORATOR ====================
def custom_login_required(view_func):
    """Custom decorator that checks session instead of Django auth"""
    from Auth_Profile.models import User

    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
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

    events = Event.objects.all()
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

    context = {
        "events": events,
        "query": query,
        "sport_choices": sport_choices,
        "selected_category": selected_category,
        "available_only": available_only,
        "user": request.user
    }

    return render(request, "event/event_list.html", context)

# ==================== AJAX EVENT SEARCH ====================
@require_http_methods(["GET"])
def ajax_search_events(request):
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
        events_data.append({
            'id': event.id,
            'name': event.name,
            'sport_type': event.sport_type,
            'city': event.city,
            'rating': str(event.rating),
            'entry_price': str(event.entry_price),
            'status': event.status,
            'photo_url': event.photo.url if event.photo else '/static/images/default-event.jpg',
            'organizer': getattr(event.organizer, 'username', 'Unknown'),
            'full_address': event.full_address,
            'is_organizer': request.user and request.user.id == event.organizer.id if request.user else False,
        })
    
    return JsonResponse({
        'success': True,
        'events': events_data,
        'count': len(events_data)
    })

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
    
    if request.method == 'POST':
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        if request.POST.get('clear_photo') == 'true' and event.photo:
            event.photo.delete()
            event.photo = None
        form = EventForm(request.POST, request.FILES if request.FILES else None, instance=event)
        if form.is_valid():
            form.save()
            if is_ajax:
                return JsonResponse({'success': True, 'message': 'Event updated successfully!', 'event_id': event.id})
            return redirect(f'/event/{event.id}/')
        else:
            if is_ajax:
                return JsonResponse({'success': False, 'errors': form.errors}, status=400)
    else:
        form = EventForm(instance=event)
    
    return render(request, 'event/edit_event.html', {'form': form, 'event': event})

# ==================== DELETE EVENT ====================
@custom_login_required
@require_http_methods(["POST"])
def ajax_delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    if event.organizer != request.user:
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    event.delete()
    return JsonResponse({'success': True, 'message': 'Event deleted successfully'})

# ==================== EVENT DETAIL ====================
def event_detail(request, pk):
    try:
        from Auth_Profile.models import User
        request.user = User.objects.get(id=request.session['user_id'])
    except:
        request.user = None

    event = get_object_or_404(Event, pk=pk)
    schedules = event.schedules.filter(is_available=True, date__gte=datetime.now().date())
    
    user_registered = False
    if request.user:
        user_registered = EventRegistration.objects.filter(event=event, user=request.user).exists()
    
    context = {
        'event': event,
        'schedules': schedules,
        'user_registered': user_registered,
        'organizer': event.organizer,
        'activities': getattr(event, 'get_activities_list', lambda: [])(),
        'user': request.user
    }
    return render(request, 'event/event_detail.html', context)

# ==================== AJAX JOIN EVENT ====================
@custom_login_required
@require_http_methods(["POST"])
def ajax_join_event(request, pk):
    try:
        data = json.loads(request.body)
        selected_date = data.get('date')
        if not selected_date:
            return JsonResponse({'success': False, 'message': 'Please select a date'}, status=400)
        
        event = get_object_or_404(Event, pk=pk)
        date_obj = datetime.strptime(selected_date, '%m / %d / %Y').date()
        schedule, created = EventSchedule.objects.get_or_create(event=event, date=date_obj, defaults={'is_available': True})

        if EventRegistration.objects.filter(event=event, user=request.user, schedule=schedule).exists():
            return JsonResponse({'success': False, 'message': 'Already registered'}, status=400)

        registration = EventRegistration.objects.create(event=event, user=request.user, schedule=schedule)
        return JsonResponse({'success': True, 'message': 'Successfully joined', 'registration_id': str(registration.pk_event_regis)})
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
        events_data.append({
            'id': event.id,
            'name': event.name,
            'sport_type': event.sport_type,
            'city': event.city,
            'rating': str(event.rating),
            'entry_price': str(event.entry_price),
            'status': event.status,
            'photo_url': event.photo.url if event.photo else '/static/images/default-event.jpg',
            'organizer': getattr(event.organizer, 'username', 'Unknown'),
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

from django.http import JsonResponse
from .models import EventSchedule

def ajax_get_schedules(request, pk):
    """
    Mengambil semua schedule untuk Event tertentu (berdasarkan pk) dan mengembalikannya sebagai JSON
    """
    try:
        schedules = EventSchedule.objects.filter(event_id=pk)
        data = [
            {
                "id": schedule.id,
                "date": schedule.date.strftime("%Y-%m-%d"),
                "start_time": schedule.start_time.strftime("%H:%M"),
                "end_time": schedule.end_time.strftime("%H:%M"),
            }
            for schedule in schedules
        ]
        return JsonResponse({"success": True, "schedules": data})
    except EventSchedule.DoesNotExist:
        return JsonResponse({"success": False, "message": "Schedules not found"}, status=404)
