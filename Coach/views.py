from django.shortcuts import render, redirect, get_object_or_404
from Coach.models import Coach
from django.http import HttpResponse, HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils.html import strip_tags
import re
import datetime as dt
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from decimal import Decimal
from django.core.exceptions import ValidationError

def _to_int(s):
    if not s:
        return None
    s = re.sub(r'[^\d]', '', s)
    return int(s) if s.isdigit() else None

def _parse_dt_local(s: str):
    """Terima 'YYYY-MM-DDTHH:MM' dari <input type='datetime-local'>"""
    if not s:
        return None
    dt_obj = parse_datetime(s)
    if dt_obj is None:
        try:
            dt_obj = dt.datetime.strptime(s, "%Y-%m-%dT%H:%M")
        except Exception:
            return None
    if timezone.is_naive(dt_obj):
        dt_obj = timezone.make_aware(dt_obj, timezone.get_current_timezone())
    return dt_obj

def _parse_time(s: str):
    """Parse 'HH:MM' dari <input type='time'>"""
    if not s:
        return None
    try:
        return dt.datetime.strptime(s, "%H:%M").time()
    except Exception:
        return None

def _to_decimal(s):
    """Convert string to Decimal for rating"""
    if not s:
        return Decimal('0')
    try:
        return Decimal(s)
    except:
        return Decimal('0')

def show_main(request):
    coach_list = Coach.objects.all()

    nama_coach = (request.GET.get('nama_coach') or '').strip()
    location = request.GET.get('location') or ''
    category = request.GET.get('category')
    min_p    = _to_int(request.GET.get('min_price'))
    max_p    = _to_int(request.GET.get('max_price'))
    sort     = request.GET.get('sort', 'date_asc')
    view_mode = request.GET.get('view', 'all')  

    # --- Filter by view mode ---
    if view_mode == 'my_bookings':
        coach_list = coach_list.filter(peserta=request.user)
    elif view_mode == 'my_coaches':
        coach_list = coach_list.filter(user=request.user)

    # --- filters ---
    if nama_coach:
        coach_list = coach_list.filter(user__nama__icontains=nama_coach)

    if location:
        coach_list = coach_list.filter(location__icontains=location)

    if category:
        coach_list = coach_list.filter(category=category)
    if min_p is not None:
        coach_list = coach_list.filter(price__gte=min_p)
    if max_p is not None:
        coach_list = coach_list.filter(price__lte=max_p)

    available_only = request.GET.get('available') in ['1', 'on', 'true', 'True']
    if available_only:
        today = timezone.now().date()
        coach_list = coach_list.filter(isBooked=False, date__gte=today)

    # --- sorting ---
    if sort == 'price_asc':
        coach_list = coach_list.order_by('price')
    elif sort == 'price_desc':
        coach_list = coach_list.order_by('-price')
    elif sort == 'date_desc':
        coach_list = coach_list.order_by('-date')
    else:  
        coach_list = coach_list.order_by('date')

    context = {
        'coach_list': coach_list, 
        'count': coach_list.count(),
        'nama_coach': nama_coach,
        'view_mode': view_mode, 
    }
    return render(request, 'main.html', context)

def coach_detail(request, pk):
    coach = get_object_or_404(Coach, pk=pk)
    return render(request, "coach_detail.html", {'coach': coach})

@login_required(login_url='/login')
def create_coach_page(request):
    return render(request, 'create_coach.html')

