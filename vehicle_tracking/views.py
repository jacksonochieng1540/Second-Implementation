from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import VehicleLocation
from api.serializers import VehicleLocationSerializer

@api_view(['GET'])
def get_latest_location(request):
    try:
        location = VehicleLocation.objects.latest('timestamp')
        serializer = VehicleLocationSerializer(location)
        return Response(serializer.data)
    except VehicleLocation.DoesNotExist:
        return Response({'error': 'No location data available'}, status=404)

@api_view(['GET'])
def get_location_history(request):
    locations = VehicleLocation.objects.order_by('-timestamp')[:100]
    serializer = VehicleLocationSerializer(locations, many=True)
    return Response(serializer.data)