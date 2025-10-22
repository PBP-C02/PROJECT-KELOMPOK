from decimal import Decimal, InvalidOperation
from datetime import datetime
import json

from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

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

    min_limit, max_limit = limits.get(coordinate_type, (None, None))
    if min_limit is None:
        return None

    if coordinate < min_limit or coordinate > max_limit:
        return None

    return coordinate

def add_court(request):
    """
    Form untuk menambahkan court secara manual (via halaman web).
    Semua user bisa akses.
    """
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
        owner_name = request.POST.get('owner_name')
        owner_phone = request.POST.get('owner_phone')
        latitude = sanitize_coordinate(request.POST.get('latitude'), "latitude")
        longitude = sanitize_coordinate(request.POST.get('longitude'), "longitude")

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
            image=image
        )
        print("✅ Lapangan berhasil dibuat.")
        return redirect('Court:show_main')

    return render(request, 'add_court.html')

@csrf_exempt
def api_add_court(request):
    """API untuk menambah lapangan via AJAX."""
    if request.method == "POST":
        try:
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
            latitude = sanitize_coordinate(data.get('latitude'), "latitude")
            longitude = sanitize_coordinate(data.get('longitude'), "longitude")

            Court.objects.create(
                name=data.get('name'),
                sport_type=data.get('sport_type'),
                location=data.get('location'),
                address=data.get('address'),
                price_per_hour=price_per_hour,
                facilities=data.get('facilities') or "",
                rating=rating,
                description=data.get('description'),
                owner_name=data.get('owner_name'),
                owner_phone=data.get('owner_phone'),
                latitude=latitude,
                longitude=longitude,
                image=image
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
    return render(request, 'main.html')

def court_detail(request, court_id):
    """Render halaman detail lapangan"""
    court = get_object_or_404(Court, id=court_id)
    context = {
        'court': court,
    }
    return render(request, 'detail.html', context)
# API Endpoints
@require_http_methods(["GET"])
def search_Court(request):
    """
    Search & filter Court dengan AJAX
    GET /api/Court/search/?q=...&sport=...&location=...
    """
    query = request.GET.get('q', '')
    sport = request.GET.get('sport', '')
    location = request.GET.get('location', '')
    
    # Start with all Court
    Court = Court.objects.all()
    
    # Filter by search query (nama atau alamat)
    if query:
        Court = Court.filter(
            Q(name__icontains=query) | 
            Q(address__icontains=query) |
            Q(location__icontains=query)
        )
    
    # Filter by sport type
    if sport:
        Court = Court.filter(sport_type=sport)
    
    # Filter by location
    if location:
        Court = Court.filter(location__icontains=location)
    
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
    } for court in Court]
    
    return JsonResponse({'Court': data})

@require_http_methods(["GET"])
def get_court_detail(request, court_id):
    """
    Get detail court by ID
    GET /api/Court/<id>/
    """
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
        }
        return JsonResponse({'court': data})
    except Court.DoesNotExist:
        return JsonResponse({'error': 'Court not found'}, status=404)

@require_http_methods(["GET"])
def get_availability(request, court_id):
    """
    Get available time slots untuk court tertentu di tanggal tertentu
    GET /api/Court/<id>/availability/?date=2024-01-15
    """
    date_str = request.GET.get('date')
    
    if not date_str:
        return JsonResponse({'error': 'Date parameter required'}, status=400)
    
    try:
        # Parse date
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Get time slots
        slots = TimeSlot.objects.filter(
            court_id=court_id,
            date=date
        ).order_by('start_time')
        
        # Serialize data
        data = [{
            'id': slot.id,
            'start_time': slot.start_time.strftime('%H:%M:%S'),
            'end_time': slot.end_time.strftime('%H:%M:%S'),
            'is_available': slot.is_available,
            'time_label': slot.get_time_label(),
        } for slot in slots]
        
        return JsonResponse({'slots': data})
        
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@require_http_methods(["POST"])
def create_booking(request):
    """
    Create booking
    POST /api/bookings/
    Body: {
        "court_id": 1,
        "date": "2024-01-15",
        "time_slot_id": 5
    }
    """
    try:
        # Parse JSON body
        data = json.loads(request.body)
        court_id = data.get('court_id')
        time_slot_id = data.get('time_slot_id')
        
        # Validate data
        if not court_id or not time_slot_id:
            return JsonResponse({
                'success': False,
                'message': 'court_id and time_slot_id are required'
            }, status=400)
        
        # Check if court exists
        try:
            court = Court.objects.get(id=court_id)
        except Court.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Court not found'
            }, status=404)
        
        # Check if time slot exists and available
        try:
            time_slot = TimeSlot.objects.get(id=time_slot_id, court_id=court_id)
            
            if not time_slot.is_available:
                return JsonResponse({
                    'success': False,
                    'message': 'Time slot is not available'
                }, status=400)
            
            # Mark as unavailable (booking confirmed)
            time_slot.is_available = False
            time_slot.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Booking successful',
                'booking': {
                    'court_name': court.name,
                    'date': time_slot.date.strftime('%Y-%m-%d'),
                    'start_time': time_slot.start_time.strftime('%H:%M'),
                    'end_time': time_slot.end_time.strftime('%H:%M'),
                }
            })
            
        except TimeSlot.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Time slot not found'
            }, status=404)
        
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
    Court = Court.objects.all()
    
    data = [{
        'id': court.id,
        'name': court.name,
        'sport_type': court.sport_type,
        'location': court.location,
        'price': str(court.price_per_hour),
        'rating': str(court.rating),
        'image': court.image.url if court.image else None,
    } for court in Court]
    
    return JsonResponse({'Court': data})

from django.http import JsonResponse
from .models import Court

from django.http import JsonResponse
from .models import Court

def api_search_court(request):
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
            "image": c.image.url if c.image else None
        })
    return JsonResponse({"court": data})  # ✅ Key disamakan dengan main.html



@csrf_exempt
def api_court_whatsapp(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Invalid request'}, status=400)

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

