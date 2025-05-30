# CDN Monitoring Dashboard - Deployment Guide

This guide covers deploying the CDN monitoring dashboard with enhanced bandwidth monitoring, stream count tracking, and real-time updates.

## Features

- **Real-time CDN Monitoring**: Track server status, connections, and performance metrics
- **Bandwidth Analytics**: Separate upload/download bandwidth monitoring with live data
- **Stream Count Tracking**: Monitor active streams per server and total across infrastructure
- **Auto-refresh Dashboard**: Statistics update every 30 seconds automatically
- **API Integration**: Supports SRS and NGINX APIs with authentication
- **Alert System**: Automated alerts for performance thresholds
- **PostgreSQL Storage**: Persistent metrics and configuration storage

## Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.8+
- PostgreSQL 12+
- Nginx (for production deployment)
- SystemD (for service management)

## Installation Steps

### 1. System Dependencies

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required system packages
sudo apt install -y python3 python3-pip python3-venv postgresql postgresql-contrib nginx git

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql
```

### 2. Database Setup

```bash
# Switch to postgres user
sudo -u postgres psql

# Create database and user
CREATE DATABASE cdnmonitor;
CREATE USER cdnmonitor WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE cdnmonitor TO cdnmonitor;
\q
```

### 3. Application Deployment

```bash
# Create application directory
sudo mkdir -p /opt/cdnmonitor
cd /opt/cdnmonitor

# Clone or copy application files
# (Copy all application files to /opt/cdnmonitor)

# Create virtual environment
sudo python3 -m venv venv
sudo chown -R www-data:www-data /opt/cdnmonitor

# Activate virtual environment and install dependencies
sudo -u www-data bash
source venv/bin/activate
pip install -r deployment_requirements.txt
exit
```

### 4. Environment Configuration

```bash
# Create environment file
sudo nano /opt/cdnmonitor/.env
```

Add the following configuration:

```env
# Database Configuration
DATABASE_URL=postgresql://cdnmonitor:your_secure_password_here@localhost/cdnmonitor

# Flask Configuration
FLASK_SECRET_KEY=your_super_secret_key_here_minimum_32_characters
FLASK_ENV=production

# Monitoring Configuration
MONITORING_INTERVAL=30
ALERT_RETENTION_DAYS=30

# Optional: External API Keys (if integrating with external services)
# TWILIO_ACCOUNT_SID=your_twilio_sid
# TWILIO_AUTH_TOKEN=your_twilio_token
# SLACK_WEBHOOK_URL=your_slack_webhook
```

### 5. Database Migration and Initialization

**IMPORTANT**: The application includes new database fields for bandwidth and stream monitoring that require proper initialization.

```bash
# Switch to application user
sudo -u www-data bash
cd /opt/cdnmonitor
source venv/bin/activate

# Initialize database tables
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"

# Verify database schema
python3 -c "
from app import app, db
from models import Server, ServerMetric, Alert
with app.app_context():
    # Check if new columns exist
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = inspector.get_columns('server_metric')
    column_names = [col['name'] for col in columns]
    
    required_columns = ['bandwidth_in', 'bandwidth_out', 'stream_count']
    missing_columns = [col for col in required_columns if col not in column_names]
    
    if missing_columns:
        print(f'Missing columns: {missing_columns}')
        print('Running database migration...')
        
        # Add missing columns
        db.engine.execute('ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS bandwidth_in FLOAT DEFAULT 0')
        db.engine.execute('ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS bandwidth_out FLOAT DEFAULT 0') 
        db.engine.execute('ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS stream_count INTEGER DEFAULT 0')
        
        print('Database migration completed')
    else:
        print('Database schema is up to date')
"

exit
```

### 6. SystemD Service Configuration

```bash
# Copy service file
sudo cp cdnmonitor.service /etc/systemd/system/

# Reload systemd and enable service
sudo systemctl daemon-reload
sudo systemctl enable cdnmonitor
sudo systemctl start cdnmonitor

# Check service status
sudo systemctl status cdnmonitor
```

### 7. Nginx Configuration

```bash
# Copy nginx configuration
sudo cp nginx_cdnmonitor.conf /etc/nginx/sites-available/cdnmonitor

# Enable site
sudo ln -s /etc/nginx/sites-available/cdnmonitor /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Restart nginx
sudo systemctl restart nginx
```

### 8. Firewall Configuration

```bash
# Allow HTTP and HTTPS traffic
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable
```

## Post-Deployment Configuration

### 1. Add CDN Servers

Navigate to `http://your-server-ip/servers` and add your CDN servers:

**For SRS Servers:**
- **Hostname**: Your server name (e.g., "OTV Svr1")
- **IP Address**: Server IP address
- **Port**: SRS API port (usually 1985)
- **Role**: origin/edge/load-balancer
- **API Type**: srs
- **API Endpoint**: `http://server-ip:1985/api/v1/streams`
- **API Token**: Your SRS API secret (if authentication is enabled)

