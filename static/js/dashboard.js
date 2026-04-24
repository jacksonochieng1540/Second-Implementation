// Dashboard JavaScript - Vehicle Tracking System
// Make functions globally available

// Global variables
let map = null;
let vehicleMarker = null;
let pathPoints = [];
let pathLine = null;
let ws = null;
let currentLocation = { lat: 40.7128, lng: -74.0060 };
let mediaStream = null;

// Initialize map when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('Dashboard initializing...');
    initMap();
    connectWebSocket();
    initWebcam();
    loadAlerts();
    setInterval(loadAlerts, 30000);
});

// Initialize Leaflet Map
function initMap() {
    map = L.map('map').setView([40.7128, -74.0060], 15);
    
    L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 19,
        minZoom: 3
    }).addTo(map);
}

// Custom car icon
const carIcon = L.divIcon({
    html: '<div style="font-size: 40px; filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));"><i class="fas fa-car-side" style="color: #667eea;"></i></div>',
    iconSize: [40, 40],
    className: 'custom-car-icon'
});

// WebSocket connection
function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = `${protocol}${window.location.host}/ws/vehicle/`;
    
    ws = new WebSocket(wsUrl);
    
    ws.onopen = function() {
        console.log('WebSocket connected');
        const statusDiv = document.getElementById('connectionStatus');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="status-dot online"></span> Connected to server';
        }
        ws.send(JSON.stringify({ type: 'GET_HISTORY' }));
    };
    
    ws.onmessage = function(e) {
        const data = JSON.parse(e.data);
        console.log('WebSocket message:', data);
        
        if (data.type === 'LOCATION_UPDATE') {
            updateVehiclePosition(data.data);
        } else if (data.type === 'LOCATION_HISTORY') {
            loadLocationHistory(data.data);
        } else if (data.type === 'COMMAND_UPDATE') {
            handleCommandUpdate(data.data);
        }
    };
    
    ws.onerror = function(error) {
        console.error('WebSocket error:', error);
        const statusDiv = document.getElementById('connectionStatus');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="status-dot offline"></span> Connection error';
        }
    };
    
    ws.onclose = function() {
        console.log('WebSocket disconnected');
        const statusDiv = document.getElementById('connectionStatus');
        if (statusDiv) {
            statusDiv.innerHTML = '<span class="status-dot offline"></span> Reconnecting...';
        }
        setTimeout(connectWebSocket, 3000);
    };
}

function updateVehiclePosition(locationData) {
    const lat = parseFloat(locationData.latitude);
    const lng = parseFloat(locationData.longitude);
    
    currentLocation = { lat, lng };
    
    // Update stats
    const speedEl = document.getElementById('speedValue');
    const headingEl = document.getElementById('headingValue');
    if (speedEl) speedEl.textContent = locationData.speed || 0;
    if (headingEl) headingEl.textContent = locationData.heading || 0;
    
    // Update marker
    if (vehicleMarker) {
        vehicleMarker.setLatLng([lat, lng]);
    } else if (map) {
        vehicleMarker = L.marker([lat, lng], { icon: carIcon }).addTo(map);
    }
    
    // Center map on vehicle
    if (map) map.panTo([lat, lng]);
    
    // Add to path
    pathPoints.push([lat, lng]);
    if (pathPoints.length > 50) pathPoints.shift();
    
    updatePathLine();
}

function updatePathLine() {
    if (!map) return;
    if (pathLine) map.removeLayer(pathLine);
    if (pathPoints.length > 1) {
        pathLine = L.polyline(pathPoints, {
            color: '#667eea',
            weight: 3,
            opacity: 0.8,
            lineJoin: 'round'
        }).addTo(map);
    }
}

