from flask import render_template, request, redirect, url_for, flash, jsonify
from app import app, db
from models import Server, ServerMetric, Alert
from monitoring import test_server_connectivity, get_server_metrics
from sqlalchemy import desc
from datetime import datetime, timedelta
import requests

@app.route('/')
def dashboard():
    """Main dashboard view"""
    # Check for mobile parameter override first
    force_mobile = request.args.get('mobile') == '1'
    force_desktop = request.args.get('desktop') == '1'
    
    # Check if this is a mobile device
    user_agent = request.headers.get('User-Agent', '').lower()
    is_mobile = any(device in user_agent for device in [
        'mobile', 'android', 'iphone', 'ipad', 'ipod', 'blackberry', 
        'windows phone', 'opera mini', 'iemobile', 'fennec', 'webos',
        'palm', 'symbian', 'tablet', 'kindle', 'silk', 'playbook'
    ]) or any(pattern in user_agent for pattern in [
        'mobi', 'phone', 'mini', 'nokia', 'samsung', 'htc', 'motorola'
    ])
    
    # Debug logging
    app.logger.info(f"User-Agent: {request.headers.get('User-Agent', 'None')}")
    app.logger.info(f"Is mobile detected: {is_mobile}")
    app.logger.info(f"Force mobile: {force_mobile}, Force desktop: {force_desktop}")
    
    if (is_mobile or force_mobile) and not force_desktop:
        app.logger.info("Redirecting to mobile dashboard")
        return redirect(url_for('mobile_dashboard'))
    
    servers = Server.query.all()
    recent_alerts = Alert.query.filter_by(acknowledged=False).order_by(desc(Alert.created_at)).limit(10).all()
    
    # Calculate summary statistics
    total_servers = len(servers)
    online_servers = len([s for s in servers if s.status == 'up'])
    offline_servers = len([s for s in servers if s.status == 'down'])
    unknown_servers = len([s for s in servers if s.status == 'unknown'])
    
    # Get total connections, bandwidth, and streams across all servers
    total_connections = 0
    total_bandwidth_up = 0
    total_bandwidth_down = 0
    total_streams = 0
    
    for server in servers:
        latest_metric = server.metrics.order_by(desc(ServerMetric.timestamp)).first()
        if latest_metric:
            if latest_metric.active_connections:
                total_connections += latest_metric.active_connections
            
            # Add separate upload/download bandwidth
            if latest_metric.bandwidth_in:
                total_bandwidth_down += latest_metric.bandwidth_in
            if latest_metric.bandwidth_out:
                total_bandwidth_up += latest_metric.bandwidth_out
                
            # Add stream count
            if latest_metric.stream_count:
                total_streams += latest_metric.stream_count
    
    stats = {
        'total_servers': total_servers,
        'online_servers': online_servers,
        'offline_servers': offline_servers,
        'unknown_servers': unknown_servers,
        'total_connections': total_connections,
        'total_bandwidth_up': total_bandwidth_up,
        'total_bandwidth_down': total_bandwidth_down,
        'total_streams': total_streams
    }
    
    return render_template('dashboard.html', servers=servers, alerts=recent_alerts, stats=stats)

@app.route('/mobile')
def mobile_dashboard():
    """Mobile-optimized dashboard view"""
    servers = Server.query.all()
    recent_alerts = Alert.query.filter_by(acknowledged=False).order_by(desc(Alert.created_at)).limit(5).all()
    
    # Calculate summary statistics
    total_servers = len(servers)
    online_servers = len([s for s in servers if s.status == 'up'])
    offline_servers = len([s for s in servers if s.status == 'down'])
    unknown_servers = len([s for s in servers if s.status == 'unknown'])
    
    # Get total connections, bandwidth, and streams across all servers
    total_connections = 0
    total_bandwidth_up = 0
    total_bandwidth_down = 0
    total_streams = 0
    
    for server in servers:
        latest_metric = server.metrics.order_by(desc(ServerMetric.timestamp)).first()
        if latest_metric:
            if latest_metric.active_connections:
                total_connections += latest_metric.active_connections
            
            # Add separate upload/download bandwidth
            if latest_metric.bandwidth_in:
                total_bandwidth_down += latest_metric.bandwidth_in
            if latest_metric.bandwidth_out:
                total_bandwidth_up += latest_metric.bandwidth_out
                
            # Add stream count
            if latest_metric.stream_count:
                total_streams += latest_metric.stream_count
    
    stats = {
        'total_servers': total_servers,
        'status_counts': {
            'up': online_servers,
            'down': offline_servers,
            'unknown': unknown_servers
        },
        'total_connections': total_connections,
        'total_bandwidth_up': total_bandwidth_up,
        'total_bandwidth_down': total_bandwidth_down,
        'total_streams': total_streams
    }
    
    return render_template('mobile_dashboard.html', servers=servers, alerts=recent_alerts, stats=stats)

