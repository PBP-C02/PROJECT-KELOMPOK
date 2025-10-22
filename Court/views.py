from decimal import Decimal, InvalidOperation
from datetime import datetime, time
import json

from urllib.parse import parse_qs, unquote, urlparse

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from Auth_Profile.models import User as ProfileUser

from .models import Court, TimeSlot


def clean_decimal(value, default=None, min_value=None, max_value=None):
    """
    Convert arbitrary input into Decimal while keeping invalid values safe.
    Returns ``default`` (which can be None) when parsing fails.
    """
    if value in (None, "", "null"):
        return default

    try:
        number = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return default

    if min_value is not None and number < min_value:
        return min_value
    if max_value is not None and number > max_value:
        return max_value

    return number


def sanitize_coordinate(value, coordinate_type):
    """
    Only accept latitude/longitude inside realistic bounds.
    Invalid input returns None so it won't be persisted.
    """
    limits = {
        "latitude": (Decimal("-90"), Decimal("90")),
        "longitude": (Decimal("-180"), Decimal("180")),
    }

    if value in (None, "", "null"):
        return None

    try:
        coordinate = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        return None

    limits_pair = limits.get(coordinate_type)
    if not limits_pair:
        return None

    min_limit, max_limit = limits_pair
    if coordinate < min_limit or coordinate > max_limit:
        return None

    return coordinate


def parse_maps_link(link):
    """
    Attempt to extract latitude and longitude from a Google Maps share URL.
    Returns tuple (lat, lng) as strings when successful.
    """
    if not link:
        return None, None

    try:
        parsed = urlparse(link)
        query_params = parse_qs(parsed.query)

        # Pattern: https://maps.google.com/?q=-6.2,106.8 or ll=...
        for key in ('q', 'query', 'll'):
            if key in query_params:
                candidate = query_params[key][0]
                parts = candidate.split(',')
                if len(parts) >= 2:
                    return parts[0].strip(), parts[1].strip()

        # Path pattern containing @lat,lng,zoom
        path = unquote(parsed.path or '')
        if '@' in path:
            after_at = path.split('@', 1)[1]
            parts = after_at.split(',')
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].strip()

        # Handle shortened maps links with !3d lat !4d lng in fragment/query
        fragment = unquote(parsed.fragment or '')
        for container in (path, fragment):
            if '!3d' in container and '!4d' in container:
                try:
                    lat = container.split('!3d', 1)[1].split('!', 1)[0]
                    lng = container.split('!4d', 1)[1].split('!', 1)[0]
                    return lat.strip(), lng.strip()
                except (IndexError, ValueError):
                    continue
    except Exception:
        return None, None

    return None, None


def _get_current_user(request):
    """Return authenticated user from session-managed Auth_Profile.User."""
    user_id = request.session.get('user_id')
    if not user_id:
        return None

    try:
        return ProfileUser.objects.get(id=user_id)
    except ProfileUser.DoesNotExist:
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


def _get_user_name(user):
    if not user:
        return ''
    name = getattr(user, 'nama', None)
    if name:
        return name
    full_name = getattr(user, 'get_full_name', None)
    if callable(full_name):
        value = full_name()
        if value:
            return value
    return getattr(user, 'username', getattr(user, 'email', ''))


def _get_user_phone(user):
    if not user:
        return ''
    return getattr(user, 'nomor_handphone', '')

def add_court(request):
    """
    Form untuk menambahkan court secara manual (via halaman web).
    Hanya user yang sudah login.
    """
    current_user, error_response = _require_user(request)
    if error_response:
        return error_response

    if request.method == 'POST':
        name = request.POST.get('name')
        sport_type = request.POST.get('sport_type')
        location = request.POST.get('location')
        address = request.POST.get('address')
        price_per_hour = clean_decimal(
            request.POST.get('price_per_hour'),
            default=Decimal("0"),
            min_value=Decimal("0"),
        )
        facilities = request.POST.get('facilities') or ""
        rating = clean_decimal(
            request.POST.get('rating'),
            default=Decimal("0"),
            min_value=Decimal("0"),
            max_value=Decimal("5"),
        )
        description = request.POST.get('description')
        owner_name = _get_user_name(current_user)
        owner_phone = _get_user_phone(current_user)
        maps_link = request.POST.get('maps_link')
        link_lat, link_lng = parse_maps_link(maps_link)
        latitude = sanitize_coordinate(link_lat, "latitude") if link_lat else None
        longitude = sanitize_coordinate(link_lng, "longitude") if link_lng else None

        image = request.FILES.get('image')

        Court.objects.create(
            name=name,
            sport_type=sport_type,
            location=location,
            address=address,
            price_per_hour=price_per_hour,
            facilities=facilities,
            rating=rating,
            description=description,
            owner_name=owner_name,
            owner_phone=owner_phone,
            latitude=latitude,
            longitude=longitude,
            image=image,
            created_by=current_user,
        )
        return redirect('Court:show_main')

    return render(request, 'add_court.html', {'user': current_user})

