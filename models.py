from app import db
from datetime import datetime
from sqlalchemy import func

class Server(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    hostname = db.Column(db.String(255), nullable=False, unique=True)
    ip_address = db.Column(db.String(45), nullable=False)
    port = db.Column(db.Integer, default=80)
    role = db.Column(db.String(20), nullable=False)  # origin, edge, load-balancer
    status = db.Column(db.String(20), default='unknown')  # up, down, unknown
    api_endpoint = db.Column(db.String(255))  # SRS API or NGINX status endpoint
    api_type = db.Column(db.String(20), default='srs')  # srs, nginx
    api_token = db.Column(db.String(512))  # API authentication token/secret
    api_username = db.Column(db.String(255))  # API username (if needed)
    api_password = db.Column(db.String(255))  # API password (if needed)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to metrics
    metrics = db.relationship('ServerMetric', backref='server', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Server {self.hostname} ({self.role})>'
    
    def to_dict(self):
        latest_metric = self.metrics.order_by(ServerMetric.timestamp.desc()).first()
        return {
            'id': self.id,
            'hostname': self.hostname,
            'ip_address': self.ip_address,
            'port': self.port,
            'role': self.role,
            'status': self.status,
            'api_endpoint': self.api_endpoint,
            'api_type': self.api_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'latest_metric': latest_metric.to_dict() if latest_metric else None
        }

class ServerMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # System metrics
    cpu_usage = db.Column(db.Float)  # Percentage
    memory_usage = db.Column(db.Float)  # Percentage
    memory_total = db.Column(db.BigInteger)  # Bytes
    memory_used = db.Column(db.BigInteger)  # Bytes
    
    # Connection metrics
    active_connections = db.Column(db.Integer, default=0)
    hls_connections = db.Column(db.Integer, default=0)
    
    # Bandwidth metrics
    bytes_sent = db.Column(db.BigInteger, default=0)  # Total bytes sent
    bytes_received = db.Column(db.BigInteger, default=0)  # Total bytes received
    bandwidth_in = db.Column(db.Float, default=0)  # Current incoming bandwidth in Mbps
    bandwidth_out = db.Column(db.Float, default=0)  # Current outgoing bandwidth in Mbps
    stream_count = db.Column(db.Integer, default=0)  # Number of active streams
    
    # Status metrics
    uptime = db.Column(db.Integer)  # Seconds
    response_time = db.Column(db.Float)  # Milliseconds
    error_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<ServerMetric {self.server_id} at {self.timestamp}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'memory_total': self.memory_total,
            'memory_used': self.memory_used,
            'active_connections': self.active_connections,
            'hls_connections': self.hls_connections,
            'bytes_sent': self.bytes_sent,
            'bytes_received': self.bytes_received,
            'bandwidth_in': self.bandwidth_in,
            'bandwidth_out': self.bandwidth_out,
            'stream_count': self.stream_count,
            'uptime': self.uptime,
            'response_time': self.response_time,
            'error_count': self.error_count
        }

class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    server_id = db.Column(db.Integer, db.ForeignKey('server.id'), nullable=False)
    alert_type = db.Column(db.String(50), nullable=False)  # cpu_high, memory_high, connection_down, etc.
    severity = db.Column(db.String(20), default='warning')  # info, warning, error, critical
    message = db.Column(db.Text, nullable=False)
    acknowledged = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    acknowledged_at = db.Column(db.DateTime)
    
    # Relationship to server
    server = db.relationship('Server', backref='alerts')
    
    def __repr__(self):
        return f'<Alert {self.alert_type} for {self.server_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'server_id': self.server_id,
            'server_hostname': self.server.hostname if self.server else None,
            'alert_type': self.alert_type,
            'severity': self.severity,
            'message': self.message,
            'acknowledged': self.acknowledged,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'acknowledged_at': self.acknowledged_at.isoformat() if self.acknowledged_at else None
        }
