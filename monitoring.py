import requests
import time
import logging
from datetime import datetime
from app import app, db
from models import Server, ServerMetric, Alert
from sqlalchemy import desc

logger = logging.getLogger(__name__)

def test_server_connectivity(server):
    """Test if a server is reachable and update its status"""
    try:
        # Basic connectivity test
        url = f"http://{server.ip_address}:{server.port}"
        if server.api_endpoint:
            url = server.api_endpoint
        
        # Prepare authentication headers
        headers = {}
        auth = None
        
        if server.api_token:
            headers['Authorization'] = f'Bearer {server.api_token}'
        elif server.api_username and server.api_password:
            auth = (server.api_username, server.api_password)
        
        start_time = time.time()
        response = requests.get(url, headers=headers, auth=auth, timeout=10)
        response_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        
        if response.status_code == 200:
            server.status = 'up'
            db.session.commit()
            return {'success': True, 'response_time': response_time}
        else:
            server.status = 'down'
            db.session.commit()
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.RequestException as e:
        server.status = 'down'
        db.session.commit()
        logger.error(f'Connectivity test failed for {server.hostname}: {str(e)}')
        return {'success': False, 'error': str(e)}
    except Exception as e:
        server.status = 'unknown'
        db.session.commit()
        logger.error(f'Unexpected error testing {server.hostname}: {str(e)}')
        return {'success': False, 'error': str(e)}