@app.route('/servers')
def servers():
    """Server management view"""
    servers = Server.query.all()
    # Pre-fetch latest metrics for each server
    for server in servers:
        server.latest_metric = server.metrics.order_by(desc(ServerMetric.timestamp)).first()
    return render_template('servers.html', servers=servers)

@app.route('/servers/add', methods=['GET', 'POST'])
def add_server():
    """Add new server"""
    if request.method == 'POST':
        try:
            hostname = request.form.get('hostname', '').strip()
            ip_address = request.form.get('ip_address', '').strip()
            port = int(request.form.get('port', 80))
            role = request.form.get('role', '').strip()
            api_endpoint = request.form.get('api_endpoint', '').strip()
            api_type = request.form.get('api_type', 'srs').strip()
            api_token = request.form.get('api_token', '').strip()
            api_username = request.form.get('api_username', '').strip()
            api_password = request.form.get('api_password', '').strip()
            
            # Validation
            if not hostname or not ip_address or not role:
                flash('Hostname, IP address, and role are required.', 'error')
                return render_template('add_server.html')
            
            if role not in ['origin', 'edge', 'load-balancer']:
                flash('Invalid server role.', 'error')
                return render_template('add_server.html')
            
            # Check if server already exists
            existing_server = Server.query.filter_by(hostname=hostname).first()
            if existing_server:
                flash(f'Server with hostname {hostname} already exists.', 'error')
                return render_template('add_server.html')
            
            # Create new server
            server = Server(
                hostname=hostname,
                ip_address=ip_address,
                port=port,
                role=role,
                api_endpoint=api_endpoint,
                api_type=api_type,
                api_token=api_token if api_token else None,
                api_username=api_username if api_username else None,
                api_password=api_password if api_password else None
            )
            
            db.session.add(server)
            db.session.commit()
            
            # Test connectivity
            test_server_connectivity(server)
            
            flash(f'Server {hostname} added successfully!', 'success')
            return redirect(url_for('servers'))
            
        except ValueError as e:
            flash('Invalid port number.', 'error')
            return render_template('add_server.html')
        except Exception as e:
            app.logger.error(f'Error adding server: {str(e)}')
            flash('An error occurred while adding the server.', 'error')
            db.session.rollback()
            return render_template('add_server.html')
    
    return render_template('add_server.html')

@app.route('/servers/<int:server_id>/edit', methods=['GET', 'POST'])
def edit_server(server_id):
    """Edit existing server"""
    server = Server.query.get_or_404(server_id)
    
    if request.method == 'POST':
        try:
            server.hostname = request.form.get('hostname', '').strip()
            server.ip_address = request.form.get('ip_address', '').strip()
            server.port = int(request.form.get('port', 80))
            server.role = request.form.get('role', '').strip()
            server.api_endpoint = request.form.get('api_endpoint', '').strip()
            server.api_type = request.form.get('api_type', 'srs').strip()
            server.api_token = request.form.get('api_token', '').strip() or None
            server.api_username = request.form.get('api_username', '').strip() or None
            server.api_password = request.form.get('api_password', '').strip() or None
            server.updated_at = datetime.utcnow()
            
            # Validation
            if not server.hostname or not server.ip_address or not server.role:
                flash('Hostname, IP address, and role are required.', 'error')
                return render_template('add_server.html', server=server, edit_mode=True)
            
            if server.role not in ['origin', 'edge', 'load-balancer']:
                flash('Invalid server role.', 'error')
                return render_template('add_server.html', server=server, edit_mode=True)
            
            db.session.commit()
            
            # Test connectivity after update
            test_server_connectivity(server)
            
            flash(f'Server {server.hostname} updated successfully!', 'success')
            return redirect(url_for('servers'))
            
        except ValueError as e:
            flash('Invalid port number.', 'error')
            return render_template('add_server.html', server=server, edit_mode=True)
        except Exception as e:
            app.logger.error(f'Error updating server: {str(e)}')
            flash('An error occurred while updating the server.', 'error')
            db.session.rollback()
            return render_template('add_server.html', server=server, edit_mode=True)
    
    return render_template('add_server.html', server=server, edit_mode=True)

@app.route('/servers/<int:server_id>/delete', methods=['POST'])
def delete_server(server_id):
    """Delete server"""
    server = Server.query.get_or_404(server_id)
    
    try:
        hostname = server.hostname
        db.session.delete(server)
        db.session.commit()
        flash(f'Server {hostname} deleted successfully!', 'success')
    except Exception as e:
        app.logger.error(f'Error deleting server: {str(e)}')
        flash('An error occurred while deleting the server.', 'error')
        db.session.rollback()
    
    return redirect(url_for('servers'))

