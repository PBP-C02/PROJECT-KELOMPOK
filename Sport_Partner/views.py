from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from Auth_Profile.models import User
from Sport_Partner.models import PartnerPost, PostParticipants
import json
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q, Count

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
    # 1. Mulai dengan mengambil semua data (QuerySet dasar)
    posts = PartnerPost.objects.select_related('creator')

    # 2. FILTERING: Kategori Olahraga (Sport)
    # Analogi: Memilih lorong rak spesifik di gudang
    selected_sport = request.GET.get('sport') # Mengambil param ?sport=...
    if selected_sport and selected_sport != "":
        # iexact: Case-insensitive (Tennis sama dengan tennis)
        posts = posts.filter(category__iexact=selected_sport)

    # 3. SEARCHING: Pencarian Teks (Judul atau Lokasi)
    # Analogi: Membaca label barang satu per satu
    search_query = request.GET.get('q') # Mengambil param ?q=...
    if search_query:
        # Gunakan Q untuk logika OR. Mencari di title ATAU lokasi
        posts = posts.filter(
            Q(title__icontains=search_query) | 
            Q(lokasi__icontains=search_query)
        )

    # 4. SORTING: Pengurutan
    # Analogi: Menyusun barang di rak agar mudah diambil
    sort_option = request.GET.get('sort')
    
    # Kita perlu anotasi jumlah partisipan jika ingin sorting berdasarkan slot/popularitas
    if sort_option == 'slots_desc':
        posts = posts.annotate(num_participants=Count('postparticipants')).order_by('-num_participants')
    elif sort_option == 'date_desc': # Terbaru
        posts = posts.order_by('-tanggal', '-jam_mulai')
    elif sort_option == 'date_asc': # Terlama (atau jadwal terdekat dari sekarang)
        posts = posts.order_by('tanggal', 'jam_mulai')
    elif sort_option == 'name_asc': # Abjad A-Z
        posts = posts.order_by('title')
    elif sort_option == 'name_desc': # Abjad Z-A
        posts = posts.order_by('-title')
    else:
        # Default sorting: Paling baru dibuat atau jadwal terdekat
        posts = posts.order_by('-tanggal')

    # --- Eksekusi Query (Looping Data) ---
    # Django baru benar-benar memanggil database di sini (Lazy Loading)
    
    data = []

    # Cek user yang login untuk status partisipan
    current_user_id = request.session.get('user_id')
    current_user = None
    if current_user_id:
        try:
            current_user = User.objects.get(id=current_user_id)
        except User.DoesNotExist:
            pass

    for post in posts:
        is_participant = False
        is_creator = False
        
        creator_name = "Unknown"
        creator_id = "0"

        # Logika User Login
        if current_user:
            is_participant = post.is_participant(current_user)
        
        if post.creator:
            creator_name = post.creator.nama 
            creator_id = str(post.creator.id)
            
            if current_user and post.creator.id == current_user.id:
                is_creator = True

        data.append({
            "post_id": str(post.post_id),
            "title": post.title,
            "description": post.description,
            "category": post.category,
            "tanggal": str(post.tanggal),
            "jam_mulai": post.jam_mulai.strftime("%H:%M"),
            "jam_selesai": post.jam_selesai.strftime("%H:%M"),
            "lokasi": post.lokasi,
            "creator_name": creator_name,
            "creator_id": creator_id,
            "total_participants": post.total_participants,
            "is_participant": is_participant,
            "is_creator": is_creator 
        })
        
    return JsonResponse(data, safe=False)

@csrf_exempt
def edit_post_json(request, post_id):
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)

    if request.method == 'POST':
        post = get_object_or_404(PartnerPost, post_id=post_id)
        
        # Cek apakah yang edit adalah creator asli
        if str(post.creator.id) != str(request.session['user_id']):
             return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)

        data = json.loads(request.body)
        
        # Update field
        post.title = data.get('title', post.title)
        post.description = data.get('description', post.description)
        post.category = data.get('category', post.category)
        post.lokasi = data.get('lokasi', post.lokasi)
        
        # Update tanggal/waktu jika ada
        if 'tanggal' in data:
            post.tanggal = data['tanggal']
        if 'jam_mulai' in data:
            post.jam_mulai = data['jam_mulai']
        if 'jam_selesai' in data:
            post.jam_selesai = data['jam_selesai']
            
        post.save()
        return JsonResponse({'success': True, 'message': 'Post updated successfully'})

    return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)

@csrf_exempt
def delete_post_json(request, post_id):
    if 'user_id' not in request.session:
        return JsonResponse({'success': False, 'message': 'Login required'}, status=401)

    if request.method == 'POST':
        post = get_object_or_404(PartnerPost, post_id=post_id)
        
        # Cek authorization
        if str(post.creator.id) != str(request.session['user_id']):
             return JsonResponse({'success': False, 'message': 'Unauthorized'}, status=403)
             
        post.delete()
        return JsonResponse({'success': True, 'message': 'Post deleted successfully'})
