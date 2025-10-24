from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Event, EventSchedule, EventRegistration
from .forms import EventForm, EventScheduleForm
import json
from datetime import datetime

# ==================== EVENT LIST WITH AJAX SEARCH & FILTER ====================
def event_list(request):
    """Halaman listing event dengan search & filter"""
    events = Event.objects.all()
    query = request.GET.get("q", "")
    selected_category = request.GET.get("category", "")
    available_only = request.GET.get("available_only") == "on"

    # 🔍 Search logic
    if query:
        events = events.filter(
            Q(name__icontains=query)
            | Q(city__icontains=query)
            | Q(full_address__icontains=query)
            | Q(sport_type__icontains=query)
        )

    # 🎯 Filter kategori
    if selected_category and selected_category.lower() != "all":
        events = events.filter(sport_type__iexact=selected_category)

    # ✅ Hanya event yang available
    if available_only:
        events = events.filter(status__iexact="Available")

    # 🔄 Urutkan dari terbaru
    events = events.order_by("-created_at")

    # 📋 List pilihan sport untuk filter
    sport_choices = [
        "All",
        "Tennis",
        "Basketball",
        "Soccer",
        "Badminton",
        "Volleyball",
        "Futsal",
        "Football",
        "Running",
        "Cycling",
        "Swimming",
        "Other",
    ]

    # 📦 Context dikirim ke template
    context = {
        "events": events,
        "query": query,
        "sport_choices": sport_choices,
        "selected_category": selected_category,
        "available_only": available_only,
    }

    return render(request, "event/event_list.html", context)



# ==================== AJAX EVENT SEARCH ====================
@require_http_methods(["GET"])
def ajax_search_events(request):
    """
    AJAX endpoint for searching events without page reload
    """
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
            'organizer': event.organizer.get_full_name() or event.organizer.username,
            'full_address': event.full_address,
            'is_organizer': request.user.is_authenticated and request.user == event.organizer,
        })
    
    return JsonResponse({
        'success': True,
        'events': events_data,
        'count': len(events_data)
    })


# ==================== ADD EVENT WITH AJAX ====================
@login_required(login_url='Auth_Profile:login')
def add_event(request):
    """
    Add new event with AJAX form submission (Image 2)
    """
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            
            # If AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Event created successfully!',
                    'event_id': event.id,
                    'redirect_url': f'/event/{event.id}/'
                })
            
            return redirect('event:event_detail', pk=event.id)
        else:
            # If AJAX request with errors
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
    else:
        form = EventForm()
    
    return render(request, 'event/add_event.html', {'form': form})


# ==================== AJAX VALIDATE EVENT FORM ====================
@login_required(login_url='Auth_Profile:login')
@require_http_methods(["POST"])
def ajax_validate_event_form(request):
    """
    Validate event form fields via AJAX
    """
    data = json.loads(request.body)
    form = EventForm(data)
    
    if form.is_valid():
        return JsonResponse({'success': True})
    else:
        return JsonResponse({
            'success': False,
            'errors': form.errors
        }, status=400)


# ==================== EDIT EVENT WITH AJAX ====================
@login_required(login_url='Auth_Profile:login')
def edit_event(request, pk):
    """
    Edit existing event with AJAX (Image 3)
    """
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    
    if request.method == 'POST':
        # Check if clear photo
        if request.POST.get('clear_photo') == 'true':
            event.photo.delete()
            event.photo = None
        
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            
            # If AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Event updated successfully!',
                    'event_id': event.id
                })
            
            return redirect('event:event_detail', pk=event.id)
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'errors': form.errors
                }, status=400)
    else:
        form = EventForm(instance=event)
    
    context = {
        'form': form,
        'event': event
    }
    
    return render(request, 'event/edit_event.html', context)


# ==================== DELETE EVENT WITH AJAX ====================
@login_required
@require_http_methods(["POST"])
def ajax_delete_event(request, pk):
    """
    Delete event via AJAX
    """
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    event.delete()
    
    return JsonResponse({
        'success': True,
        'message': 'Event deleted successfully!'
    })


# ==================== EVENT DETAIL ====================
def event_detail(request, pk):
    """
    Display event detail with join functionality (Image 4)
    """
    event = get_object_or_404(Event, pk=pk)
    schedules = event.schedules.filter(is_available=True, date__gte=datetime.now().date())
    
    user_registered = False
    if request.user.is_authenticated:
        user_registered = EventRegistration.objects.filter(
            event=event,
            user=request.user
        ).exists()
    
    context = {
        'event': event,
        'schedules': schedules,
        'user_registered': user_registered,
        'organizer': event.organizer,
        'activities': event.get_activities_list(),
    }
    
    return render(request, 'event/event_detail.html', context)


# ==================== AJAX JOIN EVENT ====================
@login_required(login_url='Auth_Profile:login')
@require_http_methods(["POST"])
def ajax_join_event(request, pk):
    """
    Join event via AJAX (from Image 4)
    """
    try:
        data = json.loads(request.body)
        event = get_object_or_404(Event, pk=pk)
        
        # Get date from request
        selected_date = data.get('date')
        if not selected_date:
            return JsonResponse({
                'success': False,
                'message': 'Please select a date'
            }, status=400)
        
        # Parse date
        date_obj = datetime.strptime(selected_date, '%m / %d / %Y').date()
        
        # Get or create schedule
        schedule, created = EventSchedule.objects.get_or_create(
            event=event,
            date=date_obj,
            defaults={'is_available': True}
        )
        
        # Check if already registered
        if EventRegistration.objects.filter(event=event, user=request.user, schedule=schedule).exists():
            return JsonResponse({
                'success': False,
                'message': 'You have already registered for this event on this date'
            }, status=400)
        
        # Create registration
        registration = EventRegistration.objects.create(
            event=event,
            user=request.user,
            schedule=schedule
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Successfully joined the event!',
            'registration_id': registration.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ==================== AJAX MARK AVAILABLE/UNAVAILABLE ====================
@login_required(login_url='Auth_Profile:login')
@require_http_methods(["POST"])
def ajax_toggle_availability(request, pk):
    """
    Toggle event availability (Mark Available/Unavailable buttons from Image 4)
    """
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    
    try:
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['available', 'unavailable']:
            return JsonResponse({
                'success': False,
                'message': 'Invalid status'
            }, status=400)
        
        event.status = new_status
        event.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Event marked as {new_status}',
            'status': event.status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


# ==================== AJAX GET EVENT SCHEDULES ====================
@require_http_methods(["GET"])
def ajax_get_schedules(request, pk):
    """
    Get available schedules for an event via AJAX
    """
    event = get_object_or_404(Event, pk=pk)
    schedules = event.schedules.filter(
        is_available=True, 
        date__gte=datetime.now().date()
    ).order_by('date')
    
    schedules_data = []
    for schedule in schedules:
        schedules_data.append({
            'id': schedule.id,
            'date': schedule.date.strftime('%m / %d / %Y'),
            'formatted_date': schedule.date.strftime('%A, %B %d, %Y')
        })
    
    return JsonResponse({
        'success': True,
        'schedules': schedules_data
    })


# ==================== AJAX FILTER BY SPORT ====================
@require_http_methods(["GET"])
def ajax_filter_sport(request):
    """
    Filter events by sport type via AJAX
    """
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
            'organizer': event.organizer.get_full_name() or event.organizer.username,
            'full_address': event.full_address,
            'is_organizer': request.user.is_authenticated and request.user == event.organizer,
        })
    
    return JsonResponse({
        'success': True,
        'events': events_data,
        'sport': sport
    })