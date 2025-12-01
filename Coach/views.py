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
from django.views.decorators.csrf import csrf_exempt
import json
from PIL import Image
import os
from django.db.models import Q
from Auth_Profile.models import User
import requests

# ==================== CUSTOM LOGIN DECORATOR ====================
def custom_login_required(view_func):
    """Custom decorator that checks session instead of Django auth"""
    @wraps(view_func)
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

def _get_current_user(request):
    """Return authenticated user from session-managed Auth_Profile.User."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None

    try:
        return User.objects.get(id=user_id)
    except User.DoesNotExist:
        return None

def _require_user(request, *, json_mode=False):
    """
    Ensure request has authenticated user.
    Returns tuple (user, error_response). If user is None, error_response contains redirect/JSON response.
    """
    user = _get_current_user(request)
    if user:
        return user, None

    if json_mode:
        return None, JsonResponse({'success': False, 'error': 'Authentication required'}, status=401)
    return None, redirect('/login/')

# ==================== VIEWS ====================
def show_main(request):
    current_user, error_response = _require_user(request)
    if error_response:
        return error_response
    return render(request, 'coach/main.html', {'user': current_user})

def coach_detail(request, pk):
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
        'user': request.user, 
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

@csrf_exempt
@require_http_methods(["GET"])
def ajax_search_coaches(request):
    """AJAX endpoint for searching and filtering coaches"""
    try:
        from Auth_Profile.models import User
        if 'user_id' in request.session:
            request.user = User.objects.get(id=request.session['user_id'])
        else:
            request.user = None
    except User.DoesNotExist:
        request.user = None

    # Get filter parameters
    search_query = request.GET.get('q', '').strip()
    location = request.GET.get('location', '')
    category = request.GET.get('category', '')
    min_price = _to_int(request.GET.get('min_price'))
    max_price = _to_int(request.GET.get('max_price'))
    available_only = request.GET.get('available', 'false') == 'true'
    view_mode = request.GET.get('view', 'all')
    sort_by = request.GET.get('sort', 'date_asc')

    # Start with all coaches
    coaches = Coach.objects.all()

    # View mode filters
    if view_mode == 'my_bookings' and request.user:
        coaches = coaches.filter(peserta=request.user)
    elif view_mode == 'my_coaches' and request.user:
        coaches = coaches.filter(user=request.user)

    # Search filter (search in title, description, location, and coach name)
    if search_query:
        coaches = coaches.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(user__nama__icontains=search_query)
        )

    # Location filter
    if location:
        coaches = coaches.filter(location__icontains=location)

    # Category filter
    if category:
        coaches = coaches.filter(category=category)

    # Price range filter
    if min_price is not None:
        coaches = coaches.filter(price__gte=min_price)
    if max_price is not None:
        coaches = coaches.filter(price__lte=max_price)

    # Available only filter
    if available_only:
        today = timezone.now().date()
        coaches = coaches.filter(isBooked=False, date__gte=today)

    # Sorting
    sort_map = {
        'date_asc': ['date', 'startTime'],
        'date_desc': ['-date', '-startTime'],
        'price_asc': 'price',
        'price_desc': '-price',
    }
    order_by = sort_map.get(sort_by, ['date', 'startTime'])
    if isinstance(order_by, list):
        coaches = coaches.order_by(*order_by)
    else:
        coaches = coaches.order_by(order_by)

    # Serialize coaches data
    coaches_data = []
    for coach in coaches:
        coaches_data.append({
            'id': str(coach.pk),
            'title': coach.title,
            'description': coach.description,
            'category': coach.category,
            'category_display': coach.get_category_display(),
            'location': coach.location,
            'address': coach.address,
            'price': coach.price,
            'price_formatted': coach.price_formatted,
            'date': coach.date.strftime('%Y-%m-%d'),
            'date_formatted': coach.date.strftime('%d %b %Y'),
            'start_time': coach.startTime.strftime('%H:%M'),
            'end_time': coach.endTime.strftime('%H:%M'),
            'rating': float(coach.rating),
            'is_booked': coach.isBooked,
            'image_url': request.build_absolute_uri(coach.image.url) if coach.image else None, 
            'user_name': coach.user.nama,
            'user_id': str(coach.user.id),
            'is_owner': request.user and str(request.user.id) == str(coach.user.id),
            'detail_url': f'/coach/{coach.pk}/',
            'edit_url': f'/coach/edit-coach/{coach.pk}/',
        })

    return JsonResponse({
        'success': True,
        'coaches': coaches_data,
        'count': len(coaches_data)
    })


def proxy_image(request):
    image_url = request.GET.get('url')
    if not image_url:
        return HttpResponse('No URL provided', status=400)
    
    try:
        # Add headers to mimic browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        # Fetch image from external source
        response = requests.get(image_url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Return the image with proper content type
        return HttpResponse(
            response.content,
            content_type=response.headers.get('Content-Type', 'image/jpeg')
        )
    except requests.RequestException as e:
        # Return proper error instead of HTML
        return HttpResponse(status=404)  # Return 404 instead of 500 with HTML
    
@csrf_exempt
def create_coach_flutter(request):
    # Cek login
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Silakan login terlebih dahulu'}, status=401)
    if request.method == 'POST':
        data = json.loads(request.body)

        title = strip_tags(data.get("title", ""))
        description = strip_tags(data.get("description", ""))
        category = data.get("category", "")
        location = strip_tags(data.get("location", ""))
        address = strip_tags(data.get("address", ""))
        price = int(data.get("price", 0))
        date_str = data.get("date", "")
        start_time_str = data.get("startTime", "")
        end_time_str = data.get("endTime", "")
        rating = data.get("rating", 0)
        instagram_link = data.get("instagram_link", "")
        mapsLink = data.get("mapsLink", "")
        user = request.user
        
        # Parse date and time
        event_dt = _parse_dt_local(date_str)
        start_time = _parse_time(start_time_str)
        end_time = _parse_time(end_time_str)
        
        new_coach = Coach(
            title=title, 
            description=description,
            category=category,
            location=location,
            address=address,
            price=price,
            date=event_dt.date() if event_dt else None,
            startTime=start_time,
            endTime=end_time,
            rating=_to_decimal(rating),
            instagram_link=instagram_link if instagram_link else None,
            mapsLink=mapsLink,
            user=user
        )
        new_coach.save()
        
        return JsonResponse({"status": "success"}, status=200)
    else:
        return JsonResponse({"status": "error"}, status=401)
    
@csrf_exempt
def show_json(request):
    coach_list = Coach.objects.all()
    data = [
        {
            'id': str(coach.coach_id),
            'title': coach.title,
            'description': coach.description,
            'category': coach.category,
            'location': coach.location,
            'address': coach.address,
            'price': coach.price,
            'date': coach.date.strftime('%Y-%m-%d'),
            'startTime': coach.startTime.strftime('%H:%M'),
            'endTime': coach.endTime.strftime('%H:%M'),
            'rating': float(coach.rating),
            'isBooked': coach.isBooked,
            'user_id': str(coach.user_id),
            'user_name': coach.user.nama,
            'image_url': request.build_absolute_uri(coach.image.url) if coach.image else None, 
            'instagram_link': coach.instagram_link,
            'mapsLink': coach.mapsLink,
        }
        for coach in coach_list
    ]

    return JsonResponse(data, safe=False)
