/**
 * Mobile Dashboard JavaScript
 * Handles mobile-specific dashboard functionality
 */

class MobileDashboard {
    constructor() {
        this.refreshInterval = null;
        this.refreshRate = 30000; // 30 seconds
        this.isRefreshing = false;
    }

    init() {
        this.startAutoRefresh();
        this.setupEventListeners();
        this.refreshData();
    }

    setupEventListeners() {
        // Pull to refresh simulation
        let startY = 0;
        let pullDistance = 0;
        const threshold = 100;

        document.addEventListener('touchstart', (e) => {
            if (window.scrollY === 0) {
                startY = e.touches[0].clientY;
            }
        });

        document.addEventListener('touchmove', (e) => {
            if (window.scrollY === 0 && startY > 0) {
                pullDistance = e.touches[0].clientY - startY;
                if (pullDistance > 0 && pullDistance < threshold) {
                    e.preventDefault();
                }
            }
        });

        document.addEventListener('touchend', () => {
            if (pullDistance > threshold && !this.isRefreshing) {
                this.refreshData();
            }
            startY = 0;
            pullDistance = 0;
        });

        // Handle navigation item clicks
        document.querySelectorAll('.nav-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!item.href || item.href.includes('#')) {
                    e.preventDefault();
                }
                
                // Update active state
                document.querySelectorAll('.nav-item').forEach(navItem => {
                    navItem.classList.remove('active');
                });
                item.classList.add('active');
            });
        });
    }

    startAutoRefresh() {
        this.refreshInterval = setInterval(() => {
            if (!this.isRefreshing) {
                this.refreshData();
            }
        }, this.refreshRate);
    }

    stopAutoRefresh() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    async refreshData() {
        if (this.isRefreshing) return;
        
        this.isRefreshing = true;
        const refreshBtn = document.querySelector('.btn-refresh');
        
        try {
            // Add spinning animation
            if (refreshBtn) {
                refreshBtn.classList.add('spinning');
            }

            // Fetch dashboard stats
            const [statsResponse, serversResponse, alertsResponse] = await Promise.all([
                this.fetchData('/api/dashboard/stats'),
                this.fetchData('/api/servers'),
                this.fetchData('/api/alerts')
            ]);

            if (statsResponse) {
                this.updateStats(statsResponse);
            }

            if (serversResponse) {
                this.updateServers(serversResponse);
            }

            if (alertsResponse) {
                this.updateAlerts(alertsResponse);
            }

        } catch (error) {
            console.error('Error refreshing mobile dashboard:', error);
            this.showToast('Failed to refresh data', 'error');
        } finally {
            this.isRefreshing = false;
            if (refreshBtn) {
                refreshBtn.classList.remove('spinning');
            }
        }
    }

    async fetchData(url) {
        try {
            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`Error fetching ${url}:`, error);
            return null;
        }
    }

    updateStats(data) {
        // Update overview stats
        this.updateElement('mobile-total-servers', data.total_servers);
        this.updateElement('mobile-online-servers', data.status_counts?.up || 0);
        this.updateElement('mobile-total-connections', data.total_connections);
        this.updateElement('mobile-total-streams', data.total_streams || 0);

        // Update bandwidth
        const bandwidthDown = document.getElementById('mobile-bandwidth-down');
        const bandwidthUp = document.getElementById('mobile-bandwidth-up');
        
        if (bandwidthDown) {
            bandwidthDown.textContent = `${(data.total_bandwidth_down || 0).toFixed(1)} Mbps`;
        }
        
        if (bandwidthUp) {
            bandwidthUp.textContent = `${(data.total_bandwidth_up || 0).toFixed(1)} Mbps`;
        }
    }

    updateServers(servers) {
        servers.forEach(server => {
            const serverCard = document.querySelector(`[data-server-id="${server.id}"]`);
            if (serverCard) {
                this.updateServerCard(serverCard, server);
            }
        });
    }

    updateServerCard(card, server) {
        // Update server status
        const statusElement = card.querySelector('.server-status');
        if (statusElement) {
            statusElement.className = `server-status status-${server.status}`;
            statusElement.innerHTML = `<i class="fas fa-${this.getStatusIcon(server.status)}"></i> ${server.status.toUpperCase()}`;
        }

        // Update metrics
        const metrics = server.latest_metrics || {};
        this.updateCardMetric(card, 'connections', metrics.active_connections || 0);
        this.updateCardMetric(card, 'stream_count', metrics.stream_count || 0);
        this.updateCardMetric(card, 'bandwidth_in', (metrics.bandwidth_in || 0).toFixed(2));
        this.updateCardMetric(card, 'bandwidth_out', (metrics.bandwidth_out || 0).toFixed(2));
    }

    updateCardMetric(card, metricName, value) {
        const element = card.querySelector(`[data-metric="${metricName}"]`);
        if (element) {
            element.textContent = value;
        }
    }

    updateAlerts(alerts) {
        const alertsList = document.getElementById('mobile-alerts-list');
        const alertsSection = document.querySelector('.alerts-section');
        
        if (!alerts || alerts.length === 0) {
            if (alertsSection) {
                alertsSection.style.display = 'none';
            }
            return;
        }

        if (alertsSection) {
            alertsSection.style.display = 'block';
        }

        if (alertsList) {
            alertsList.innerHTML = alerts.map(alert => this.createAlertHTML(alert)).join('');
        }
    }

    createAlertHTML(alert) {
        const timeString = new Date(alert.created_at).toLocaleTimeString('en-US', {
            hour: '2-digit',
            minute: '2-digit'
        });

        return `
            <div class="mobile-alert alert-${alert.severity}">
                <div class="alert-icon">
                    <i class="fas fa-${this.getAlertIcon(alert.severity)}"></i>
                </div>
                <div class="alert-content">
                    <div class="alert-message">${this.escapeHtml(alert.message)}</div>
                    <div class="alert-time">${timeString}</div>
                </div>
                ${!alert.acknowledged ? `
                    <button class="alert-dismiss" onclick="acknowledgeMobileAlert(${alert.id})">
                        <i class="fas fa-check"></i>
                    </button>
                ` : ''}
            </div>
        `;
    }

    updateElement(id, value) {
        const element = document.getElementById(id);
        if (element) {
            if (element.textContent !== value.toString()) {
                element.textContent = value;
                this.animateValueChange(element);
            }
        }
    }

    animateValueChange(element) {
        element.style.transform = 'scale(1.1)';
        element.style.transition = 'transform 0.2s ease';
        
        setTimeout(() => {
            element.style.transform = 'scale(1)';
        }, 200);
    }

    getStatusIcon(status) {
        switch (status) {
            case 'up': return 'check-circle';
            case 'down': return 'times-circle';
            default: return 'question-circle';
        }
    }

    getAlertIcon(severity) {
        switch (severity) {
            case 'warning': return 'exclamation-triangle';
            case 'error':
            case 'critical': return 'times-circle';
            default: return 'info-circle';
        }
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showToast(message, type = 'info') {
        // Create toast element
        const toast = document.createElement('div');
        toast.className = `mobile-toast toast-${type}`;
        toast.textContent = message;
        
        // Style the toast
        Object.assign(toast.style, {
            position: 'fixed',
            top: '80px',
            left: '50%',
            transform: 'translateX(-50%)',
            background: type === 'error' ? '#dc2626' : '#059669',
            color: 'white',
            padding: '12px 24px',
            borderRadius: '8px',
            zIndex: '1001',
            fontSize: '14px',
            fontWeight: '500',
            boxShadow: '0 4px 12px rgba(0, 0, 0, 0.15)',
            opacity: '0',
            transition: 'opacity 0.3s ease'
        });

        document.body.appendChild(toast);

        // Animate in
        setTimeout(() => {
            toast.style.opacity = '1';
        }, 100);

        // Remove after 3 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.parentNode.removeChild(toast);
                }
            }, 300);
        }, 3000);
    }
}