function loadLocationHistory(historyData) {
    pathPoints = historyData.map(h => [parseFloat(h.latitude), parseFloat(h.longitude)]);
    if (pathPoints.length > 0 && map) {
        const lastPoint = pathPoints[pathPoints.length - 1];
        if (vehicleMarker) {
            vehicleMarker.setLatLng(lastPoint);
        } else {
            vehicleMarker = L.marker(lastPoint, { icon: carIcon }).addTo(map);
        }
        map.setView(lastPoint, 15);
        updatePathLine();
    }
}

function handleCommandUpdate(commandData) {
    console.log('Command update:', commandData);
    if (commandData.command === 'UNLOCK') {
        updateEngineStatus('UNLOCKED');
    } else if (commandData.command === 'LOCK') {
        updateEngineStatus('LOCKED');
    }
}

function updateEngineStatus(status) {
    const statusDiv = document.getElementById('engineStatus');
    if (!statusDiv) return;
    
    if (status === 'UNLOCKED') {
        statusDiv.className = 'engine-status unlocked';
        statusDiv.innerHTML = `
            <div class="engine-icon"><i class="fas fa-unlock-alt"></i></div>
            <div class="engine-text">ENGINE UNLOCKED</div>
        `;
        showNotification('Engine Unlocked', 'Vehicle engine has been unlocked', 'success');
    } else {
        statusDiv.className = 'engine-status locked';
        statusDiv.innerHTML = `
            <div class="engine-icon"><i class="fas fa-lock"></i></div>
            <div class="engine-text">ENGINE LOCKED</div>
        `;
        showNotification('Engine Locked', 'Vehicle engine has been locked', 'info');
    }
}

// Make sendCommand globally available
window.sendCommand = async function(command) {
    console.log('Sending command:', command);
    try {
        const response = await fetch('/api/vehicle/send-command/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ command: command })
        });
        
        if (response.ok) {
            showNotification('Command Sent', `${command} command sent successfully`, 'success');
            updateEngineStatus(command === 'UNLOCK' ? 'UNLOCKED' : 'LOCKED');
        } else {
            const error = await response.json();
            showNotification('Error', error.error || 'Failed to send command', 'error');
        }
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error', 'Network error', 'error');
    }
};

// Make captureAndAuthenticate globally available
window.captureAndAuthenticate = async function() {
    console.log('Capturing face for authentication...');
    const video = document.getElementById('video');
    const canvas = document.getElementById('canvas');
    const authMessage = document.getElementById('authMessage');
    
    if (!video || !canvas) {
        console.error('Video or canvas element not found');
        return;
    }
    
    // Check if video is ready
    if (!video.videoWidth || !video.videoHeight) {
        if (authMessage) {
            authMessage.innerHTML = '<span style="color: #dc3545;">Camera not ready. Please wait...</span>';
        }
        setTimeout(() => {
            if (authMessage) authMessage.innerHTML = '';
        }, 3000);
        return;
    }
    
    const context = canvas.getContext('2d');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    context.drawImage(video, 0, 0, canvas.width, canvas.height);
    
    const imageData = canvas.toDataURL('image/jpeg', 0.8);
    
    if (authMessage) {
        authMessage.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Authenticating...';
        authMessage.style.color = '#667eea';
    }
    
    try {
        const response = await fetch('/api/face-auth/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ face_image: imageData })
        });
        
        const result = await response.json();
        
        if (response.ok && result.success) {
            if (authMessage) {
                authMessage.innerHTML = '<i class="fas fa-check-circle"></i> Face recognized! Engine unlocking...';
                authMessage.style.color = '#28a745';
            }
            updateEngineStatus('UNLOCKED');
            showNotification('Authentication Success', 'Face recognized - Engine unlocked', 'success');
        } else {
            if (authMessage) {
                authMessage.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Face not recognized - Access denied';
                authMessage.style.color = '#dc3545';
            }
            showNotification('Authentication Failed', 'Face not recognized - Access denied', 'error');
        }
    } catch (error) {
        console.error('Auth error:', error);
        if (authMessage) {
            authMessage.innerHTML = '<i class="fas fa-exclamation-triangle"></i> Network error';
            authMessage.style.color = '#dc3545';
        }
        showNotification('Error', 'Authentication failed', 'error');
    }
    
    setTimeout(() => {
        if (authMessage) authMessage.innerHTML = '';
    }, 3000);
};

