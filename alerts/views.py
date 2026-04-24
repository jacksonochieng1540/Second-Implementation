from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from .models import Alert

@api_view(['GET'])
@permission_classes([AllowAny])
def alert_list(request):
    alerts = Alert.objects.all()[:50]
    alerts_data = []
    for alert in alerts:
        alerts_data.append({
            'id': alert.id,
            'title': alert.title,
            'description': alert.description,
            'severity': alert.severity,
            'timestamp': alert.timestamp.isoformat(),
            'image_url': alert.image.url if alert.image else None,
            'is_resolved': alert.is_resolved
        })
    return Response(alerts_data)