from rest_framework import serializers
from .models import VehicleCommand, EventLog
from vehicle_tracking.models import VehicleLocation

class VehicleCommandSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = VehicleCommand
        fields = ['id', 'command', 'executed', 'user', 'user_name', 'timestamp', 'executed_at']
        read_only_fields = ['id', 'executed', 'timestamp', 'executed_at']

class EventLogSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='user.username', read_only=True)
    
    class Meta:
        model = EventLog
        fields = ['id', 'user', 'user_name', 'event_type', 'description', 'timestamp', 'ip_address']
        read_only_fields = ['id', 'timestamp']

class VehicleLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VehicleLocation
        fields = ['id', 'latitude', 'longitude', 'speed', 'heading', 'timestamp']