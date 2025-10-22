from django.shortcuts import render

# Create your views here.
def show_post(request):
    context = {
        'npm' : '2406432103',
        'name': 'Darrell',
    }

    return render(request, "main.html", context)