// Global functions for mobile dashboard
function refreshMobileDashboard() {
    if (window.mobileDashboard) {
        window.mobileDashboard.refreshData();
    }
}

function showMobileServerDetails(serverId) {
    console.log('showMobileServerDetails called with serverId:', serverId);
    
    const modal = document.getElementById('mobile-server-modal');
    const modalTitle = document.getElementById('mobile-modal-title');
    const modalBody = document.getElementById('mobile-modal-body');

    if (!modal || !modalTitle || !modalBody) {
        console.error('Modal elements not found:', { modal, modalTitle, modalBody });
        return;
    }

    // Show loading state
    modalTitle.textContent = 'Loading...';
    modalBody.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin"></i></div>';
    modal.classList.add('show');
    
    console.log('Modal should now be visible');

    // Fetch server details
    Promise.all([
        fetch(`/api/servers/${serverId}/metrics`).then(r => {
            console.log('Metrics response status:', r.status);
            return r.json();
        }).catch(e => {
            console.error('Metrics fetch error:', e);
            return [];
        }),
        fetch(`/api/servers/${serverId}/streams`).then(r => {
            console.log('Streams response status:', r.status);
            return r.json();
        }).catch(e => {
            console.error('Streams fetch error:', e);
            return { streams: [] };
        }),
        fetch(`/api/servers`).then(r => {
            console.log('Servers response status:', r.status);
            return r.json();
        }).catch(e => {
            console.error('Servers fetch error:', e);
            return [];
        })
    ]).then(([metrics, streamsResponse, servers]) => {
        console.log('API responses:', { metrics, streamsResponse, servers });
        
        const server = servers.find(s => s.id === parseInt(serverId));
        if (server) {
            modalTitle.textContent = server.hostname;
            // Extract streams from the response object
            const streams = streamsResponse.streams || [];
            console.log('Found streams:', streams);
            modalBody.innerHTML = generateMobileServerDetails(server, metrics, streams);
        } else {
            console.error('Server not found with ID:', serverId);
            modalBody.innerHTML = '<div class="text-center p-4 text-danger">Server not found</div>';
        }
    }).catch(error => {
        console.error('Error loading server details:', error);
        modalBody.innerHTML = '<div class="text-center p-4 text-danger">Failed to load server details</div>';
    });
}

