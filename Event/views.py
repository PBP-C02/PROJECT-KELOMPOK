from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.utils import timezone
from .models import Event, EventRegistration, EventOrganizer, EventReview
from .forms import EventSearchForm, EventRegistrationForm, EventReviewForm


def event_list(request):
    """Halaman listing event dengan search & filter"""
    events = Event.objects.filter(is_active=True, date__gte=timezone.now().date())
    
    # Ambil parameter filter
    search_query = request.GET.get('search', '')
    city_filter = request.GET.get('city', '')
    category_filter = request.GET.get('category', '')
    level_filter = request.GET.get('level', '')
    sort_by = request.GET.get('sort', 'date')  # date, price, participants
    
    # Apply filters
    if search_query:
        events = events.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location_name__icontains=search_query)
        )
    
    if city_filter:
        events = events.filter(city__iexact=city_filter)
    
    if category_filter:
        events = events.filter(category=category_filter)
    
    if level_filter:
        events = events.filter(level=level_filter)
    
    # Sorting
    if sort_by == 'date':
        events = events.order_by('date', 'time')
    elif sort_by == 'price_low':
        events = events.order_by('price')
    elif sort_by == 'price_high':
        events = events.order_by('-price')
    elif sort_by == 'participants':
        events = events.annotate(
            participant_count=Count('registrations', filter=Q(registrations__status='confirmed'))
        ).order_by('-participant_count')
    
    # Ambil unique cities dan categories untuk filter dropdowns
    cities = Event.objects.filter(is_active=True).values_list('city', flat=True).distinct()
    categories = Event.CATEGORY_CHOICES
    levels = Event.LEVEL_CHOICES
    
    context = {
        'events': events,
        'total_events': events.count(),
        'cities': cities,
        'categories': categories,
        'levels': levels,
        'search_query': search_query,
        'city_filter': city_filter,
        'category_filter': category_filter,
        'level_filter': level_filter,
        'sort_by': sort_by,
    }
    
    return render(request, 'Event/event_list.html', context)


def event_detail(request, event_id):
    """Halaman detail event"""
    event = get_object_or_404(Event, id=event_id, is_active=True)
    
    # Ambil peserta yang sudah dikonfirmasi
    confirmed_registrations = event.registrations.filter(status='confirmed').select_related('user')
    participants = [reg.user for reg in confirmed_registrations]
    
    # Ambil semua reviews
    reviews = event.reviews.all().select_related('user')
    
    # Cek apakah user sudah daftar
    user_registration = None
    if request.user.is_authenticated:
        user_registration = event.registrations.filter(user=request.user).first()
    
    # Ambil event yang direkomendasikan (kategori sama atau kota sama)
    recommended_events = Event.objects.filter(
        is_active=True,
        date__gte=timezone.now().date()
    ).filter(
        Q(category=event.category) | Q(city=event.city)
    ).exclude(id=event.id)[:3]
    
    context = {
        'event': event,
        'participants': participants,
        'reviews': reviews,
        'user_registration': user_registration,
        'recommended_events': recommended_events,
    }
    
    return render(request, 'Event/event_detail.html', context)


@login_required
def event_register(request, event_id):
    """Handle pendaftaran event"""
    event = get_object_or_404(Event, id=event_id, is_active=True)
    
    # Cek apakah event sudah penuh
    if event.is_full:
        messages.error(request, 'Maaf, event ini sudah penuh!')
        return redirect('Event:event_detail', event_id=event.id)
    
    # Cek apakah user sudah daftar sebelumnya
    existing_registration = EventRegistration.objects.filter(
        event=event,
        user=request.user
    ).first()
    
    if existing_registration:
        messages.warning(request, 'Kamu sudah terdaftar untuk event ini!')
        return redirect('Event:event_detail', event_id=event.id)
    
    if request.method == 'POST':
        form = EventRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            registration = form.save(commit=False)
            registration.event = event
            registration.user = request.user
            registration.status = 'pending'
            registration.save()
            
            messages.success(
                request, 
                'Permintaan gabung berhasil dikirim! Tunggu konfirmasi dari penyelenggara.'
            )
            return redirect('Event:event_detail', event_id=event.id)
    else:
        form = EventRegistrationForm()
    
    context = {
        'event': event,
        'form': form,
    }
    
    return render(request, 'Event/event_register.html', context)


