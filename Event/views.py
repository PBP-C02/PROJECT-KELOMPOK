from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event, EventRegistration
from .forms import EventForm

def event_list(request):
    events = Event.objects.all().order_by('date', 'time')
    
    # Filter by category
    category = request.GET.get('category')
    if category:
        events = events.filter(category=category)
    
    # Ambil semua kategori untuk filter dropdown
    categories = Event.CATEGORY_CHOICES
    
    context = {
        'events': events,
        'categories': categories,
        'selected_category': category,
    }
    return render(request, 'event/event_list.html', context)

def event_detail(request, pk):
    event = get_object_or_404(Event, pk=pk)
    is_registered = False
    
    if request.user.is_authenticated:
        is_registered = EventRegistration.objects.filter(
            event=event, 
            user=request.user
        ).exists()
    
    participants = event.registrations.select_related('user').all()
    
    context = {
        'event': event,
        'is_registered': is_registered,
        'participants': participants,
        'participants_count': participants.count(),
        'available_slots': event.available_slots(),
    }
    return render(request, 'event/event_detail.html', context)

@login_required
def create_event(request):
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)
        if form.is_valid():
            event = form.save(commit=False)
            event.organizer = request.user
            event.save()
            messages.success(request, 'Event created successfully!')
            return redirect('event:event_detail', pk=event.pk)
    else:
        form = EventForm()
    
    return render(request, 'event/create_event.html', {'form': form})

@login_required
def edit_event(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)
        if form.is_valid():
            form.save()
            messages.success(request, 'Event updated successfully!')
            return redirect('event:event_detail', pk=event.pk)
    else:
        form = EventForm(instance=event)
    
    return render(request, 'event/edit_event.html', {'form': form, 'event': event})

@login_required
def delete_event(request, pk):
    event = get_object_or_404(Event, pk=pk, organizer=request.user)
    
    if request.method == 'POST':
        event.delete()
        messages.success(request, 'Event deleted successfully!')
        return redirect('event:event_list')
    
    return render(request, 'event/delete_event.html', {'event': event})

@login_required
def register_event(request, pk):
    event = get_object_or_404(Event, pk=pk)
    
    # Cek apakah event sudah penuh
    if event.is_full():
        messages.error(request, 'Sorry, this event is already full!')
        return redirect('event:event_detail', pk=pk)
    
    # Cek apakah user sudah terdaftar
    if EventRegistration.objects.filter(event=event, user=request.user).exists():
        messages.warning(request, 'You are already registered for this event!')
        return redirect('event:event_detail', pk=pk)
    
    # Daftar ke event
    EventRegistration.objects.create(event=event, user=request.user)
    messages.success(request, 'Successfully registered for the event!')
    return redirect('event:event_detail', pk=pk)

@login_required
def cancel_registration(request, pk):
    event = get_object_or_404(Event, pk=pk)
    registration = EventRegistration.objects.filter(event=event, user=request.user)
    
    if registration.exists():
        registration.delete()
        messages.success(request, 'Registration cancelled successfully!')
    else:
        messages.error(request, 'You are not registered for this event!')
    
    return redirect('event:event_detail', pk=pk)