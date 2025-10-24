from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from Auth_Profile.models import User
import json
from datetime import datetime

def homepage_view(request):
    user = User.objects.get(id=request.session['user_id'])
    context = {
        'user': user
    }
    return render(request, 'homepage.html', context)
def login_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return JsonResponse({
                'success': False,
                'message': 'Email dan password harus diisi'
            })
        
        try:
            user = User.objects.get(email=email)
            
            # Cek password
            if check_password(password, user.password):
                # Simpan user info di session
                request.session['user_id'] = str(user.id)
                request.session['email'] = user.email
                request.session['nama'] = user.nama
                request.session['kelamin'] = user.kelamin
                request.session['tanggal_lahir'] = str(user.tanggal_lahir)
                request.session['nomor_handphone'] = user.nomor_handphone
                
                return JsonResponse({
                    'success': True,
                    'message': 'Login berhasil',
                    'redirect_url': '/'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Email atau password salah'
                })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Email atau password salah'
            })
    
    return render(request, 'login.html')

def register_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        nama = data.get('nama')
        email = data.get('email')
        kelamin = data.get('kelamin')
        tanggal_lahir = data.get('tanggal_lahir')
        nomor_handphone = data.get('nomor_handphone')
        password = data.get('password')
        password2 = data.get('password2')
        
        # Validasi input kosong
        if not all([nama, email, kelamin, tanggal_lahir, nomor_handphone, password, password2]):
            return JsonResponse({
                'success': False,
                'message': 'Semua field harus diisi'
            })
        
        # Validasi format email
        if '@' not in email:
            return JsonResponse({
                'success': False,
                'message': 'Format email tidak valid'
            })
        
        # Validasi kelamin
        if kelamin not in ['L', 'P']:
            return JsonResponse({
                'success': False,
                'message': 'Kelamin harus L atau P'
            })
        
        # Validasi format tanggal lahir
        try:
            datetime.strptime(tanggal_lahir, '%Y-%m-%d')
        except ValueError:
            return JsonResponse({
                'success': False,
                'message': 'Format tanggal lahir tidak valid (gunakan YYYY-MM-DD)'
            })
        
        # Validasi nomor handphone (hanya angka)
        if not nomor_handphone.replace('+', '').replace('-', '').isdigit():
            return JsonResponse({
                'success': False,
                'message': 'Nomor handphone hanya boleh berisi angka'
            })
        
        # Validasi password match
        if password != password2:
            return JsonResponse({
                'success': False,
                'message': 'Password tidak cocok'
            })
        
        # Validasi panjang password
        if len(password) < 8:
            return JsonResponse({
                'success': False,
                'message': 'Password minimal 8 karakter'
            })
        
        # Cek email sudah terdaftar
        if User.objects.filter(email=email).exists():
            return JsonResponse({
                'success': False,
                'message': 'Email sudah terdaftar'
            })
        
        # Buat user baru dengan password yang di-hash
        try:
            user = User.objects.create(
                nama=nama,
                email=email,
                kelamin=kelamin,
                tanggal_lahir=tanggal_lahir,
                nomor_handphone=nomor_handphone,
                password=make_password(password)
            )
            return JsonResponse({
                'success': True,
                'message': 'Registrasi berhasil',
                'redirect_url': '/login/'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Terjadi kesalahan: {str(e)}'
            })
    
    return render(request, 'register.html')

def logout_view(request):
    # Hapus session
    request.session.flush()
    return redirect('/login/')
