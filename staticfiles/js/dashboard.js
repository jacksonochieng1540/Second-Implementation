// Dashboard JavaScript - Modular code
const VehicleTracker = {
    map: null,
    vehicleMarker: null,
    pathPoints: [],
    pathLine: null,
    ws: null,
    currentLocation: { lat: 40.7128, lng: -74.0060 },
    
    init: function() {
        this.initMap();
        this.initWebSocket();
        this.initWebcam();
        this.loadAlerts();
        this.setupEventListeners();
    },
    
    initMap: function() {
        this.map = L.map('map').setView([40.7128, -74.0060], 15);
        
        L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/attributions">CARTO</a>',
            subdomains: 'abcd',
            maxZoom: 19
        }).addTo(this.map);
        
        this.carIcon = L.divIcon({
            html: '<div style="font-size: 40px;"><i class="fas fa-car-side" style="color: #667eea; filter: drop-shadow(2px 2px 4px rgba(0,0,0,0.3));"></i></div>',
            iconSize: [40, 40],
            className: 'custom-car-icon'
        });
    },
    
    initWebSocket: function() {
        const protocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
        const wsUrl = `${protocol}${window.location.host}/ws/vehicle/`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateConnectionStatus(true);
            this.ws.send(JSON.stringify({ type: 'GET_HISTORY' }));
        };
        
        this.ws.onmessage = (e) => {
            const data = JSON.parse(e.data);
            this.handleWebSocketMessage(data);
        };
        
        this.ws.onerror = () => {
            this.updateConnectionStatus(false);
        };
        
        this.ws.onclose = () => {
            this.updateConnectionStatus(false);
            setTimeout(() => this.initWebSocket(), 3000);
        };
    },
    
    handleWebSocketMessage: function(data) {
        switch(data.type) {
            case 'LOCATION_UPDATE':
                this.updateVehiclePosition(data.data);
                break;
            case 'LOCATION_HISTORY':
                this.loadLocationHistory(data.data);
                break;
            case 'COMMAND_UPDATE':
                this.handleCommandUpdate(data.data);
                break;
        }
    },
    
    updateVehiclePosition: function(locationData) {
        const lat = parseFloat(locationData.latitude);
        const lng = parseFloat(locationData.longitude);
        
        this.currentLocation = { lat, lng };
        
        if (this.vehicleMarker) {
            this.vehicleMarker.setLatLng([lat, lng]);
        } else {
            this.vehicleMarker = L.marker([lat, lng], { icon: this.carIcon }).addTo(this.map);
        }
        
        this.map.panTo([lat, lng]);
        this.pathPoints.push([lat, lng]);
        if (this.pathPoints.length > 50) this.pathPoints.shift();
        this.updatePathLine();
        
        // Update UI
        document.getElementById('speedValue').textContent = locationData.speed || 0;
        document.getElementById('headingValue').textContent = locationData.heading || 0;
    },
    
    updatePathLine: function() {
        if (this.pathLine) this.map.removeLayer(this.pathLine);
        if (this.pathPoints.length > 1) {
            this.pathLine = L.polyline(this.pathPoints, {
                color: '#667eea',
                weight: 3,
                opacity: 0.8
            }).addTo(this.map);
        }
    },
    
    loadLocationHistory: function(historyData) {
        this.pathPoints = historyData.map(h => [parseFloat(h.latitude), parseFloat(h.longitude)]);
        if (this.pathPoints.length > 0) {
            const lastPoint = this.pathPoints[this.pathPoints.length - 1];
            if (this.vehicleMarker) {
                this.vehicleMarker.setLatLng(lastPoint);
            } else {
                this.vehicleMarker = L.marker(lastPoint, { icon: this.carIcon }).addTo(this.map);
            }
            this.map.setView(lastPoint, 15);
            this.updatePathLine();
        }
    },
    
    handleCommandUpdate: function(commandData) {
        const status = commandData.command === 'UNLOCK' ? 'UNLOCKED' : 'LOCKED';
        this.updateEngineStatus(status);
    },
    
    updateEngineStatus: function(status) {
        const statusDiv = document.getElementById('engineStatus');
        if (status === 'UNLOCKED') {
            statusDiv.className = 'engine-status unlocked';
            statusDiv.innerHTML = '<div class="engine-icon"><i class="fas fa-unlock-alt"></i></div><div class="engine-text">ENGINE UNLOCKED</div>';
        } else {
            statusDiv.className = 'engine-status locked';
            statusDiv.innerHTML = '<div class="engine-icon"><i class="fas fa-lock"></i></div><div class="engine-text">ENGINE LOCKED</div>';
        }
    },
    
    updateConnectionStatus: function(isConnected) {
        const statusDiv = document.getElementById('connectionStatus');
        if (isConnected) {
            statusDiv.innerHTML = '<span class="status-dot online"></span> Connected to server';
        } else {
            statusDiv.innerHTML = '<span class="status-dot offline"></span> Disconnected - Reconnecting...';
        }
    },
    
    initWebcam: async function() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true });
            document.getElementById('video').srcObject = stream;
        } catch (error) {
            console.error('Webcam error:', error);
        }
    },
    
    loadAlerts: async function() {
        try {
            const response = await fetch('/alerts/alerts/');
            if (response.ok) {
                const alerts = await response.json();
                this.displayAlerts(alerts);
            }
        } catch (error) {
            console.error('Error loading alerts:', error);
        }
    },
    
    displayAlerts: function(alerts) {
        const alertsList = document.getElementById('alertsList');
        if (alerts.length === 0) {
            alertsList.innerHTML = '<div style="text-align: center; color: #999; padding: 20px;"><i class="fas fa-check-circle"></i> No alerts</div>';
            return;
        }
        
        alertsList.innerHTML = alerts.map(alert => `
            <div class="alert-item ${alert.severity.toLowerCase()}">
                <div class="alert-title"><i class="fas ${this.getAlertIcon(alert.severity)}"></i> ${alert.title}</div>
                <div>${alert.description}</div>
                <div class="alert-time"><i class="far fa-clock"></i> ${new Date(alert.timestamp).toLocaleString()}</div>
            </div>
        `).join('');
    },
    
    getAlertIcon: function(severity) {
        const icons = {
            'HIGH': 'fa-exclamation-triangle',
            'CRITICAL': 'fa-skull-crossbones',
            'MEDIUM': 'fa-exclamation-circle',
            'LOW': 'fa-info-circle'
        };
        return icons[severity] || 'fa-bell';
    },
    
    setupEventListeners: function() {
        document.getElementById('unlockBtn')?.addEventListener('click', () => this.sendCommand('UNLOCK'));
        document.getElementById('lockBtn')?.addEventListener('click', () => this.sendCommand('LOCK'));
        document.getElementById('captureBtn')?.addEventListener('click', () => this.captureAndAuthenticate());
    },
    
    sendCommand: async function(command) {
        try {
            const response = await fetch('/api/vehicle/send-command/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ command: command })
            });
            
            if (response.ok) {
                this.showNotification('Success', `${command} command sent`, 'success');
                this.updateEngineStatus(command === 'UNLOCK' ? 'UNLOCKED' : 'LOCKED');
            }
        } catch (error) {
            this.showNotification('Error', 'Failed to send command', 'error');
        }
    },
    
    captureAndAuthenticate: async function() {
        const video = document.getElementById('video');
        const canvas = document.getElementById('canvas');
        const context = canvas.getContext('2d');
        
        canvas.width = video.videoWidth;
        canvas.height = video.videoHeight;
        context.drawImage(video, 0, 0, canvas.width, canvas.height);
        
        const imageData = canvas.toDataURL('image/jpeg', 0.8);
        
        try {
            const response = await fetch('/api/face-auth/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ face_image: imageData })
            });
            
            const result = await response.json();
            
            if (response.ok && result.success) {
                this.showNotification('Authentication Success', 'Face recognized - Engine unlocked', 'success');
                this.updateEngineStatus('UNLOCKED');
            } else {
                this.showNotification('Authentication Failed', 'Face not recognized', 'error');
            }
        } catch (error) {
            this.showNotification('Error', 'Authentication failed', 'error');
        }
    },
    
    showNotification: function(title, message, type) {
        const notification = document.createElement('div');
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#28a745' : '#dc3545'};
            color: white;
            padding: 15px 20px;
            border-radius: 10px;
            z-index: 10000;
            animation: slideIn 0.3s ease-out;
            box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        `;
        notification.innerHTML = `<strong>${title}</strong><br><small>${message}</small>`;
        document.body.appendChild(notification);
        
        setTimeout(() => notification.remove(), 3000);
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => VehicleTracker.init());