@login_required
def event_cancel_registration(request, registration_id):
    """Batalkan pendaftaran"""
    registration = get_object_or_404(
        EventRegistration, 
        id=registration_id, 
        user=request.user
    )
    
    event = registration.event
    
    if request.method == 'POST':
        registration.status = 'cancelled'
        registration.save()
        
        messages.success(request, 'Registrasi berhasil dibatalkan.')
        return redirect('Event:event_detail', event_id=event.id)
    
    context = {
        'registration': registration,
        'event': event,
    }
    
    return render(request, 'Event/event_cancel_registration.html', context)


@login_required
def event_add_review(request, event_id):
    """Tambah review untuk event"""
    event = get_object_or_404(Event, id=event_id)
    
    # Cek apakah user pernah ikut event ini (punya registration confirmed dan event sudah lewat)
    registration = EventRegistration.objects.filter(
        event=event,
        user=request.user,
        status='confirmed'
    ).first()
    
    if not registration or not event.is_past:
        messages.error(request, 'Kamu hanya bisa review event yang sudah kamu ikuti!')
        return redirect('Event:event_detail', event_id=event.id)
    
    # Cek apakah sudah pernah review
    existing_review = EventReview.objects.filter(event=event, user=request.user).first()
    if existing_review:
        messages.warning(request, 'Kamu sudah memberikan review untuk event ini!')
        return redirect('Event:event_detail', event_id=event.id)
    
    if request.method == 'POST':
        form = EventReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.event = event
            review.user = request.user
            review.save()
            
            messages.success(request, 'Review berhasil ditambahkan!')
            return redirect('Event:event_detail', event_id=event.id)
    else:
        form = EventReviewForm()
    
    context = {
        'event': event,
        'form': form,
    }
    
    return render(request, 'Event/event_add_review.html', context)


@login_required
def my_events(request):
    """Halaman event yang diikuti user"""
    # Event yang akan datang
    upcoming_registrations = EventRegistration.objects.filter(
        user=request.user,
        event__date__gte=timezone.now().date(),
        status__in=['pending', 'confirmed']
    ).select_related('event').order_by('event__date', 'event__time')
    
    # Event yang sudah lewat
    past_registrations = EventRegistration.objects.filter(
        user=request.user,
        event__date__lt=timezone.now().date()
    ).select_related('event').order_by('-event__date', '-event__time')
    
    context = {
        'upcoming_registrations': upcoming_registrations,
        'past_registrations': past_registrations,
    }
    
    return render(request, 'Event/my_events.html', context)

@login_required
def create_event(request):
    """Create event baru"""
    # Cek apakah user punya organizer profile
    try:
        organizer = request.user.organizer_profile
    except EventOrganizer.DoesNotExist:
        messages.error(request, 'Kamu harus jadi organizer dulu!')
        return redirect('Event:event_list')
    
    if request.method == 'POST':
        # Ambil data dari form
        try:
            event = Event.objects.create(
                name=request.POST.get('name'),
                description=request.POST.get('description'),
                category=request.POST.get('category'),
                level=request.POST.get('level'),
                date=request.POST.get('date'),
                time=request.POST.get('time'),
                duration_hours=request.POST.get('duration_hours', 2.0),
                location_name=request.POST.get('location_name'),
                location_address=request.POST.get('location_address'),
                city=request.POST.get('city'),
                price=request.POST.get('price'),
                max_participants=request.POST.get('max_participants'),
                min_participants=request.POST.get('min_participants', 2),
                organizer=organizer,
                requirements=request.POST.get('requirements', ''),
                payment_info=request.POST.get('payment_info', ''),
                instagram_link=request.POST.get('instagram_link', ''),
                image=request.FILES.get('image')
            )
            
            messages.success(request, f'Event "{event.name}" berhasil dibuat!')
            return redirect('Event:event_detail', event_id=event.id)
            
        except Exception as e:
            messages.error(request, f'Gagal membuat event: {str(e)}')
    
    # GET request - tampilkan form
    context = {
        'categories': Event.CATEGORY_CHOICES,
        'levels': Event.LEVEL_CHOICES,
    }
    
    return render(request, 'Event/create_event.html', context)