**For NGINX Servers:**
- **Hostname**: Your server name (e.g., "PN Edge1")
- **IP Address**: Server IP address
- **Port**: NGINX status port (usually 80)
- **Role**: origin/edge/load-balancer
- **API Type**: nginx
- **API Endpoint**: `http://server-ip/nginx_status`
- **API Username/Password**: If basic auth is configured

### 2. Verify Monitoring

1. Check that servers appear as "UP" on the dashboard
2. Verify bandwidth metrics are being collected (should show actual Mbps values)
3. Confirm stream counts are accurate
4. Watch for automatic updates every 30 seconds

### 3. Configure Alerts (Optional)

The system automatically generates alerts for:
- High CPU usage (>80%)
- High memory usage (>90%)
- Server downtime
- High bandwidth utilization

## New Features in This Version

### Enhanced Bandwidth Monitoring
- **Separate Upload/Download Tracking**: Dashboard now displays distinct upload and download bandwidth metrics
- **Real-time Updates**: Bandwidth values refresh every 30 seconds with live data from SRS `/api/v1/streams` endpoint
- **Accurate Measurements**: Uses actual kbps data from stream APIs, converted to Mbps for display

### Stream Count Analytics
- **Per-Server Streams**: Individual server cards show active stream count
- **Total Stream Counter**: Dashboard displays total active streams across all servers
- **Live Stream Tracking**: Stream counts update automatically as streams start/stop

### Improved Dashboard Layout
- **Two-Row Statistics**: Clean organization with server stats in top row, bandwidth/streams in bottom row
- **Auto-refresh Functionality**: All cards update every 30 seconds without page reload
- **Enhanced Server Cards**: Now show Connections, Streams, and Response Time in individual server displays

## Database Schema Updates

This version includes new database fields:

```sql
-- New columns in server_metric table
ALTER TABLE server_metric ADD COLUMN bandwidth_in FLOAT DEFAULT 0;
ALTER TABLE server_metric ADD COLUMN bandwidth_out FLOAT DEFAULT 0;
ALTER TABLE server_metric ADD COLUMN stream_count INTEGER DEFAULT 0;
```

These columns store:
- `bandwidth_in`: Download bandwidth in Mbps
- `bandwidth_out`: Upload bandwidth in Mbps  
- `stream_count`: Number of active streams on the server

## Troubleshooting

### Service Issues
```bash
# Check service logs
sudo journalctl -u cdnmonitor -f

# Restart service
sudo systemctl restart cdnmonitor

# Check database connectivity
sudo -u www-data bash
cd /opt/cdnmonitor
source venv/bin/activate
python3 -c "from app import db; print('Database connection:', db.engine.execute('SELECT 1').scalar())"
```

### Monitoring Issues
```bash
# Test server connectivity manually
curl -H "Authorization: Bearer YOUR_API_TOKEN" http://server-ip:1985/api/v1/streams

# Check monitoring logs
sudo journalctl -u cdnmonitor | grep -i monitoring

# Verify database is receiving metrics
sudo -u postgres psql cdnmonitor -c "SELECT hostname, bandwidth_in, bandwidth_out, stream_count, timestamp FROM server_metric JOIN server ON server_metric.server_id = server.id ORDER BY timestamp DESC LIMIT 5;"
```

### Performance Optimization

For high-traffic deployments:

1. **Database Optimization**:
   ```sql
   CREATE INDEX idx_server_metric_timestamp ON server_metric(timestamp);
   CREATE INDEX idx_server_metric_server_id ON server_metric(server_id);
   ```

2. **Nginx Caching**:
   Add to nginx configuration:
   ```nginx
   location /static/ {
       expires 1d;
       add_header Cache-Control "public, immutable";
   }
   ```

3. **Log Rotation**:
   ```bash
   sudo nano /etc/logrotate.d/cdnmonitor
   ```

## Security Considerations

1. **API Token Security**: Store SRS API tokens securely in environment variables
2. **Database Access**: Use strong passwords and limit database access to localhost
3. **HTTPS**: Configure SSL certificates for production deployments
4. **Firewall**: Restrict access to monitoring ports and databases
5. **Regular Updates**: Keep system packages and Python dependencies updated

## Backup and Recovery

### Database Backup
```bash
# Create backup
sudo -u postgres pg_dump cdnmonitor > /backup/cdnmonitor_$(date +%Y%m%d_%H%M%S).sql

# Restore backup
sudo -u postgres psql cdnmonitor < /backup/cdnmonitor_backup.sql
```

### Application Backup
```bash
# Backup application and configuration
sudo tar -czf /backup/cdnmonitor_app_$(date +%Y%m%d_%H%M%S).tar.gz /opt/cdnmonitor
```

## Support

For issues related to:
- **SRS API Integration**: Verify SRS server configuration and API endpoints
- **Database Performance**: Check PostgreSQL logs and consider indexing
- **High Load**: Monitor system resources and consider scaling horizontally

The dashboard is designed to handle multiple CDN servers with real-time bandwidth and stream monitoring. All metrics are stored for historical analysis and trending.