// Dashboard JavaScript functionality
class CDNDashboard {
    constructor() {
        this.charts = {};
        this.refreshInterval = null;
        this.init();
    }
    
    init() {
        this.setupEventListeners();
        this.startAutoRefresh();
    }
    
    setupEventListeners() {
        // Refresh button
        const refreshBtn = document.querySelector('[onclick="refreshDashboard()"]');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => this.refreshDashboard());
        }
        
        // Server card interactions
        document.addEventListener('click', (e) => {
            if (e.target.closest('.server-card')) {
                const serverId = e.target.closest('.server-card').dataset.serverId;
                if (serverId) {
                    this.showServerDetails(serverId);
                }
            }
        });
        
        // Auto-acknowledge alerts after 5 minutes
        this.setupAutoAcknowledge();
    }
    
    startAutoRefresh() {
        // Refresh every 30 seconds
        console.log('Starting auto-refresh every 30 seconds');
        this.refreshInterval = setInterval(() => {
            console.log('Auto-refreshing dashboard...');
            this.refreshDashboard();
        }, 30000);
    }
    
    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }
    
    async refreshDashboard() {
        try {
            // Show loading state
            this.showLoading(true);
            
            // Fetch updated data
            const [statsData, serversData, alertsData] = await Promise.all([
                this.fetchData('/api/dashboard/stats'),
                this.fetchData('/api/servers'),
                this.fetchData('/api/alerts')
            ]);
            
            // Update dashboard components
            this.updateStats(statsData);
            this.updateServerGrid(serversData);
            this.updateAlerts(alertsData);
            this.updateCharts(statsData, serversData);
            
        } catch (error) {
            console.error('Error refreshing dashboard:', error);
            this.showError('Failed to refresh dashboard data');
        } finally {
            this.showLoading(false);
        }
    }
    
    async fetchData(url) {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    }
    
    updateStats(data) {
        console.log('Updating stats with data:', data);
        const elements = {
            'total-servers': data.total_servers,
            'online-servers': data.status_counts.up || 0,
            'offline-servers': data.status_counts.down || 0,
            'total-connections': data.total_connections,
            'total-streams': data.total_streams || 0
        };
        
        Object.entries(elements).forEach(([id, value]) => {
            const element = document.getElementById(id);
            if (element) {
                console.log(`Updating ${id} from ${element.textContent} to ${value}`);
                this.animateNumber(element, parseInt(element.textContent) || 0, value);
            }
        });
        
        // Update bandwidth stats with decimal values
        const totalBandwidthUpElement = document.getElementById('total-bandwidth-up');
        if (totalBandwidthUpElement && data.total_bandwidth_up !== undefined) {
            const oldUp = totalBandwidthUpElement.textContent;
            const newUp = data.total_bandwidth_up.toFixed(1) + ' Mbps';
            console.log(`Updating bandwidth up from ${oldUp} to ${newUp}`);
            totalBandwidthUpElement.textContent = newUp;
        }
        
        const totalBandwidthDownElement = document.getElementById('total-bandwidth-down');
        if (totalBandwidthDownElement && data.total_bandwidth_down !== undefined) {
            const oldDown = totalBandwidthDownElement.textContent;
            const newDown = data.total_bandwidth_down.toFixed(1) + ' Mbps';
            console.log(`Updating bandwidth down from ${oldDown} to ${newDown}`);
            totalBandwidthDownElement.textContent = newDown;
        }
    }
    
    updateServerGrid(servers) {
        const grid = document.getElementById('servers-grid');
        if (!grid) return;
        
        servers.forEach(server => {
            const serverCard = document.querySelector(`[data-server-id="${server.id}"]`);
            if (serverCard) {
                this.updateServerCard(serverCard, server);
            }
        });
    }
    
    updateServerCard(card, server) {
        // Update status badge
        const statusBadge = card.querySelector('.badge');
        if (statusBadge) {
            const statusClass = this.getStatusClass(server.status);
            statusBadge.className = `badge ${statusClass}`;
            statusBadge.textContent = server.status.toUpperCase();
        }
        
        // Update metrics
        const connectionsMetric = card.querySelector('[data-metric="connections"]');
        if (connectionsMetric && server.latest_metric) {
            const connections = server.latest_metric.active_connections || 0;
            this.animateNumber(connectionsMetric, 
                parseInt(connectionsMetric.textContent) || 0, connections);
        }
        
        const responseTimeMetric = card.querySelector('[data-metric="response_time"]');
        if (responseTimeMetric && server.latest_metric && server.latest_metric.response_time) {
            const responseTime = Math.round(server.latest_metric.response_time);
            responseTimeMetric.textContent = responseTime + 'ms';
            
            // Add color coding based on response time
            responseTimeMetric.className = this.getResponseTimeClass(responseTime);
        }
        
        // Update stream count metric
        const streamCountMetric = card.querySelector('[data-metric="stream_count"]');
        if (streamCountMetric && server.latest_metric) {
            const streamCount = server.latest_metric.stream_count || 0;
            streamCountMetric.textContent = streamCount;
        }
        
        // Update bandwidth metrics
        const bandwidthInMetric = card.querySelector('[data-metric="bandwidth_in"]');
        if (bandwidthInMetric && server.latest_metric) {
            const bandwidthIn = server.latest_metric.bandwidth_in || 0;
            bandwidthInMetric.textContent = bandwidthIn.toFixed(2);
        }
        
        const bandwidthOutMetric = card.querySelector('[data-metric="bandwidth_out"]');
        if (bandwidthOutMetric && server.latest_metric) {
            const bandwidthOut = server.latest_metric.bandwidth_out || 0;
            bandwidthOutMetric.textContent = bandwidthOut.toFixed(2);
        }
    }
    
    updateAlerts(alerts) {
        const alertsList = document.getElementById('alerts-list');
        if (!alertsList) return;
        
        if (alerts.length === 0) {
            alertsList.innerHTML = `
                <div class="text-center py-3">
                    <i class="fas fa-check-circle fa-2x text-success mb-2"></i>
                    <p class="text-muted mb-0">No active alerts</p>
                </div>
            `;
            return;
        }
        
        alertsList.innerHTML = alerts.map(alert => `
            <div class="list-group-item d-flex justify-content-between align-items-start">
                <div class="ms-2 me-auto">
                    <div class="fw-bold">
                        <span class="badge ${this.getSeverityClass(alert.severity)} me-2">
                            ${alert.severity.toUpperCase()}
                        </span>
                        ${this.escapeHtml(alert.message)}
                    </div>
                    <small class="text-muted">
                        ${this.formatDate(alert.created_at)} • ${alert.server_hostname || 'Unknown Server'}
                    </small>
                </div>
                <button class="btn btn-sm btn-outline-secondary" onclick="acknowledgeAlert(${alert.id})">
                    <i class="fas fa-check me-1"></i>Acknowledge
                </button>
            </div>
        `).join('');
    }
    
    updateCharts(statsData, serversData) {
        // Update status chart
        if (window.statusChart) {
            window.statusChart.data.datasets[0].data = [
                statsData.status_counts.up || 0,
                statsData.status_counts.down || 0,
                statsData.status_counts.unknown || 0
            ];
            window.statusChart.update('none'); // No animation for real-time updates
        }
        
        // Update connections chart
        if (window.connectionsChart) {
            const serverNames = serversData.map(s => s.hostname);
            const connectionCounts = serversData.map(s => 
                s.latest_metric ? s.latest_metric.active_connections || 0 : 0
            );
            
            window.connectionsChart.data.labels = serverNames;
            window.connectionsChart.data.datasets[0].data = connectionCounts;
            window.connectionsChart.update('none');
        }
        
        // Update bandwidth chart
        if (window.bandwidthChart) {
            const serverNames = serversData.map(s => s.hostname);
            const bandwidthIn = serversData.map(s => 
                s.latest_metric ? s.latest_metric.bandwidth_in || 0 : 0
            );
            const bandwidthOut = serversData.map(s => 
                s.latest_metric ? s.latest_metric.bandwidth_out || 0 : 0
            );
            
            window.bandwidthChart.data.labels = serverNames;
            window.bandwidthChart.data.datasets[0].data = bandwidthIn;
            window.bandwidthChart.data.datasets[1].data = bandwidthOut;
            window.bandwidthChart.update('none');
        }
        

    }
    
    async showServerDetails(serverId) {
        try {
            const [metrics, streams, server] = await Promise.all([
                this.fetchData(`/api/servers/${serverId}/metrics`),
                this.fetchData(`/api/servers/${serverId}/streams`),
                this.fetchData(`/api/servers`).then(servers => 
                    servers.find(s => s.id == serverId)
                )
            ]);
            
            if (!server) {
                throw new Error('Server not found');
            }
            
            this.displayServerModal(server, metrics, streams);
            
        } catch (error) {
            console.error('Error loading server details:', error);
            this.showError('Failed to load server details');
        }
    }
    
    displayServerModal(server, metrics, streams) {
        const modalHtml = `
            <div class="modal fade" id="serverModal" tabindex="-1">
                <div class="modal-dialog modal-xl">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">
                                <i class="fas fa-server me-2"></i>
                                ${this.escapeHtml(server.hostname)}
                                <span class="badge ${this.getStatusClass(server.status)} ms-2">
                                    ${server.status.toUpperCase()}
                                </span>
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            ${this.generateServerDetailsContent(server, metrics, streams)}
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal
        const existingModal = document.getElementById('serverModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add new modal
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        // Show modal
        const modal = new bootstrap.Modal(document.getElementById('serverModal'));
        modal.show();
        
        // Create chart if metrics available
        if (metrics.length > 0) {
            setTimeout(() => this.createServerMetricsChart(metrics), 100);
        }
    }
    
    generateServerDetailsContent(server, metrics) {
        const latestMetric = metrics[0];
        
        return `
            <div class="row mb-4">
                <div class="col-md-6">
                    <h6>Server Information</h6>
                    <table class="table table-sm">
                        <tr><td><strong>Role:</strong></td><td><span class="badge ${this.getRoleClass(server.role)}">${server.role.toUpperCase()}</span></td></tr>
                        <tr><td><strong>IP Address:</strong></td><td><code>${server.ip_address}:${server.port}</code></td></tr>
                        <tr><td><strong>API Type:</strong></td><td>${server.api_type ? server.api_type.toUpperCase() : 'N/A'}</td></tr>
                        <tr><td><strong>Last Updated:</strong></td><td>${this.formatDate(server.updated_at)}</td></tr>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Current Metrics</h6>
                    ${latestMetric ? `
                        <table class="table table-sm">
                            <tr><td><strong>Connections:</strong></td><td>${latestMetric.active_connections || 0}</td></tr>
                            <tr><td><strong>HLS Streams:</strong></td><td>${latestMetric.hls_connections || 0}</td></tr>
                            <tr><td><strong>Response Time:</strong></td><td>${latestMetric.response_time ? Math.round(latestMetric.response_time) + 'ms' : 'N/A'}</td></tr>
                            <tr><td><strong>CPU Usage:</strong></td><td>${latestMetric.cpu_usage ? latestMetric.cpu_usage.toFixed(1) + '%' : 'N/A'}</td></tr>
                            <tr><td><strong>Memory Usage:</strong></td><td>${latestMetric.memory_usage ? latestMetric.memory_usage.toFixed(1) + '%' : 'N/A'}</td></tr>
                        </table>
                    ` : '<p class="text-muted">No metrics available</p>'}
                </div>
            </div>
            ${metrics.length > 0 ? `
                <div class="row">
                    <div class="col">
                        <h6>Connection History (Last 24 Hours)</h6>
                        <canvas id="serverMetricsChart" style="max-height: 300px;"></canvas>
                    </div>
                </div>
            ` : ''}
        `;
    }
    
    createServerMetricsChart(metrics) {
        const ctx = document.getElementById('serverMetricsChart');
        if (!ctx) return;
        
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: metrics.slice(-48).reverse().map(m => 
                    new Date(m.timestamp).toLocaleTimeString()
                ),
                datasets: [{
                    label: 'Active Connections',
                    data: metrics.slice(-48).reverse().map(m => m.active_connections || 0),
                    borderColor: '#007bff',
                    backgroundColor: 'rgba(0, 123, 255, 0.1)',
                    fill: true,
                    tension: 0.4
                }, {
                    label: 'Response Time (ms)',
                    data: metrics.slice(-48).reverse().map(m => m.response_time || 0),
                    borderColor: '#28a745',
                    backgroundColor: 'rgba(40, 167, 69, 0.1)',
                    fill: false,
                    yAxisID: 'y1',
                    tension: 0.4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false,
                },
                scales: {
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Connections'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        title: {
                            display: true,
                            text: 'Response Time (ms)'
                        },
                        grid: {
                            drawOnChartArea: false,
                        },
                    }
                },
                plugins: {
                    legend: {
                        position: 'top',
                    }
                }
            }
        });
    }
    
    setupAutoAcknowledge() {
        // Auto-acknowledge old alerts after 30 minutes
        setInterval(() => {
            const alerts = document.querySelectorAll('.list-group-item [onclick*="acknowledgeAlert"]');
            alerts.forEach(button => {
                const alertElement = button.closest('.list-group-item');
                const timeElement = alertElement.querySelector('.text-muted');
                if (timeElement) {
                    const timeText = timeElement.textContent;
                    const alertTime = this.parseAlertTime(timeText);
                    const now = new Date();
                    const diffMinutes = (now - alertTime) / (1000 * 60);
                    
                    if (diffMinutes > 30) {
                        // Auto-acknowledge old alerts
                        const alertId = this.extractAlertId(button.getAttribute('onclick'));
                        if (alertId) {
                            this.acknowledgeAlert(alertId, true);
                        }
                    }
                }
            });
        }, 5 * 60 * 1000); // Check every 5 minutes
    }
    
    async acknowledgeAlert(alertId, silent = false) {
        try {
            const response = await fetch(`/api/alerts/${alertId}/acknowledge`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Remove the alert from the list
                const alertElement = document.querySelector(`[onclick="acknowledgeAlert(${alertId})"]`)
                    ?.closest('.list-group-item');
                if (alertElement) {
                    alertElement.remove();
                }
                
                // Check if no alerts remain
                const alertsList = document.getElementById('alerts-list');
                if (alertsList && alertsList.children.length === 0) {
                    alertsList.innerHTML = `
                        <div class="text-center py-3">
                            <i class="fas fa-check-circle fa-2x text-success mb-2"></i>
                            <p class="text-muted mb-0">No active alerts</p>
                        </div>
                    `;
                }
                
                if (!silent) {
                    this.showSuccess('Alert acknowledged successfully');
                }
            } else {
                throw new Error(data.error || 'Failed to acknowledge alert');
            }
        } catch (error) {
            console.error('Error acknowledging alert:', error);
            if (!silent) {
                this.showError('Failed to acknowledge alert');
            }
        }
    }
    
    // Utility methods
    animateNumber(element, from, to) {
        const duration = 500;
        const steps = 20;
        const stepValue = (to - from) / steps;
        const stepDuration = duration / steps;
        
        let current = from;
        let step = 0;
        
        const timer = setInterval(() => {
            current += stepValue;
            step++;
            
            if (step >= steps) {
                current = to;
                clearInterval(timer);
            }
            
            element.textContent = Math.round(current);
        }, stepDuration);
    }
    
    getStatusClass(status) {
        const classes = {
            'up': 'bg-success',
            'down': 'bg-danger',
            'unknown': 'bg-secondary'
        };
        return classes[status] || 'bg-secondary';
    }
    
    getRoleClass(role) {
        const classes = {
            'origin': 'bg-primary',
            'edge': 'bg-success',
            'load-balancer': 'bg-warning'
        };
        return classes[role] || 'bg-secondary';
    }
    
    getSeverityClass(severity) {
        const classes = {
            'critical': 'bg-danger',
            'warning': 'bg-warning',
            'info': 'bg-info',
            'error': 'bg-danger'
        };
        return classes[severity] || 'bg-secondary';
    }
    
    getResponseTimeClass(responseTime) {
        if (responseTime < 1000) return 'text-success';
        if (responseTime < 3000) return 'text-warning';
        return 'text-danger';
    }
    
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    formatDate(dateString) {
        if (!dateString) return 'Never';
        const date = new Date(dateString);
        return date.toLocaleString();
    }
    
    parseAlertTime(timeText) {
        // Extract timestamp from alert time text
        const match = timeText.match(/(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})/);
        return match ? new Date(match[1]) : new Date();
    }
    
    extractAlertId(onclickText) {
        const match = onclickText.match(/acknowledgeAlert\((\d+)\)/);
        return match ? parseInt(match[1]) : null;
    }
    
    showLoading(show) {
        const refreshBtn = document.querySelector('[onclick="refreshDashboard()"]');
        if (refreshBtn) {
            const icon = refreshBtn.querySelector('i');
            if (show) {
                refreshBtn.disabled = true;
                icon.className = 'fas fa-spinner fa-spin me-1';
            } else {
                refreshBtn.disabled = false;
                icon.className = 'fas fa-sync-alt me-1';
            }
        }
    }
    
    showSuccess(message) {
        this.showToast(message, 'success');
    }
    
    showError(message) {
        this.showToast(message, 'danger');
    }
    
    showToast(message, type) {
        const toastHtml = `
            <div class="toast align-items-center text-white bg-${type} border-0" role="alert">
                <div class="d-flex">
                    <div class="toast-body">
                        ${this.escapeHtml(message)}
                    </div>
                    <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
                </div>
            </div>
        `;
        
        let toastContainer = document.getElementById('toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.id = 'toast-container';
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1050';
            document.body.appendChild(toastContainer);
        }
        
        toastContainer.insertAdjacentHTML('beforeend', toastHtml);
        
        const toastElement = toastContainer.lastElementChild;
        const toast = new bootstrap.Toast(toastElement, { delay: 3000 });
        toast.show();
        
        // Remove toast element after it's hidden
        toastElement.addEventListener('hidden.bs.toast', () => {
            toastElement.remove();
        });
    }
}

// Global functions for backward compatibility
function refreshDashboard() {
    if (window.dashboard) {
        window.dashboard.refreshDashboard();
    }
}

function acknowledgeAlert(alertId) {
    if (window.dashboard) {
        window.dashboard.acknowledgeAlert(alertId);
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.dashboard = new CDNDashboard();
});

// Clean up on page unload
window.addEventListener('beforeunload', function() {
    if (window.dashboard) {
        window.dashboard.stopAutoRefresh();
    }
});