@csrf_exempt
def api_add_court(request):
    """API untuk menambah lapangan via AJAX."""
    if request.method == "POST":
        try:
            current_user, error_response = _require_user(request, json_mode=True)
            if error_response:
                return error_response
            data = request.POST
            image = request.FILES.get('image')
            price_per_hour = clean_decimal(
                data.get('price_per_hour'),
                default=Decimal("0"),
                min_value=Decimal("0"),
            )
            rating = clean_decimal(
                data.get('rating'),
                default=Decimal("0"),
                min_value=Decimal("0"),
                max_value=Decimal("5"),
            )
            maps_link = data.get('maps_link')
            link_lat, link_lng = parse_maps_link(maps_link)
            latitude = sanitize_coordinate(link_lat, "latitude") if link_lat else None
            longitude = sanitize_coordinate(link_lng, "longitude") if link_lng else None

            Court.objects.create(
                name=data.get('name'),
                sport_type=data.get('sport_type'),
                location=data.get('location'),
                address=data.get('address'),
                price_per_hour=price_per_hour,
                facilities=data.get('facilities') or "",
                rating=rating,
                description=data.get('description'),
                owner_name=_get_user_name(current_user),
                owner_phone=_get_user_phone(current_user),
                latitude=latitude,
                longitude=longitude,
                image=image,
                created_by=current_user,
            )

            return JsonResponse({"success": True})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
    return JsonResponse({"success": False, "error": "Invalid request"}, status=405)



# View untuk render halaman utama
def show_main(request):
    """
    Render halaman utama Court
    Nampilin semua lapangan
    """
    current_user, error_response = _require_user(request)
    if error_response:
        return error_response
    return render(request, 'main.html', {'user': current_user})

def court_detail(request, court_id):
    """Render halaman detail lapangan"""
    court = get_object_or_404(Court, id=court_id)
    current_user, error_response = _require_user(request)
    if error_response:
        return error_response
    context = {
        'court': court,
        'can_manage_slots': court.created_by_id == getattr(current_user, 'id', None) if current_user else False,
        'can_edit': court.created_by_id == getattr(current_user, 'id', None) if current_user else False,
    }
    return render(request, 'detail.html', context)


def edit_court(request, court_id):
    """Edit court attributes by the creator."""
    current_user, error_response = _require_user(request)
    if error_response:
        return error_response

    court = get_object_or_404(Court, id=court_id, created_by=current_user)

    if request.method == 'POST':
        court.name = request.POST.get('name') or court.name
        court.sport_type = request.POST.get('sport_type') or court.sport_type
        court.location = request.POST.get('location') or court.location
        court.address = request.POST.get('address') or court.address

        price_value = clean_decimal(
            request.POST.get('price_per_hour'),
            default=court.price_per_hour,
            min_value=Decimal("0"),
        )
        if price_value is not None:
            court.price_per_hour = price_value

        rating_value = clean_decimal(
            request.POST.get('rating'),
            default=court.rating,
            min_value=Decimal("0"),
            max_value=Decimal("5"),
        )
        if rating_value is not None:
            court.rating = rating_value

        facilities = request.POST.get('facilities')
        if facilities is not None:
            court.facilities = facilities

        description = request.POST.get('description')
        if description is not None:
            court.description = description

        maps_link = request.POST.get('maps_link')
        if maps_link:
            link_lat, link_lng = parse_maps_link(maps_link)
            if link_lat:
                parsed_lat = sanitize_coordinate(link_lat, "latitude")
                if parsed_lat is not None:
                    court.latitude = parsed_lat
            if link_lng:
                parsed_lng = sanitize_coordinate(link_lng, "longitude")
                if parsed_lng is not None:
                    court.longitude = parsed_lng

        image = request.FILES.get('image')
        if image:
            court.image = image

        court.owner_name = _get_user_name(current_user)
        court.owner_phone = _get_user_phone(current_user)

        court.save()
        return redirect('Court:court_detail', court_id=court.id)

    context = {
        'court': court,
        'sport_choices': Court.SPORT_CHOICES,
    }
    return render(request, 'edit_court.html', context)
