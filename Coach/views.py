from django.shortcuts import render, redirect, get_object_or_404
from Coach.models import Coach
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.utils.html import strip_tags
from functools import wraps
import re
import datetime as dt
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.views.decorators.http import require_http_methods
import json
from PIL import Image
import os

# ==================== CUSTOM LOGIN DECORATOR ====================
def custom_login_required(view_func):
    """Custom decorator that checks session instead of Django auth"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if 'user_id' not in request.session:
            # AJAX request
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Please login first',
                    'redirect_url': '/login/'
                }, status=401)
            # Normal request
            return redirect('/login/')
        
        # Set request.user from session
        try:
            from Auth_Profile.models import User
            request.user = User.objects.get(id=request.session['user_id'])
        except User.DoesNotExist:
            request.session.flush()
            return redirect('/login/')
        
        return view_func(request, *args, **kwargs)
    return wrapper

# ==================== HELPER FUNCTIONS ====================
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

def validate_image(file):
    """Validate uploaded image"""
    if not file:
        return None
    
    # Check file size (max 5MB)
    if file.size > 5 * 1024 * 1024:
        raise ValidationError('Image size must be less than 5MB')
    
    # Check file extension
    ext = os.path.splitext(file.name)[1].lower()
    valid_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    if ext not in valid_extensions:
        raise ValidationError(f'Invalid file type. Allowed: {", ".join(valid_extensions)}')
    
    # Verify it's actually an image
    try:
        img = Image.open(file)
        img.verify()
    except Exception:
        raise ValidationError('Invalid image file')
    
    return file

# ==================== VIEWS ====================
def show_main(request):
    coach_list = Coach.objects.all()

    # Set request.user from session if logged in - FIXED
    if 'user_id' in request.session:
        try:
            from Auth_Profile.models import User
            request.user = User.objects.get(id=request.session['user_id'])
        except User.DoesNotExist:
            request.session.flush()
            request.user = None
    else:
        request.user = None

    nama_coach = (request.GET.get('nama_coach') or '').strip()
    location = request.GET.get('location') or ''
    category = request.GET.get('category')
    min_p    = _to_int(request.GET.get('min_price'))
    max_p    = _to_int(request.GET.get('max_price'))
    sort     = request.GET.get('sort', 'date_asc')
    view_mode = request.GET.get('view', 'all')  

    # --- Filter by view mode ---
    if view_mode == 'my_bookings' and request.user:
        coach_list = coach_list.filter(peserta=request.user)
    elif view_mode == 'my_coaches' and request.user:
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
        'user': request.user,  # ADDED: explicitly pass user to template
    }
    return render(request, 'main.html', context)

def coach_detail(request, pk):
    # Set request.user from session if logged in - FIXED
    if 'user_id' in request.session:
        try:
            from Auth_Profile.models import User
            request.user = User.objects.get(id=request.session['user_id'])
        except User.DoesNotExist:
            request.session.flush()
            request.user = None
    else:
        request.user = None
    
    coach = get_object_or_404(Coach, pk=pk)
    
    context = {
        'coach': coach,
        'user': request.user,  # ADDED: Pass user explicitly to template
    }
    
    return render(request, "coach_detail.html", context)

@custom_login_required
def create_coach_page(request):
    return render(request, 'create_coach.html')

@custom_login_required
@require_http_methods(["POST"])
def add_coach(request):
    try:
        # price
        price = _to_int(request.POST.get("price"))
        if price is None or price < 0:
            return JsonResponse({'success': False, 'message': 'Invalid price'}, status=400)

        # date
        date_str = request.POST.get("date")
        event_dt = _parse_dt_local(date_str)
        if event_dt is None:
            return JsonResponse({'success': False, 'message': 'Invalid date'}, status=400)
        
        # startTime & endTime
        start_time = _parse_time(request.POST.get("startTime"))
        end_time = _parse_time(request.POST.get("endTime"))
        
        if not start_time or not end_time:
            return JsonResponse({'success': False, 'message': 'Invalid time'}, status=400)
        
        if end_time <= start_time:
            return JsonResponse({'success': False, 'message': 'End time must be after start time'}, status=400)

        # rating
        rating = _to_decimal(request.POST.get("rating"))
        if rating < 0 or rating > 5:
            return JsonResponse({'success': False, 'message': 'Rating must be between 0 and 5'}, status=400)

        # Validate image
        image = request.FILES.get("image")
        if image:
            try:
                image = validate_image(image)
            except ValidationError as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=400)

        new_coach = Coach(
            title=strip_tags(request.POST.get("title")),
            description=strip_tags(request.POST.get("description")),
            category=request.POST.get("category"),
            location=strip_tags(request.POST.get("location")),
            address=strip_tags(request.POST.get("address")),
            image=image,
            user=request.user,
            price=price,
            date=event_dt.date(),
            startTime=start_time,
            endTime=end_time,
            rating=rating,
            instagram_link=request.POST.get("instagram_link") or None,
            mapsLink=request.POST.get("mapsLink") or "",
        )
        new_coach.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Coach created successfully!',
            'coach_id': str(new_coach.pk),
            'redirect_url': f'/coach/{new_coach.pk}/'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@custom_login_required
def edit_coach_page(request, pk):
    coach = get_object_or_404(Coach, pk=pk)
    if coach.user_id != request.user.id:
        return HttpResponseForbidden(b"FORBIDDEN: not the owner")
    return render(request, "edit_coach.html", {"coach": coach})

@custom_login_required
@require_http_methods(["POST"])
def update_coach(request, pk):
    try:
        coach = get_object_or_404(Coach, pk=pk)
        if coach.user_id != request.user.id:
            return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)

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
        
        return JsonResponse({
            'success': True,
            'message': 'Coach updated successfully!',
            'redirect_url': f'/coach/{coach.pk}/'
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@custom_login_required
@require_http_methods(["POST"])
def book_coach(request, pk):
    coach = get_object_or_404(Coach, pk=pk)
    
    if coach.user == request.user:
        return JsonResponse({'success': False, 'message': 'Cannot book your own coach'}, status=400)
    
    if coach.isBooked:
        return JsonResponse({'success': False, 'message': 'Coach already booked'}, status=400)
    
    try:
        coach.peserta = request.user
        coach.isBooked = True
        coach.save()
        return JsonResponse({
            'success': True,
            'message': 'Booking successful!',
            'coach': {
                'isBooked': True,
                'peserta_name': request.user.nama
            }
        })
    except ValidationError as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)

@custom_login_required
@require_http_methods(["POST"])
def cancel_booking(request, pk):
    coach = get_object_or_404(Coach, pk=pk)
    
    if coach.peserta != request.user:
        return JsonResponse({'success': False, 'message': 'Forbidden'}, status=403)
    
    try:
        coach.peserta = None
        coach.isBooked = False
        coach.save()
        return JsonResponse({
            'success': True,
            'message': 'Booking cancelled successfully',
            'coach': {'isBooked': False}
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'Error: {str(e)}'}, status=500)

@custom_login_required
@require_http_methods(["POST"])
def mark_available(request, pk):
    """Mark coach as available"""
    try:
        coach = get_object_or_404(Coach, pk=pk)
        
        # Check if user is the owner
        if coach.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'You do not have permission to modify this coach'
            }, status=403)
        
        # Mark as available
        coach.isBooked = False
        coach.peserta = None
        coach.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Coach marked as available'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@custom_login_required
@require_http_methods(["POST"])
def mark_unavailable(request, pk):
    """Mark coach as unavailable"""
    try:
        coach = get_object_or_404(Coach, pk=pk)
        
        # Check if user is the owner
        if coach.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'You do not have permission to modify this coach'
            }, status=403)
        
        # Mark as unavailable
        coach.isBooked = True
        coach.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Coach marked as unavailable'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@custom_login_required
@require_http_methods(["POST"])
def delete_coach(request, pk):
    """Delete coach"""
    try:
        coach = get_object_or_404(Coach, pk=pk)
        
        # Check if user is the owner
        if coach.user != request.user:
            return JsonResponse({
                'success': False,
                'message': 'You do not have permission to delete this coach'
            }, status=403)
        
        # Delete the coach
        coach.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Coach deleted successfully'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)