@app.route('/servers/<int:server_id>/test', methods=['POST'])
def test_server(server_id):
    """Test server connectivity"""
    server = Server.query.get_or_404(server_id)
    
    try:
        result = test_server_connectivity(server)
        if result['success']:
            flash(f'Server {server.hostname} is reachable!', 'success')
        else:
            flash(f'Server {server.hostname} is not reachable: {result["error"]}', 'error')
    except Exception as e:
        app.logger.error(f'Error testing server connectivity: {str(e)}')
        flash('An error occurred while testing server connectivity.', 'error')
    
    return redirect(url_for('servers'))

@app.route('/api/servers')
def api_servers():
    """API endpoint to get all servers with their latest metrics"""
    servers = Server.query.all()
    return jsonify([server.to_dict() for server in servers])

@app.route('/api/servers/<int:server_id>/metrics')
def api_server_metrics(server_id):
    """API endpoint to get server metrics"""
    server = Server.query.get_or_404(server_id)
    
    # Get metrics for the last 24 hours
    since = datetime.utcnow() - timedelta(hours=24)
    metrics = ServerMetric.query.filter(
        ServerMetric.server_id == server_id,
        ServerMetric.timestamp >= since
    ).order_by(ServerMetric.timestamp.desc()).limit(288).all()  # 5-minute intervals for 24 hours
    
    return jsonify([metric.to_dict() for metric in metrics])

@app.route('/api/servers/<int:server_id>/streams')
def api_server_streams(server_id):
    """API endpoint to get current server streams"""
    server = Server.query.get_or_404(server_id)
    
    streams = []
    
    try:
        if server.api_endpoint and server.api_type == 'srs':
            # Prepare authentication headers
            headers = {}
            auth = None
            
            if server.api_token:
                headers['Authorization'] = f'Bearer {server.api_token}'
            elif server.api_username and server.api_password:
                auth = (server.api_username, server.api_password)
            
            # Get streams from SRS API
            response = requests.get(f"{server.api_endpoint}/api/v1/streams", 
                                  headers=headers, auth=auth, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'streams' in data:
                    for stream in data['streams']:
                        streams.append({
                            'id': stream.get('id', ''),
                            'name': stream.get('name', ''),
                            'app': stream.get('app', ''),
                            'url': stream.get('url', ''),
                            'clients': stream.get('clients', 0),
                            'frames': stream.get('frames', 0),
                            'bandwidth_in': stream.get('kbps', {}).get('recv_30s', 0),
                            'bandwidth_out': stream.get('kbps', {}).get('send_30s', 0),
                            'video': stream.get('video', {}),
                            'audio': stream.get('audio', {}),
                            'publish_active': stream.get('publish', {}).get('active', False),
                            'live_time': stream.get('live_ms', 0)
                        })
    except Exception as e:
        app.logger.error(f'Error fetching streams for server {server.hostname}: {str(e)}')
    
    return jsonify({
        'server': server.to_dict(),
        'streams': streams,
        'total_streams': len(streams),
        'total_clients': sum(s['clients'] for s in streams)
    })

@app.route('/api/alerts')
def api_alerts():
    """API endpoint to get recent alerts"""
    alerts = Alert.query.filter_by(acknowledged=False).order_by(desc(Alert.created_at)).limit(20).all()
    return jsonify([alert.to_dict() for alert in alerts])

@app.route('/api/alerts/<int:alert_id>/acknowledge', methods=['POST'])
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    alert = Alert.query.get_or_404(alert_id)
    
    try:
        alert.acknowledged = True
        alert.acknowledged_at = datetime.utcnow()
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f'Error acknowledging alert: {str(e)}')
        db.session.rollback()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/dashboard/stats')
def api_dashboard_stats():
    """API endpoint for dashboard statistics"""
    servers = Server.query.all()
    
    # Server status counts
    status_counts = {'up': 0, 'down': 0, 'unknown': 0}
    role_counts = {'origin': 0, 'edge': 0, 'load-balancer': 0}
    total_connections = 0
    total_bandwidth_up = 0
    total_bandwidth_down = 0
    total_streams = 0
    
    for server in servers:
        status_counts[server.status] = status_counts.get(server.status, 0) + 1
        role_counts[server.role] = role_counts.get(server.role, 0) + 1
        
        # Get latest metrics
        latest_metric = server.metrics.order_by(desc(ServerMetric.timestamp)).first()
        if latest_metric:
            if latest_metric.active_connections:
                total_connections += latest_metric.active_connections
            
            # Add separate upload/download bandwidth
            if latest_metric.bandwidth_in:
                total_bandwidth_down += latest_metric.bandwidth_in
            if latest_metric.bandwidth_out:
                total_bandwidth_up += latest_metric.bandwidth_out
                
            # Add stream count
            if latest_metric.stream_count:
                total_streams += latest_metric.stream_count
    
    return jsonify({
        'total_servers': len(servers),
        'status_counts': status_counts,
        'role_counts': role_counts,
        'total_connections': total_connections,
        'total_bandwidth_up': total_bandwidth_up,
        'total_bandwidth_down': total_bandwidth_down,
        'total_streams': total_streams
    })