@require_http_methods(["GET"])
def search_Court(request):
    """
    Search & filter Court dengan AJAX
    GET /api/Court/search/?q=...&sport=...&location=...
    """
    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    query = request.GET.get('q', '')
    sport = request.GET.get('sport', '')
    location = request.GET.get('location', '')
    
    # Start with all Court
    courts_qs = Court.objects.all()
    
    # Filter by search query (nama atau alamat)
    if query:
        courts_qs = courts_qs.filter(
            Q(name__icontains=query) | 
            Q(address__icontains=query) |
            Q(location__icontains=query)
        )
    
    # Filter by sport type
    if sport:
        courts_qs = courts_qs.filter(sport_type=sport)
    
    # Filter by location
    if location:
        courts_qs = courts_qs.filter(location__icontains=location)
    
    # Serialize data
    data = [{
        'id': court.id,
        'name': court.name,
        'sport_type': court.sport_type,
        'location': court.location,
        'address': court.address,
        'price': str(court.price_per_hour),
        'rating': str(court.rating),
        'image': court.image.url if court.image else None,
        'facilities': court.facilities,
        'owned_by_user': court.created_by_id == getattr(current_user, 'id', None),
    } for court in courts_qs]
    
    return JsonResponse({'Court': data})

@require_http_methods(["GET"])
def get_court_detail(request, court_id):
    """
    Get detail court by ID
    GET /api/Court/<id>/
    """
    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    try:
        court = Court.objects.get(id=court_id)
        data = {
            'id': court.id,
            'name': court.name,
            'sport_type': court.sport_type,
            'location': court.location,
            'address': court.address,
            'price': str(court.price_per_hour),
            'rating': str(court.rating),
            'image': court.image.url if court.image else None,
            'facilities': court.facilities,
            'owned_by_user': court.created_by_id == getattr(current_user, 'id', None),
        }
        return JsonResponse({'court': data})
    except Court.DoesNotExist:
        return JsonResponse({'error': 'Court not found'}, status=404)


@require_http_methods(["POST"])
def delete_court(request, court_id):
    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    try:
        court = Court.objects.get(id=court_id, created_by=current_user)
    except Court.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Anda tidak memiliki akses untuk lapangan ini'}, status=403)

    court.delete()
    return JsonResponse({'success': True})