@login_required(login_url='/login')
def add_coach(request):
    if request.method != 'POST':
        return HttpResponse(status=405)

    # price
    price = _to_int(request.POST.get("price"))
    if price is None or price < 0:
        return HttpResponse(b"INVALID PRICE", status=400)

    # date
    date_str = request.POST.get("date")
    event_dt = _parse_dt_local(date_str)
    if event_dt is None:
        return HttpResponse(b"INVALID DATE", status=400)
    
    # startTime & endTime
    start_time = _parse_time(request.POST.get("startTime"))
    end_time = _parse_time(request.POST.get("endTime"))
    
    if not start_time or not end_time:
        return HttpResponse(b"INVALID TIME", status=400)
    
    if end_time <= start_time:
        return HttpResponse(b"END TIME MUST BE AFTER START TIME", status=400)

    # rating
    rating = _to_decimal(request.POST.get("rating"))
    if rating < 0 or rating > 5:
        return HttpResponse(b"RATING MUST BE BETWEEN 0 AND 5", status=400)

    new_coach = Coach(
        title=strip_tags(request.POST.get("title")),
        description=strip_tags(request.POST.get("description")),
        category=request.POST.get("category"),
        location=strip_tags(request.POST.get("location")),
        address=strip_tags(request.POST.get("address")),
        image=request.FILES.get("image"),
        user=request.user,
        price=price,
        date=event_dt.date(),
        startTime=start_time,
        endTime=end_time,
        rating=rating,
        instagram_link=request.POST.get("instagram_link") or None,
        mapsLink=request.POST.get("mapsLink") or "",  # NEW
    )
    new_coach.save()
    return redirect('coach:show_main')

def edit_coach_page(request, pk):
    coach = get_object_or_404(Coach, pk=pk)
    if coach.user_id != request.user.id:
        return HttpResponseForbidden(b"FORBIDDEN: not the owner")
    return render(request, "edit_coach.html", {"coach": coach})

@login_required(login_url='/login')
def update_coach(request, pk):
    if request.method != 'POST':
        return HttpResponse(status=405)

    coach = get_object_or_404(Coach, pk=pk)
    if coach.user_id != request.user.id:
        return HttpResponse(b"FORBIDDEN", status=403)

    # price
    price = _to_int(request.POST.get("price"))
    if price is not None and price >= 0:
        coach.price = price

    # fields text
    coach.title = strip_tags(request.POST.get("title", coach.title))
    coach.description = strip_tags(request.POST.get("description", coach.description))
    coach.category = request.POST.get("category", coach.category) or coach.category
    coach.location = strip_tags(request.POST.get("location", coach.location))
    coach.address = strip_tags(request.POST.get("address", coach.address))

    # date
    date_str = request.POST.get("date")
    event_dt = _parse_dt_local(date_str)
    if event_dt:
        coach.date = event_dt.date()
    
    # time
    start_time = _parse_time(request.POST.get("startTime"))
    end_time = _parse_time(request.POST.get("endTime"))
    if start_time:
        coach.startTime = start_time
    if end_time:
        coach.endTime = end_time

    # rating
    rating_str = request.POST.get("rating")
    if rating_str:
        coach.rating = _to_decimal(rating_str)
    
    # instagram_link
    instagram = request.POST.get("instagram_link")
    if instagram:
        coach.instagram_link = instagram
    
    # mapsLink 
    maps_link = request.POST.get("mapsLink")
    if maps_link:
        coach.mapsLink = maps_link

    # image
    image = request.FILES.get("image")
    if image:
        coach.image = image

    coach.save()
    return redirect("coach:coach_detail", pk=coach.pk)

@login_required(login_url='/login')
def book_coach(request, pk):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    coach = get_object_or_404(Coach, pk=pk)
    
    if coach.user == request.user:
        return HttpResponse(b"Cannot book your own coach", status=400)
    
    if coach.isBooked:
        return HttpResponse(b"Coach already booked", status=400)
    
    try:
        coach.peserta = request.user
        coach.isBooked = True
        coach.save()
        return redirect('coach:coach_detail', pk=pk)
    except ValidationError as e:
        return HttpResponse(str(e).encode(), status=400)

@login_required(login_url='/login')
def cancel_booking(request, pk):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    coach = get_object_or_404(Coach, pk=pk)
    
    if coach.peserta != request.user:
        return HttpResponse(b"FORBIDDEN", status=403)
    
    coach.peserta = None
    coach.isBooked = False
    coach.save()
    return redirect('coach:coach_detail', pk=pk)