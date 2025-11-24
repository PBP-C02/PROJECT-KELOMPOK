from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from Auth_Profile.models import User
from Sport_Partner.models import PartnerPost, PostParticipants
import json
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt

def show_post(request):
    # Cek login
    if 'user_id' not in request.session:
        return redirect('/login/')
    
    user_now = User.objects.get(id=request.session['user_id'])
    post_list = PartnerPost.objects.all()
    
    context = {
        'user': user_now,
        'post_list': post_list
    }
    
    return render(request, "sport_partner.html", context)

@csrf_exempt
def create_post(request):
    # Cek login
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Silakan login terlebih dahulu'}, status=401)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        title = data.get('title')
        description = data.get('description')
        category = data.get('category')
        tanggal = data.get('tanggal')
        jam_mulai = data.get('jam_mulai')
        jam_selesai = data.get('jam_selesai')
        lokasi = data.get('lokasi')
        
        # Validasi input kosong
        if not all([title, description, category, tanggal, jam_mulai, jam_selesai, lokasi]):
            return JsonResponse({
                'success': False,
                'message': 'Semua field harus diisi'
            })
        
        # Validasi format tanggal
        try:
            datetime.strptime(tanggal, '%Y-%m-%d')
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Format tanggal tidak valid'
            })
        
        # Validasi format waktu
        try:
            datetime.strptime(jam_mulai, '%H:%M')
            datetime.strptime(jam_selesai, '%H:%M')
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Format waktu tidak valid'
            })
        
        try:
            # Ambil user yang sedang login
            creator = User.objects.get(id=request.session['user_id'])
            
            # Buat post baru
            partner_post = PartnerPost.objects.create(
                creator=creator,
                title=title,
                description=description,
                category=category,
                tanggal=tanggal,
                jam_mulai=jam_mulai,
                jam_selesai=jam_selesai,
                lokasi=lokasi
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Post berhasil dibuat',
                'redirect_url': '/sport_partner/'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Terjadi kesalahan: {str(e)}'
            })
    
    return render(request, 'create_post.html')


def post_detail(request, post_id):
    # Cek login
    if 'user_id' not in request.session:
        return redirect('/login/')
    
    post = get_object_or_404(PartnerPost, post_id=post_id)
    user_now = User.objects.get(id=request.session['user_id'])
    
    context = {
        'post': post,
        'user': user_now,
        'is_participant': post.is_participant(user_now),
    }
    
    return render(request, 'post_detail.html', context)


def get_participants_json(request, post_id):
    """API untuk ambil list participants dalam format JSON"""
    post = get_object_or_404(PartnerPost, post_id=post_id)
    
    participants = []
    for pp in post.postparticipants_set.select_related('participant').all():
        participants.append({
            'id': str(pp.participant.id),
            'nama': pp.participant.nama,
            'email': pp.participant.email,
        })
    
    return JsonResponse({
        'success': True,
        'total': len(participants),
        'participants': participants
    })

@csrf_exempt
def join_post(request, post_id):
    """User join ke post"""
    # Cek login
    if 'user_id' not in request.session:
        return JsonResponse({
            'success': False,
            'message': 'Anda harus login terlebih dahulu'
        })
    
    if request.method == 'POST':
        post = get_object_or_404(PartnerPost, post_id=post_id)
        user = User.objects.get(id=request.session['user_id'])
        
        # Cek apakah ini creator
        if post.creator.id == user.id:
            return JsonResponse({
                'success': False,
                'message': 'Anda adalah creator post ini'
            })
        
        # Tambah participant
        if post.add_participant(user):
            return JsonResponse({
                'success': True,
                'message': 'Berhasil join!',
                'total_participants': post.total_participants
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Anda sudah join post ini'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Method tidak valid'
    })

@csrf_exempt
def leave_post(request, post_id):
    """User leave dari post"""
    # Cek login
    if 'user_id' not in request.session:
        return JsonResponse({
            'success': False,
            'message': 'Anda harus login terlebih dahulu'
        })
    
    if request.method == 'POST':
        post = get_object_or_404(PartnerPost, post_id=post_id)
        user = User.objects.get(id=request.session['user_id'])
        
        post.remove_participant(user)
        
        return JsonResponse({
            'success': True,
            'message': 'Berhasil leave',
            'total_participants': post.total_participants
        })
    
    return JsonResponse({
        'success': False,
        'message': 'Method tidak valid'
    })

@csrf_exempt
def show_json(request):
    posts = PartnerPost.objects.select_related('creator').all()
    data = []

    # Cek siapa user yang sedang request (untuk status is_participant)
    current_user_id = request.session.get('user_id')
    current_user = None
    if current_user_id:
        try:
            current_user = User.objects.get(id=current_user_id)
        except User.DoesNotExist:
            pass

    for post in posts:
        # Logika cek apakah user sudah join
        is_participant = False
        if current_user:
            is_participant = post.is_participant(current_user)

        data.append({
            "post_id": str(post.post_id),
            "title": post.title,
            "description": post.description,
            "category": post.category,
            "tanggal": str(post.tanggal),
            "jam_mulai": post.jam_mulai.strftime("%H:%M"), # Format jam biar rapi
            "jam_selesai": post.jam_selesai.strftime("%H:%M"),
            "lokasi": post.lokasi,
            
            # INI KUNCI PERBAIKANNYA:
            "creator_name": post.creator.nama,  # Ambil nama dari relasi creator
            "creator_id": str(post.creator.id),
            
            "total_participants": post.total_participants,
            "is_participant": is_participant
        })
        
    return JsonResponse(data, safe=False)