@require_http_methods(["GET"])
def get_availability(request, court_id):
    """
    Get availability status untuk court tertentu di tanggal tertentu
    GET /api/Court/<id>/availability/?date=2024-01-15
    """
    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter required'}, status=400)
    
    try:
        # Parse date
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        court = Court.objects.get(id=court_id)
        
        slot = TimeSlot.objects.filter(court=court, date=date).order_by('start_time').first()
        available = slot.is_available if slot else True
        can_manage = court.created_by_id == getattr(current_user, 'id', None)

        return JsonResponse({'available': available, 'can_manage': can_manage})
        
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    except Court.DoesNotExist:
        return JsonResponse({'error': 'Court not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["POST"])
def set_availability(request, court_id):
    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    try:
        court = Court.objects.get(id=court_id, created_by=current_user)
    except Court.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Anda tidak memiliki akses untuk lapangan ini'}, status=403)

    try:
        payload = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    date_str = payload.get('date')
    is_available = payload.get('is_available', True)

    if not date_str:
        return JsonResponse({'success': False, 'error': 'Tanggal wajib diisi'}, status=400)

    try:
        slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return JsonResponse({'success': False, 'error': 'Format tanggal tidak valid'}, status=400)

    is_available_bool = str(is_available).lower() not in ('false', '0', 'no')

    slot, created = TimeSlot.objects.get_or_create(
        court=court,
        date=slot_date,
        defaults={
            'start_time': time(0, 0),
            'end_time': time(23, 59),
            'is_available': is_available_bool,
        }
    )

    if not created:
        slot.is_available = is_available_bool
        slot.start_time = time(0, 0)
        slot.end_time = time(23, 59)
        slot.save()

    TimeSlot.objects.filter(court=court, date=slot_date).exclude(pk=slot.pk).delete()

    return JsonResponse({'success': True, 'available': slot.is_available})

@require_http_methods(["POST"])
def create_booking(request):
    """
    Create booking by marking a specific date as unavailable.
    POST /api/bookings/
    Body: {
        "court_id": 1,
        "date": "2024-01-15"
    }
    """
    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    try:
        # Parse JSON body
        data = json.loads(request.body)
        court_id = data.get('court_id')
        date_str = data.get('date')

        if not court_id or not date_str:
            return JsonResponse({
                'success': False,
                'message': 'court_id dan date wajib diisi'
            }, status=400)

        try:
            slot_date = datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Format tanggal tidak valid'
            }, status=400)
        
        # Check if court exists
        try:
            court = Court.objects.get(id=court_id)
        except Court.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Court not found'
            }, status=404)
        
        slot, _ = TimeSlot.objects.get_or_create(
            court=court,
            date=slot_date,
            defaults={
                'start_time': time(0, 0),
                'end_time': time(23, 59),
                'is_available': True,
            }
        )

        if not slot.is_available:
            return JsonResponse({
                'success': False,
                'message': 'Tanggal tersebut sudah dibooking'
            }, status=400)

        slot.is_available = False
        slot.start_time = time(0, 0)
        slot.end_time = time(23, 59)
        slot.save()

        return JsonResponse({
            'success': True,
            'message': 'Booking successful',
            'booking': {
                'court_name': court.name,
                'date': slot.date.strftime('%Y-%m-%d'),
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': 'Invalid JSON'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

# Optional: Get all Court (tanpa filter)
@require_http_methods(["GET"])
def get_all_Court(request):
    """
    Get semua Court
    GET /api/Court/
    """
    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    Court_qs = Court.objects.all()
    
    data = [{
        'id': court.id,
        'name': court.name,
        'sport_type': court.sport_type,
        'location': court.location,
        'price': str(court.price_per_hour),
        'rating': str(court.rating),
        'image': court.image.url if court.image else None,
        'facilities': court.facilities,
        'is_available': court.is_available(),
        'latitude': float(court.latitude) if court.latitude is not None else None,
        'longitude': float(court.longitude) if court.longitude is not None else None,
        'owned_by_user': court.created_by_id == getattr(current_user, 'id', None),
    } for court in Court_qs]

    return JsonResponse({'Court': data})

@require_http_methods(["GET"])
def api_search_court(request):
    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    q = request.GET.get('q', '')
    sport = request.GET.get('sport', '')
    location = request.GET.get('location', '')

    courts = Court.objects.all()
    if q:
        courts = courts.filter(name__icontains=q)
    if sport:
        courts = courts.filter(sport_type=sport)
    if location:
        courts = courts.filter(location__icontains=location)

    data = []
    for c in courts:
        data.append({
            "id": c.id,
            "name": c.name,
            "sport_type": c.sport_type,
            "rating": float(c.rating),
            "location": c.location,
            "price": float(c.price_per_hour),
            "is_available": c.is_available(),
            "image": c.image.url if c.image else None,
            "owned_by_user": c.created_by_id == getattr(current_user, 'id', None),
        })
    return JsonResponse({"court": data})  # ✅ Key disamakan dengan main.html



@csrf_exempt
def api_court_whatsapp(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

    current_user, error_response = _require_user(request, json_mode=True)
    if error_response:
        return error_response

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON'}, status=400)

    court_id = data.get('court_id')
    if not court_id:
        return JsonResponse({'success': False, 'error': 'court_id is required'}, status=400)

    try:
        court = Court.objects.get(id=court_id)
    except Court.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Lapangan tidak ditemukan'}, status=404)

    whatsapp_link = court.get_whatsapp_link(
        date=data.get('date'),
        time=data.get('time')
    )

    return JsonResponse({'success': True, 'whatsapp_link': whatsapp_link})


@csrf_exempt
def get_whatsapp_link(request):
    """
    Generate WhatsApp booking link for a given court and selected time.
    """
    if request.method == 'POST':
        current_user, error_response = _require_user(request, json_mode=True)
        if error_response:
            return error_response
        try:
            data = json.loads(request.body)
            court_id = data.get('court_id')
            date = data.get('date')
            time = data.get('time')

            # Ambil data court dari database
            court = Court.objects.get(id=court_id)

            whatsapp_link = court.get_whatsapp_link(date=date, time=time)

            return JsonResponse({'success': True, 'whatsapp_link': whatsapp_link})
        except Court.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Lapangan tidak ditemukan'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'error': 'Invalid request method'}, status=405)