function generateMobileServerDetails(server, metrics, streams) {
    const latestMetric = metrics && metrics.length > 0 ? metrics[0] : {};
    
    return `
        <div class="mobile-server-details">
            <div class="detail-section">
                <h6 class="detail-title">Server Information</h6>
                <div class="detail-grid">
                    <div class="detail-item">
                        <span class="detail-label">Address:</span>
                        <span class="detail-value">${server.ip_address}:${server.port}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Role:</span>
                        <span class="detail-value">${server.role}</span>
                    </div>
                    <div class="detail-item">
                        <span class="detail-label">Status:</span>
                        <span class="detail-value status-${server.status}">${server.status.toUpperCase()}</span>
                    </div>
                </div>
            </div>

            <div class="detail-section">
                <h6 class="detail-title">Current Metrics</h6>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">${latestMetric.active_connections || 0}</div>
                        <div class="metric-label">Connections</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${latestMetric.stream_count || 0}</div>
                        <div class="metric-label">Streams</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${(latestMetric.bandwidth_in || 0).toFixed(1)} Mbps</div>
                        <div class="metric-label">Bandwidth In</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">${(latestMetric.bandwidth_out || 0).toFixed(1)} Mbps</div>
                        <div class="metric-label">Bandwidth Out</div>
                    </div>
                </div>
            </div>

            ${streams && streams.length > 0 ? `
                <div class="detail-section">
                    <h6 class="detail-title">Live Streams (${streams.length})</h6>
                    <div class="streams-list">
                        ${streams.sort((a, b) => (a.name || '').localeCompare(b.name || '')).map(stream => `
                            <div class="stream-item">
                                <div class="stream-header">
                                    <div class="stream-name">${stream.name || 'Unknown'}</div>
                                    <div class="stream-status ${stream.publish_active ? 'status-live' : 'status-offline'}">
                                        <i class="fas fa-${stream.publish_active ? 'broadcast-tower' : 'pause'}"></i>
                                        ${stream.publish_active ? 'LIVE' : 'OFFLINE'}
                                    </div>
                                </div>
                                
                                <div class="stream-metrics">
                                    <div class="stream-metric">
                                        <i class="fas fa-users"></i>
                                        <span>${stream.clients || 0} viewers</span>
                                    </div>
                                    <div class="stream-metric">
                                        <i class="fas fa-download"></i>
                                        <span>${((stream.bandwidth_in || 0) / 1000).toFixed(1)} Mbps</span>
                                    </div>
                                    <div class="stream-metric">
                                        <i class="fas fa-upload"></i>
                                        <span>${((stream.bandwidth_out || 0) / 1000).toFixed(1)} Mbps</span>
                                    </div>
                                </div>

                                ${stream.video || stream.audio ? `
                                    <div class="stream-details">
                                        ${stream.video ? `
                                            <div class="codec-info video-codec">
                                                <i class="fas fa-video"></i>
                                                <span>${stream.video.codec} ${stream.video.width}x${stream.video.height}</span>
                                                <small>${stream.video.profile} L${stream.video.level}</small>
                                            </div>
                                        ` : ''}
                                        ${stream.audio ? `
                                            <div class="codec-info audio-codec">
                                                <i class="fas fa-volume-up"></i>
                                                <span>${stream.audio.codec} ${stream.audio.sample_rate}Hz</span>
                                                <small>${stream.audio.channel}ch ${stream.audio.profile}</small>
                                            </div>
                                        ` : ''}
                                    </div>
                                ` : ''}

                                <div class="stream-stats">
                                    <div class="stat-item">
                                        <span class="stat-label">Frames:</span>
                                        <span class="stat-value">${(stream.frames || 0).toLocaleString()}</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">Uptime:</span>
                                        <span class="stat-value">${formatStreamUptime(stream.live_time)}</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">Data Sent:</span>
                                        <span class="stat-value">${formatBytes(stream.send_bytes || 0)}</span>
                                    </div>
                                    <div class="stat-item">
                                        <span class="stat-label">Data Received:</span>
                                        <span class="stat-value">${formatBytes(stream.recv_bytes || 0)}</span>
                                    </div>
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            ` : `
                <div class="detail-section">
                    <h6 class="detail-title">Streams</h6>
                    <div class="no-streams">
                        <i class="fas fa-broadcast-tower"></i>
                        <p>No active streams</p>
                    </div>
                </div>
            `}
        </div>

        <style>
            .mobile-server-details {
                color: var(--dark-slate);
            }
            
            .detail-section {
                margin-bottom: 1.5rem;
            }
            
            .detail-title {
                font-size: 1rem;
                font-weight: 600;
                margin-bottom: 1rem;
                color: var(--primary-blue);
            }
            
            .detail-grid {
                display: grid;
                gap: 0.75rem;
            }
            
            .detail-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0.5rem;
                background: var(--light-gray);
                border-radius: 8px;
            }
            
            .detail-label {
                font-weight: 500;
                color: var(--medium-gray);
            }
            
            .detail-value {
                font-weight: 600;
            }
            
            .metrics-grid {
                display: grid;
                grid-template-columns: 1fr 1fr;
                gap: 1rem;
            }
            
            .metric-card {
                text-align: center;
                padding: 1rem;
                background: var(--light-gray);
                border-radius: 8px;
            }
            
            .metric-card .metric-value {
                font-size: 1.25rem;
                font-weight: 700;
                color: var(--dark-slate);
                margin-bottom: 0.25rem;
            }
            
            .metric-card .metric-label {
                font-size: 0.75rem;
                color: var(--medium-gray);
                text-transform: uppercase;
                font-weight: 500;
            }
            
            .streams-list {
                display: flex;
                flex-direction: column;
                gap: 0.5rem;
            }
            
            .stream-item {
                padding: 1rem;
                background: var(--light-gray);
                border-radius: 12px;
                border-left: 4px solid var(--primary-blue);
                margin-bottom: 1rem;
            }
            
            .stream-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 0.75rem;
            }
            
            .stream-name {
                font-weight: 600;
                font-size: 1rem;
                color: var(--dark-slate);
            }
            
            .stream-status {
                display: flex;
                align-items: center;
                gap: 0.25rem;
                font-size: 0.75rem;
                font-weight: 600;
                padding: 0.25rem 0.5rem;
                border-radius: 4px;
                text-transform: uppercase;
            }
            
            .status-live {
                background: #dcfce7;
                color: #15803d;
            }
            
            .status-offline {
                background: #fef2f2;
                color: #dc2626;
            }
            
            .stream-metrics {
                display: grid;
                grid-template-columns: repeat(3, 1fr);
                gap: 0.5rem;
                margin-bottom: 0.75rem;
            }
            
            .stream-metric {
                display: flex;
                align-items: center;
                gap: 0.25rem;
                font-size: 0.75rem;
                color: var(--medium-gray);
            }
            
            .stream-metric i {
                font-size: 0.875rem;
                color: var(--primary-blue);
            }
            
            .stream-details {
                margin: 0.75rem 0;
                padding: 0.5rem;
                background: rgba(59, 130, 246, 0.05);
                border-radius: 8px;
            }
            
            .codec-info {
                display: flex;
                align-items: center;
                gap: 0.5rem;
                margin-bottom: 0.5rem;
                font-size: 0.875rem;
            }
            
            .codec-info:last-child {
                margin-bottom: 0;
            }
            
            .codec-info i {
                color: var(--primary-blue);
                width: 16px;
            }
            
            .codec-info small {
                color: var(--medium-gray);
                margin-left: auto;
            }
            
            .stream-stats {
                display: grid;
                grid-template-columns: repeat(2, 1fr);
                gap: 0.5rem;
                margin-top: 0.75rem;
                padding-top: 0.75rem;
                border-top: 1px solid #e5e7eb;
            }
            
            .stat-item {
                display: flex;
                justify-content: space-between;
                font-size: 0.75rem;
            }
            
            .stat-label {
                color: var(--medium-gray);
            }
            
            .stat-value {
                font-weight: 600;
                color: var(--dark-slate);
            }
            
            .no-streams {
                text-align: center;
                padding: 2rem;
                color: var(--medium-gray);
            }
            
            .no-streams i {
                font-size: 2rem;
                margin-bottom: 0.5rem;
                opacity: 0.5;
            }
        </style>
    `;
}

function closeMobileModal() {
    const modal = document.getElementById('mobile-server-modal');
    if (modal) {
        modal.classList.remove('show');
    }
}

function acknowledgeMobileAlert(alertId) {
    fetch(`/api/alerts/${alertId}/acknowledge`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    }).then(response => {
        if (response.ok) {
            // Remove the alert from the DOM
            const alertElement = document.querySelector(`[onclick="acknowledgeMobileAlert(${alertId})"]`).closest('.mobile-alert');
            if (alertElement) {
                alertElement.style.opacity = '0';
                alertElement.style.transform = 'translateX(100%)';
                setTimeout(() => {
                    alertElement.remove();
                    
                    // Hide alerts section if no more alerts
                    const remainingAlerts = document.querySelectorAll('.mobile-alert');
                    if (remainingAlerts.length === 0) {
                        const alertsSection = document.querySelector('.alerts-section');
                        if (alertsSection) {
                            alertsSection.style.display = 'none';
                        }
                    }
                }, 300);
            }
        }
    }).catch(error => {
        console.error('Error acknowledging alert:', error);
    });
}

function scrollToSection(sectionClass) {
    const section = document.querySelector(`.${sectionClass}`);
    if (section) {
        section.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function formatStreamUptime(liveMs) {
    if (!liveMs) return '0s';
    
    const now = Date.now();
    const uptimeMs = now - liveMs;
    const seconds = Math.floor(uptimeMs / 1000);
    
    if (seconds < 60) return seconds + 's';
    
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return minutes + 'm ' + (seconds % 60) + 's';
    
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return hours + 'h ' + (minutes % 60) + 'm';
    
    const days = Math.floor(hours / 24);
    return days + 'd ' + (hours % 24) + 'h';
}

// Initialize mobile dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.mobileDashboard = new MobileDashboard();
});