from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.hashers import make_password, check_password
from Auth_Profile.models import User
import json
from datetime import datetime

def homepage_view(request):
    if 'user_id' not in request.session:
        return redirect('Auth_Profile:login')
    
    try:
        user = User.objects.get(id=request.session['user_id'])
    except User.DoesNotExist:
        request.session.flush()
        return redirect('Auth_Profile:login')

    context = {
        'user': user
    }
    return render(request, 'homepage.html', context)

def profile_display_view(request):
    if 'user_id' not in request.session:
        return redirect('Auth_Profile:login')
    
    try:
        user = User.objects.get(id=request.session['user_id'])
    except User.DoesNotExist:
        request.session.flush()
        return redirect('Auth_Profile:login')

    context = {
        'user': user
    }
    return render(request, 'profile_display.html', context)

def profile_edit_view(request):
    if 'user_id' not in request.session:
        return redirect('Auth_Profile:login')
    
    try:
        user = User.objects.get(id=request.session['user_id'])
    except User.DoesNotExist:
        request.session.flush()
        return redirect('Auth_Profile:login')

    if request.method == 'POST':
        nama = request.POST.get('nama')
        kelamin = request.POST.get('kelamin')
        tanggal_lahir = request.POST.get('tanggal_lahir')
        nomor_handphone = request.POST.get('nomor_handphone')
        
        if not all([nama, kelamin, tanggal_lahir, nomor_handphone]):
            context = {'user': user, 'error_message': 'Semua field harus diisi'}
            return render(request, 'profile_edit.html', context)
        
        try:
            datetime.strptime(tanggal_lahir, '%Y-%m-%d')
        except ValueError:
            context = {'user': user, 'error_message': 'Format tanggal lahir tidak valid'}
            return render(request, 'profile_edit.html', context)
        
        user.nama = nama
        user.kelamin = kelamin
        user.tanggal_lahir = tanggal_lahir
        user.nomor_handphone = nomor_handphone
        user.save()
        
        request.session['nama'] = user.nama
        request.session['kelamin'] = user.kelamin
        request.session['tanggal_lahir'] = str(user.tanggal_lahir)
        request.session['nomor_handphone'] = user.nomor_handphone
        
        return redirect('Auth_Profile:profile_display')

    context = {
        'user': user
    }
    return render(request, 'profile_edit.html', context)

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
            
            if check_password(password, user.password):
                # Login user menggunakan auth
                auth.login(request, user)
                
                # Simpan session
                request.session['user_id'] = str(user.id)
                request.session['email'] = user.email
                request.session['nama'] = user.nama
                request.session['kelamin'] = user.kelamin
                request.session['tanggal_lahir'] = str(user.tanggal_lahir)
                request.session['nomor_handphone'] = user.nomor_handphone
                
                next_url = request.GET.get('next', '/')
                return JsonResponse({
                    'success': True,
                    'message': 'Login berhasil',
                    'redirect_url': next_url
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
        role = data.get('role')
        # Tambahkan username, gunakan email sebagai username
        username = email.split('@')[0]  # Atau bisa menggunakan email langsung
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
        
        # Cek username sudah terdaftar
        if User.objects.filter(username=username).exists():
            return JsonResponse({
                'success': False,
                'message': 'Username sudah terdaftar'
            })

        # Buat user baru
        try:
            user = User.objects.create(
                username=username,  # Tambahkan ini
                nama=nama,
                email=email,
                kelamin=kelamin,
                role=role,
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
