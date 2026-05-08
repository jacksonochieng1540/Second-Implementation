from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import VehicleLocation
from authentication.models import UserProfile  
from django.contrib.auth.models import User
import json
import requests


def get_user_role(user):
    """Helper to get user role from UserProfile"""
    try:
        if hasattr(user, 'profile'):
            return user.profile.role
    except:
        pass
    return 'user'


# ============= EXISTING FUNCTIONS =============

def get_latest_location(request):
    """Get latest location - API endpoint"""
    latest = VehicleLocation.objects.first()
    if latest:
        return JsonResponse({
            'latitude': float(latest.latitude),
            'longitude': float(latest.longitude),
            'speed': latest.speed,
            'heading': latest.heading,
            'timestamp': latest.timestamp.isoformat()
        })
    return JsonResponse({'error': 'No location data'}, status=404)


def get_location_history(request):
    """Get location history - API endpoint"""
    days = int(request.GET.get('days', 1))
    locations = VehicleLocation.objects.filter(
        timestamp__gte=timezone.now() - timezone.timedelta(days=days)
    )[:100]
    
    data = [{
        'latitude': float(loc.latitude),
        'longitude': float(loc.longitude),
        'speed': loc.speed,
        'heading': loc.heading,
        'timestamp': loc.timestamp.isoformat()
    } for loc in locations]
    
    return JsonResponse({'locations': data})


# ============= DASHBOARD VIEWS =============

@login_required
def dashboard_home(request):
    """Main dashboard view with map"""
    user_role = get_user_role(request.user)
    
    # Get latest location for map
    latest_location = VehicleLocation.objects.first()
    
    context = {
        'user_role': user_role,
        'is_admin': user_role == 'owner',
        'is_kinsman': user_role == 'kinsman',
        'latest_location': latest_location,
    }
    return render(request, 'dashboard/home.html', context)


@login_required
def admin_panel(request):
    """Admin panel for immobilize/enable engine and manage kinsmen"""
    # Only allow admin/owner users
    if get_user_role(request.user) != 'owner':
        messages.error(request, 'Access denied. Admin only.')
        return redirect('dashboard_home')
    
    # Get kinsmen (users with role='kinsman')
    kinsmen = User.objects.filter(profile__role='kinsman')
    
    context = {
        'kinsmen': kinsmen,
        'vehicle_id': 1,
    }
    return render(request, 'dashboard/admin_panel.html', context)


def admin_login_view(request):
    """Custom admin login page"""
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and get_user_role(user) == 'owner':
            login(request, user)
            return redirect('admin_panel')
        else:
            messages.error(request, 'Invalid credentials or not an admin')
    
    return render(request, 'dashboard/admin_login.html')


# ============= ENGINE CONTROL API - FIXED URL =============
# FIXED: Changed from /api/send-command/ to /api/vehicle/send-command/

@require_http_methods(["POST"])
@csrf_exempt
def immobilize_engine(request, vehicle_id):
    """Immobilize engine - sends LOCK command to Raspberry Pi"""
    try:
        response = requests.post(
            'http://10.251.159.57:8000/api/vehicle/send-command/',  # FIXED URL
            headers={'X-API-KEY': 'mysecurekey123', 'Content-Type': 'application/json'},
            json={'command': 'LOCK'},
            timeout=3
        )
        if response.status_code == 201:
            return JsonResponse({'success': True, 'message': 'Engine immobilized'})
        else:
            return JsonResponse({'success': False, 'message': f'Server returned {response.status_code}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


@require_http_methods(["POST"])
@csrf_exempt
def enable_engine(request, vehicle_id):
    """Enable engine - sends UNLOCK command to Raspberry Pi"""
    try:
        response = requests.post(
            'http://10.251.159.57:8000/api/vehicle/send-command/',  # FIXED URL
            headers={'X-API-KEY': 'mysecurekey123', 'Content-Type': 'application/json'},
            json={'command': 'UNLOCK'},
            timeout=3
        )
        if response.status_code == 201:
            return JsonResponse({'success': True, 'message': 'Engine enabled'})
        else:
            return JsonResponse({'success': False, 'message': f'Server returned {response.status_code}'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ============= EMERGENCY ACCESS API =============

@require_http_methods(["POST"])
@csrf_exempt
def grant_emergency_access(request, vehicle_id):
    """Grant emergency access to a kinsman for a limited time"""
    # Only owner can grant access
    if get_user_role(request.user) != 'owner':
        return JsonResponse({'success': False, 'message': 'Permission denied'})
    
    try:
        data = json.loads(request.body)
        kinsman_id = data.get('kinsman_id')
        duration_minutes = int(data.get('duration_minutes', 30))
        
        kinsman = User.objects.get(id=kinsman_id)
        
        return JsonResponse({
            'success': True, 
            'message': f'Emergency access granted to {kinsman.username} for {duration_minutes} minutes'
        })
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Kinsman not found'})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)})


# ============= LOCATION API =============

@login_required
def get_vehicle_location_api(request, vehicle_id):
    """API endpoint for real-time location on map"""
    latest = VehicleLocation.objects.first()
    
    if latest:
        return JsonResponse({
            'latitude': float(latest.latitude),
            'longitude': float(latest.longitude),
            'speed': latest.speed,
            'heading': latest.heading,
            'timestamp': latest.timestamp.isoformat()
        })
    return JsonResponse({'error': 'No location data'}, status=404)
