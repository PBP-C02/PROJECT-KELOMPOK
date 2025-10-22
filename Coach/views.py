from django.shortcuts import render, redirect, get_object_or_404
from Coach.forms import Coach
from Coach.models import Coach
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.core import serializers
from django.contrib import messages
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
import datetime
from django.views.decorators.csrf import csrf_exempt, csrf_protect
from django.views.decorators.http import require_POST, require_GET
from django.urls import reverse
from django.utils.html import strip_tags
import json

def show_main(request):
    filter_type = request.GET.get("filter", "all")  # default 'all'
    
    if filter_type == "all":
        coach_list = Coach.objects.all()
    else:
        coach_list = Coach.objects.filter(user=request.user)

    context = {
        'coach_list': coach_list,
    }

    return render(request, "main.html", context)

def show_coach(request, id):
    coach = get_object_or_404(Coach, pk=id)

    context = {
        'coach': coach
    }

    return render(request, "coach_detail.html", context)