def get_server_metrics(server):
    """Fetch metrics from a server using its API"""
    metrics = {
        'active_connections': 0,
        'hls_connections': 0,
        'cpu_usage': None,
        'memory_usage': None,
        'memory_total': None,
        'memory_used': None,
        'uptime': None,
        'response_time': None,
        'error_count': 0
    }
    
    try:
        if not server.api_endpoint:
            logger.warning(f'No API endpoint configured for server {server.hostname}')
            return metrics
        
        # Prepare authentication headers
        headers = {}
        auth = None
        
        if server.api_token:
            headers['Authorization'] = f'Bearer {server.api_token}'
        elif server.api_username and server.api_password:
            auth = (server.api_username, server.api_password)
        
        start_time = time.time()
        
        if server.api_type == 'srs':
            # SRS API format
            response = requests.get(f"{server.api_endpoint}/api/v1/clients", 
                                  headers=headers, auth=auth, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                clients = data.get('clients', [])
                metrics['active_connections'] = len(clients)
                metrics['hls_connections'] = len([c for c in clients if c.get('type') == 'hls'])
                metrics['response_time'] = response_time
                
                # Try to get bandwidth data from streams endpoint
                try:
                    streams_response = requests.get(f"{server.api_endpoint}/api/v1/streams", 
                                                  headers=headers, auth=auth, timeout=5)
                    if streams_response.status_code == 200:
                        streams_data = streams_response.json()
                        logger.debug(f'Streams data for {server.hostname}: {streams_data}')
                        
                        total_bandwidth_in = 0
                        total_bandwidth_out = 0
                        total_bytes_sent = 0
                        total_bytes_received = 0
                        
                        # Parse SRS streams data - check different possible structures
                        streams_list = None
                        if 'streams' in streams_data:
                            streams_list = streams_data['streams']
                        elif isinstance(streams_data, list):
                            streams_list = streams_data
                        elif 'data' in streams_data and 'streams' in streams_data['data']:
                            streams_list = streams_data['data']['streams']
                        
                        if streams_list:
                            logger.debug(f'Found {len(streams_list)} streams for {server.hostname}')
                            for stream in streams_list:
                                logger.debug(f'Stream data: {stream}')
                                
                                # Check for bandwidth data in various formats
                                if 'kbps' in stream:
                                    kbps_data = stream['kbps']
                                    if 'recv_30s' in kbps_data:
                                        total_bandwidth_in += float(kbps_data['recv_30s'])
                                    if 'send_30s' in kbps_data:
                                        total_bandwidth_out += float(kbps_data['send_30s'])
                                
                                # Extract total bytes from streams
                                if 'bytes' in stream:
                                    bytes_data = stream['bytes']
                                    if 'recv' in bytes_data:
                                        total_bytes_received += int(bytes_data['recv'])
                                    if 'send' in bytes_data:
                                        total_bytes_sent += int(bytes_data['send'])
                        
                        # Convert kbps to Mbps and store metrics
                        metrics['bandwidth_in'] = total_bandwidth_in / 1000
                        metrics['bandwidth_out'] = total_bandwidth_out / 1000
                        metrics['bytes_received'] = total_bytes_received
                        metrics['bytes_sent'] = total_bytes_sent
                        
                        logger.debug(f'Bandwidth metrics for {server.hostname}: in={metrics["bandwidth_in"]}, out={metrics["bandwidth_out"]}')
                                    
                except Exception as e:
                    logger.debug(f'Could not get streams data for {server.hostname}: {str(e)}')
                    
                    # Fallback to summaries endpoint for basic stats
                    try:
                        stats_response = requests.get(f"{server.api_endpoint}/api/v1/summaries", 
                                                    headers=headers, auth=auth, timeout=5)
                        if stats_response.status_code == 200:
                            stats_data = stats_response.json()
                            
                            # Parse SRS bandwidth data from summaries as fallback
                            if 'data' in stats_data and isinstance(stats_data['data'], dict):
                                data_section = stats_data['data']
                                
                                if 'kbps' in data_section:
                                    kbps_data = data_section['kbps']
                                    if 'recv_30s' in kbps_data:
                                        metrics['bandwidth_in'] = float(kbps_data['recv_30s']) / 1000
                                    if 'send_30s' in kbps_data:
                                        metrics['bandwidth_out'] = float(kbps_data['send_30s']) / 1000
                                
                                if 'bytes' in data_section:
                                    bytes_data = data_section['bytes']
                                    if 'recv' in bytes_data:
                                        metrics['bytes_received'] = int(bytes_data['recv'])
                                    if 'send' in bytes_data:
                                        metrics['bytes_sent'] = int(bytes_data['send'])
                    except Exception as e2:
                        logger.debug(f'Could not get fallback stats for {server.hostname}: {str(e2)}')
                    
        elif server.api_type == 'nginx':
            # NGINX stub_status format
            response = requests.get(server.api_endpoint, headers=headers, auth=auth, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                # Parse NGINX stub_status format
                lines = response.text.strip().split('\n')
                for line in lines:
                    if 'Active connections:' in line:
                        metrics['active_connections'] = int(line.split(':')[1].strip())
                    elif line.strip().isdigit():
                        # Handle requests line: accepts handled requests
                        parts = line.strip().split()
                        if len(parts) >= 3:
                            metrics['active_connections'] = int(parts[0])
                
                metrics['response_time'] = response_time
        
        else:
            # Generic HTTP health check
            response = requests.get(server.api_endpoint, headers=headers, auth=auth, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                metrics['response_time'] = response_time
                # Try to parse JSON if available
                try:
                    data = response.json()
                    if 'connections' in data:
                        metrics['active_connections'] = data['connections']
                    if 'cpu' in data:
                        metrics['cpu_usage'] = data['cpu']
                    if 'memory' in data:
                        metrics['memory_usage'] = data['memory']
                except:
                    pass
    
    except requests.exceptions.RequestException as e:
        logger.error(f'Failed to get metrics for {server.hostname}: {str(e)}')
        metrics['error_count'] = 1
    except Exception as e:
        logger.error(f'Unexpected error getting metrics for {server.hostname}: {str(e)}')
        metrics['error_count'] = 1
    
    return metrics

def collect_server_metrics():
    """Collect metrics for all servers"""
    with app.app_context():
        servers = Server.query.all()
        
        for server in servers:
            try:
                # Test connectivity
                connectivity_result = test_server_connectivity(server)
                
                # Get detailed metrics if server is up
                if connectivity_result['success']:
                    metrics_data = get_server_metrics(server)
                    metrics_data['response_time'] = connectivity_result.get('response_time')
                else:
                    # Server is down, record minimal metrics
                    metrics_data = {
                        'active_connections': 0,
                        'hls_connections': 0,
                        'cpu_usage': None,
                        'memory_usage': None,
                        'memory_total': None,
                        'memory_used': None,
                        'uptime': None,
                        'response_time': None,
                        'error_count': 1
                    }
                
                # Save metrics to database
                metric = ServerMetric(
                    server_id=server.id,
                    cpu_usage=metrics_data.get('cpu_usage'),
                    memory_usage=metrics_data.get('memory_usage'),
                    memory_total=metrics_data.get('memory_total'),
                    memory_used=metrics_data.get('memory_used'),
                    active_connections=metrics_data.get('active_connections', 0),
                    hls_connections=metrics_data.get('hls_connections', 0),
                    uptime=metrics_data.get('uptime'),
                    response_time=metrics_data.get('response_time'),
                    error_count=metrics_data.get('error_count', 0)
                )
                
                db.session.add(metric)
                
                # Check for alerts
                check_server_alerts(server, metrics_data)
                
            except Exception as e:
                logger.error(f'Error collecting metrics for {server.hostname}: {str(e)}')
        
        try:
            db.session.commit()
        except Exception as e:
            logger.error(f'Error saving metrics to database: {str(e)}')
            db.session.rollback()

def check_server_alerts(server, metrics_data):
    """Check for alert conditions and create alerts if necessary"""
    try:
        # Check if server is down
        if server.status == 'down':
            existing_alert = Alert.query.filter_by(
                server_id=server.id,
                alert_type='server_down',
                acknowledged=False
            ).first()
            
            if not existing_alert:
                alert = Alert(
                    server_id=server.id,
                    alert_type='server_down',
                    severity='critical',
                    message=f'Server {server.hostname} is down and not responding to health checks.'
                )
                db.session.add(alert)
        
        # Check high CPU usage
        if metrics_data.get('cpu_usage') and metrics_data['cpu_usage'] > 80:
            existing_alert = Alert.query.filter_by(
                server_id=server.id,
                alert_type='cpu_high',
                acknowledged=False
            ).first()
            
            if not existing_alert:
                alert = Alert(
                    server_id=server.id,
                    alert_type='cpu_high',
                    severity='warning',
                    message=f'High CPU usage on {server.hostname}: {metrics_data["cpu_usage"]:.1f}%'
                )
                db.session.add(alert)
        
        # Check high memory usage
        if metrics_data.get('memory_usage') and metrics_data['memory_usage'] > 85:
            existing_alert = Alert.query.filter_by(
                server_id=server.id,
                alert_type='memory_high',
                acknowledged=False
            ).first()
            
            if not existing_alert:
                alert = Alert(
                    server_id=server.id,
                    alert_type='memory_high',
                    severity='warning',
                    message=f'High memory usage on {server.hostname}: {metrics_data["memory_usage"]:.1f}%'
                )
                db.session.add(alert)
        
        # Check high response time
        if metrics_data.get('response_time') and metrics_data['response_time'] > 5000:  # 5 seconds
            existing_alert = Alert.query.filter_by(
                server_id=server.id,
                alert_type='response_slow',
                acknowledged=False
            ).first()
            
            if not existing_alert:
                alert = Alert(
                    server_id=server.id,
                    alert_type='response_slow',
                    severity='warning',
                    message=f'Slow response time on {server.hostname}: {metrics_data["response_time"]:.0f}ms'
                )
                db.session.add(alert)
                
    except Exception as e:
        logger.error(f'Error checking alerts for {server.hostname}: {str(e)}')

def start_monitoring(scheduler):
    """Start the background monitoring jobs"""
    try:
        # Collect metrics every 5 minutes
        scheduler.add_job(
            func=collect_server_metrics,
            trigger="interval",
            minutes=5,
            id='collect_metrics',
            name='Collect server metrics',
            replace_existing=True
        )
        
        logger.info('Background monitoring started')
        
        # Run initial metrics collection
        collect_server_metrics()
        
    except Exception as e:
        logger.error(f'Error starting monitoring: {str(e)}')