// Load alerts
async function loadAlerts() {
    try {
        const response = await fetch('/alerts/alerts/');
        if (response.ok) {
            const alerts = await response.json();
            const alertsList = document.getElementById('alertsList');
            
            if (!alertsList) return;
            
            if (alerts.length === 0) {
                alertsList.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;"><i class="fas fa-check-circle"></i> No alerts</div>';
                return;
            }
            
            alertsList.innerHTML = alerts.map(alert => `
                <div class="alert-item ${alert.severity.toLowerCase()}">
                    <div class="alert-title">
                        <i class="fas ${getAlertIcon(alert.severity)}"></i>
                        ${alert.title}
                    </div>
                    <div>${alert.description}</div>
                    <div class="alert-time">
                        <i class="far fa-clock"></i> ${new Date(alert.timestamp).toLocaleString()}
                    </div>
                </div>
            `).join('');
        }
    } catch (error) {
        console.error('Error loading alerts:', error);
    }
}

function getAlertIcon(severity) {
    switch(severity) {
        case 'HIGH': return 'fa-exclamation-triangle';
        case 'CRITICAL': return 'fa-skull-crossbones';
        default: return 'fa-info-circle';
    }
}

function showNotification(title, message, type) {
    const notification = document.createElement('div');
    const bgColor = type === 'success' ? '#28a745' : type === 'error' ? '#dc3545' : '#17a2b8';
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${bgColor};
        color: white;
        padding: 15px 20px;
        border-radius: 10px;
        z-index: 10000;
        animation: slideIn 0.3s ease-out;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        min-width: 250px;
    `;
    notification.innerHTML = `<strong>${title}</strong><br><small>${message}</small>`;
    document.body.appendChild(notification);
    
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Initialize webcam
async function initWebcam() {
    const video = document.getElementById('video');
    const authMessage = document.getElementById('authMessage');
    
    if (!video) {
        console.error('Video element not found');
        return;
    }
    
    if (authMessage) {
        authMessage.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Requesting camera access...';
        authMessage.style.color = '#667eea';
    }
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ 
            video: { 
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: 'user'
            } 
        });
        
        video.srcObject = stream;
        mediaStream = stream;
        
        video.onloadedmetadata = () => {
            video.play();
            console.log('Camera ready');
            if (authMessage) {
                authMessage.innerHTML = '<span style="color: #28a745;">✓ Camera ready! Click "SCAN FACE" to authenticate.</span>';
                setTimeout(() => {
                    if (authMessage && authMessage.innerHTML.includes('Camera ready')) {
                        authMessage.innerHTML = '';
                    }
                }, 3000);
            }
        };
    } catch (error) {
        console.error('Webcam error:', error);
        let errorMsg = 'Camera access denied. ';
        if (error.name === 'NotAllowedError') {
            errorMsg += 'Please allow camera access in your browser settings.';
        } else if (error.name === 'NotFoundError') {
            errorMsg += 'No camera found on this device.';
        } else {
            errorMsg += 'Please check your camera.';
        }
        if (authMessage) {
            authMessage.innerHTML = `<span style="color: #dc3545;">❌ ${errorMsg}</span>`;
        }
        showNotification('Camera Error', errorMsg, 'error');
    }
}

// Add CSS animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from { transform: translateX(100%); opacity: 0; }
        to { transform: translateX(0); opacity: 1; }
    }
    @keyframes slideOut {
        from { transform: translateX(0); opacity: 1; }
        to { transform: translateX(100%); opacity: 0; }
    }
`;
document.head.appendChild(style);

// Clean up camera when page closes
window.addEventListener('beforeunload', function() {
    if (mediaStream) {
        mediaStream.getTracks().forEach(track => track.stop());
    }
});