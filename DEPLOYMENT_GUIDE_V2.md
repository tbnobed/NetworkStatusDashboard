# CDN Monitoring Dashboard - Complete Deployment Guide v2.0

This comprehensive guide covers deployment of the enhanced CDN Monitoring Dashboard with email notifications, mobile optimization, visual status indicators, and professional branding.

## New Features in Version 2.0

- **Email Alert System**: Automated SendGrid notifications for critical server issues
- **Mobile-Optimized Interface**: Complete responsive design with PWA support
- **Visual Status Indicators**: Color-coded server cards and table rows with pulsing alerts
- **Professional Branding**: OBTV CDN favicon system and mobile app icons
- **Enhanced Monitoring**: Real-time bandwidth and stream analytics
- **Progressive Web App**: Installable mobile app with offline capabilities

## Prerequisites

- Python 3.8 or higher
- PostgreSQL 12+ database
- Nginx (recommended for production)
- SendGrid account (for email notifications)

## Installation Steps

### 1. Environment Setup

```bash
# Clone the repository
git clone <repository-url>
cd cdn-monitoring-dashboard

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Required Dependencies

Ensure your `requirements.txt` includes all necessary packages:

```
apscheduler>=3.10.4
email-validator>=2.1.0
flask>=3.0.0
flask-sqlalchemy>=3.1.1
gunicorn>=21.2.0
psycopg2-binary>=2.9.9
python-dotenv>=1.0.0
requests>=2.31.0
sendgrid>=6.11.0
sqlalchemy>=2.0.23
werkzeug>=3.0.1
```

### 3. Database Setup

Create PostgreSQL database and user:

```sql
-- Connect as postgres superuser
sudo -u postgres psql

-- Create database and user
CREATE DATABASE cdn_monitoring;
CREATE USER cdn_user WITH PASSWORD 'your_secure_password_here';
GRANT ALL PRIVILEGES ON DATABASE cdn_monitoring TO cdn_user;

-- Grant additional permissions for schema management
GRANT CREATE ON DATABASE cdn_monitoring TO cdn_user;
ALTER USER cdn_user CREATEDB;

\q
```

### 4. Environment Configuration

Create `.env` file in project root:

```env
# Database Configuration
DATABASE_URL=postgresql://cdn_user:your_secure_password_here@localhost:5432/cdn_monitoring

# Flask Configuration (minimum 32 characters)
SESSION_SECRET=your_very_secure_session_secret_key_minimum_32_characters_long

# Email Configuration (SendGrid)
SENDGRID_API_KEY=SG.your_sendgrid_api_key_here
FROM_EMAIL=alerts@obedtv.com
TO_EMAIL=obedtest@tbn.tv

# Optional: Additional Configuration
FLASK_ENV=production
HOST=0.0.0.0
PORT=5000
```

### 5. Database Initialization

Choose one of the following methods:

#### Method A: Automatic Initialization (Recommended)
```bash
python3 -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('✓ Database tables created successfully!')
"
```

#### Method B: Using Migration Script
```bash
# Run the enhanced migration script
python3 migrate_database.py
```

#### Method C: Manual SQL Setup
```sql
-- Connect to your database
psql -h localhost -U cdn_user -d cdn_monitoring

-- Create servers table with enhanced fields
CREATE TABLE IF NOT EXISTS server (
    id SERIAL PRIMARY KEY,
    hostname VARCHAR(255) NOT NULL UNIQUE,
    ip_address VARCHAR(45) NOT NULL,
    port INTEGER DEFAULT 80,
    role VARCHAR(20) NOT NULL CHECK (role IN ('origin', 'edge', 'load-balancer')),
    status VARCHAR(20) DEFAULT 'unknown' CHECK (status IN ('up', 'down', 'unknown')),
    api_endpoint VARCHAR(255),
    api_type VARCHAR(20) DEFAULT 'srs' CHECK (api_type IN ('srs', 'nginx')),
    api_token VARCHAR(512),
    api_username VARCHAR(255),
    api_password VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create enhanced server metrics table
CREATE TABLE IF NOT EXISTS server_metric (
    id SERIAL PRIMARY KEY,
    server_id INTEGER REFERENCES server(id) ON DELETE CASCADE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cpu_usage FLOAT CHECK (cpu_usage >= 0 AND cpu_usage <= 100),
    memory_usage FLOAT CHECK (memory_usage >= 0 AND memory_usage <= 100),
    memory_total BIGINT CHECK (memory_total >= 0),
    memory_used BIGINT CHECK (memory_used >= 0),
    active_connections INTEGER DEFAULT 0 CHECK (active_connections >= 0),
    hls_connections INTEGER DEFAULT 0 CHECK (hls_connections >= 0),
    bytes_sent BIGINT DEFAULT 0 CHECK (bytes_sent >= 0),
    bytes_received BIGINT DEFAULT 0 CHECK (bytes_received >= 0),
    bandwidth_in FLOAT DEFAULT 0 CHECK (bandwidth_in >= 0),
    bandwidth_out FLOAT DEFAULT 0 CHECK (bandwidth_out >= 0),
    stream_count INTEGER DEFAULT 0 CHECK (stream_count >= 0),
    uptime INTEGER CHECK (uptime >= 0),
    response_time FLOAT CHECK (response_time >= 0),
    error_count INTEGER DEFAULT 0 CHECK (error_count >= 0)
);

-- Create alerts table with severity levels
CREATE TABLE IF NOT EXISTS alert (
    id SERIAL PRIMARY KEY,
    server_id INTEGER REFERENCES server(id) ON DELETE CASCADE,
    alert_type VARCHAR(50) NOT NULL CHECK (alert_type IN ('server_down', 'cpu_high', 'memory_high', 'connection_failed', 'api_error')),
    severity VARCHAR(20) DEFAULT 'warning' CHECK (severity IN ('info', 'warning', 'error', 'critical')),
    message TEXT NOT NULL,
    acknowledged BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    acknowledged_at TIMESTAMP
);

-- Create performance indexes
CREATE INDEX IF NOT EXISTS idx_server_metric_server_timestamp ON server_metric(server_id, timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_server_metric_timestamp ON server_metric(timestamp);
CREATE INDEX IF NOT EXISTS idx_alert_server_acknowledged ON alert(server_id, acknowledged);
CREATE INDEX IF NOT EXISTS idx_alert_created_at ON alert(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_server_status ON server(status);

-- Create trigger for updating server.updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_server_updated_at BEFORE UPDATE ON server 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

### 6. Static Assets Verification

Ensure all static files are properly in place:

```bash
# Check favicon system
ls -la static/
# Should include: favicon.ico, apple-touch-icon*.png, android-chrome*.png, site.webmanifest

# Verify CSS and JavaScript
ls -la static/css/
ls -la static/js/

# Check templates
ls -la templates/
# Should include: dashboard.html, mobile_dashboard.html, mobile_servers.html
```

### 7. SendGrid Email Setup

1. **Create SendGrid Account**: Visit https://sendgrid.com and create an account
2. **Generate API Key**:
   - Go to Settings → API Keys
   - Click "Create API Key"
   - Choose "Full Access" permissions
   - Copy the key (starts with "SG.")
3. **Verify Sender Domain**:
   - Go to Settings → Sender Authentication
   - Verify the domain for alerts@obedtv.com
4. **Test Email Configuration**:
```bash
python3 -c "
import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

api_key = os.environ.get('SENDGRID_API_KEY')
if api_key:
    sg = SendGridAPIClient(api_key)
    message = Mail(
        from_email='alerts@obedtv.com',
        to_emails='obedtest@tbn.tv',
        subject='CDN Monitor Test Email',
        html_content='<p>Email system is working correctly!</p>'
    )
    response = sg.send(message)
    print(f'✓ Test email sent successfully! Status: {response.status_code}')
else:
    print('✗ SENDGRID_API_KEY not found in environment')
"
```

### 8. Application Startup

#### Development Mode
```bash
# Start the application
python3 main.py

# Application will be available at http://localhost:5000
```

#### Production Mode
```bash
# Using Gunicorn with multiple workers
gunicorn --bind 0.0.0.0:5000 --workers 4 --reload main:app

# With additional options for production
gunicorn \
  --bind 0.0.0.0:5000 \
  --workers 4 \
  --worker-class sync \
  --worker-connections 1000 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --timeout 30 \
  --keep-alive 2 \
  --reload \
  main:app
```

### 9. Nginx Configuration (Production)

Create `/etc/nginx/sites-available/cdn-monitor`:

```nginx
upstream cdn_monitor {
    server 127.0.0.1:5000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration (Let's Encrypt recommended)
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;

    # Main application
    location / {
        proxy_pass http://cdn_monitor;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support for real-time updates
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Static files with caching
    location /static/ {
        alias /path/to/your/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
        
        # Compression
        gzip on;
        gzip_vary on;
        gzip_types
            text/css
            application/javascript
            application/json
            image/svg+xml
            font/woff
            font/woff2;
    }

    # Favicon and PWA icons
    location ~ ^/(favicon\.ico|apple-touch-icon.*\.png|android-chrome.*\.png|site\.webmanifest)$ {
        root /path/to/your/app/static;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # Security: Block access to sensitive files
    location ~ /\. {
        deny all;
    }
    
    location ~ \.(env|py)$ {
        deny all;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/cdn-monitor /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 10. Systemd Service (Production)

Create `/etc/systemd/system/cdn-monitor.service`:

```ini
[Unit]
Description=OBTV CDN Monitoring Dashboard
Documentation=https://github.com/your-org/cdn-monitor
After=network.target postgresql.service
Wants=postgresql.service

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/opt/cdn-monitor
Environment=PATH=/opt/cdn-monitor/venv/bin
EnvironmentFile=/opt/cdn-monitor/.env

# Main command
ExecStart=/opt/cdn-monitor/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class sync \
    --timeout 30 \
    --keep-alive 2 \
    --reload \
    main:app

# Reload command
ExecReload=/bin/kill -s HUP $MAINPID

# Restart configuration
Restart=always
RestartSec=10
StartLimitInterval=60
StartLimitBurst=3

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/cdn-monitor

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cdn-monitor
sudo systemctl start cdn-monitor
sudo systemctl status cdn-monitor
```

## Server Configuration

### Adding Servers via Web Interface

1. Navigate to `https://your-domain.com`
2. Click "Server Management" (or hamburger menu on mobile)
3. Click "Add New Server"
4. Configure server details:

**Basic Information:**
- **Hostname**: Display name (e.g., "CDN1 Srv4", "PN Edge1")
- **IP Address**: Server IP address
- **Port**: Service port (80, 1935, 1985, 2025)
- **Role**: Select from origin, edge, load-balancer

**API Configuration:**
- **API Type**: Choose 'srs' for SRS servers, 'nginx' for Nginx
- **API Endpoint**: Full API URL (e.g., `http://136.52.130.171:2025/api/v1/`)
- **Authentication**: Token, username/password if required

### Example Server Configurations

#### SRS Server Example
```
Hostname: CDN1 Srv4
IP Address: 136.52.130.171
Port: 2025
Role: origin
API Type: srs
API Endpoint: http://136.52.130.171:2025/api/v1/
```

#### Nginx Server Example
```
Hostname: Load Balancer 1
IP Address: 192.168.1.100
Port: 80
Role: load-balancer
API Type: nginx
API Endpoint: http://192.168.1.100/nginx_status
```

### Adding Servers via Command Line

```bash
# Connect to database
psql -h localhost -U cdn_user -d cdn_monitoring

# Insert server record
INSERT INTO server (hostname, ip_address, port, role, api_endpoint, api_type) 
VALUES ('CDN1 Srv4', '136.52.130.171', 2025, 'origin', 'http://136.52.130.171:2025/api/v1/', 'srs');
```

## Email Notification Configuration

### Alert Types and Thresholds

The system automatically sends emails for:

1. **Server Down** (Critical): Server becomes unreachable
2. **High Memory Usage** (Error/Critical): >85% usage (error), >95% usage (critical)
3. **High CPU Usage** (Warning/Error): >80% usage
4. **Connection Failures** (Error): API connectivity lost

### Email Template Features

- Professional OBTV CDN branding
- Detailed server information with metrics
- Severity indicators and color coding
- Timestamp and acknowledgment tracking
- Plain text fallback for compatibility
- Actionable recommendations

### Customizing Email Settings

Edit `email_notifications.py` to customize:
- Email templates and styling
- Alert thresholds and conditions
- Recipient lists and routing
- Retry logic and error handling

## Mobile App Installation

### Progressive Web App (PWA) Installation

**iOS Safari:**
1. Visit the dashboard URL
2. Tap Share button (square with arrow)
3. Scroll down and tap "Add to Home Screen"
4. Customize name and tap "Add"

**Android Chrome:**
1. Visit the dashboard URL
2. Look for "Install app" notification
3. Or tap menu (⋮) → "Install app"
4. Confirm installation

**Desktop Chrome:**
1. Visit the dashboard URL
2. Click install icon (⊕) in address bar
3. Or Chrome menu → "Install CDN Monitor..."

### Mobile Features

- Responsive card-based interface
- Touch-optimized navigation
- Offline capability with cached data
- Push notifications (if enabled)
- Native app-like experience

## Advanced Features

### Visual Status System

#### Server Cards (Desktop)
- **Online (UP)**: Green top border, normal styling
- **Offline (DOWN)**: Red top border, red background tint, red title, dimmed metrics

#### Table Rows
- **Online (UP)**: Green left border with subtle green background
- **Offline (DOWN)**: Red left border with red background and pulsing badges

#### Status Badges
- **UP**: Green background with success styling
- **DOWN**: Red background with pulsing animation
- **UNKNOWN**: Gray background with muted styling

### Real-Time Monitoring

Automatic dashboard refresh every 30 seconds showing:
- Live server status and health metrics
- Real-time bandwidth utilization (in/out Mbps)
- Active connection counts and stream analytics
- Response times and error tracking
- CPU and memory usage trends

### API Integration Details

#### SRS (Simple Realtime Server)
Supports SRS API endpoints:
- `/api/v1/summaries` - CPU/memory stats
- `/api/v1/clients` - Connection monitoring
- `/api/v1/streams` - Stream analytics
- Bandwidth calculation from stream data

#### Nginx
Supports Nginx status module:
- `/nginx_status` - Connection metrics
- `/api/status` - Extended statistics
- Basic health monitoring

## Troubleshooting

### Common Issues and Solutions

#### 1. Database Connection Errors
```bash
# Check PostgreSQL status
sudo systemctl status postgresql

# Test connection
python3 -c "
import os
from sqlalchemy import create_engine
try:
    engine = create_engine(os.environ.get('DATABASE_URL'))
    connection = engine.connect()
    print('✓ Database connection successful')
    connection.close()
except Exception as e:
    print(f'✗ Database connection failed: {e}')
"

# Check database permissions
sudo -u postgres psql -c "SELECT usename, usecreatedb FROM pg_user WHERE usename='cdn_user';"
```

#### 2. Email Notifications Not Working
```bash
# Verify SendGrid API key
python3 -c "
import os
key = os.environ.get('SENDGRID_API_KEY')
if key and key.startswith('SG.'):
    print('✓ SendGrid API key format is correct')
else:
    print('✗ Invalid or missing SendGrid API key')
"

# Test email sending
python3 -c "
from email_notifications import send_alert_email, should_send_email_alert
print('✓ Email notification system loaded successfully')
"
```

#### 3. Server API Connection Issues
```bash
# Test API connectivity manually
curl -v http://136.52.130.171:2025/api/v1/summaries

# Check server firewall
sudo ufw status
sudo iptables -L

# Verify API endpoint format
python3 -c "
import requests
try:
    response = requests.get('http://136.52.130.171:2025/api/v1/summaries', timeout=5)
    print(f'✓ API response: {response.status_code}')
except Exception as e:
    print(f'✗ API connection failed: {e}')
"
```

#### 4. Mobile Interface Problems
- Clear browser cache and cookies
- Check CSS/JS loading in browser developer tools
- Verify responsive viewport meta tags
- Test on different mobile browsers

#### 5. Visual Indicators Not Updating
- Check JavaScript console for errors
- Verify API endpoints are responding correctly
- Refresh page to reload latest CSS/JS
- Check server status in database directly

### Debug Commands

```bash
# Check application logs
sudo journalctl -u cdn-monitor -f --lines=100

# Monitor database activity
sudo -u postgres psql -c "SELECT pid, usename, application_name, state, query FROM pg_stat_activity WHERE datname='cdn_monitoring';"

# Test database migrations
python3 migrate_database.py --dry-run

# Reset database (development only)
python3 -c "
from app import app, db
with app.app_context():
    db.drop_all()
    db.create_all()
    print('Database reset complete')
"

# View current server status
python3 -c "
from app import app, db
from models import Server
with app.app_context():
    servers = Server.query.all()
    for server in servers:
        print(f'{server.hostname}: {server.status} ({server.ip_address}:{server.port})')
"
```

### Performance Monitoring

```bash
# Check system resources
htop
iotop
df -h

# Monitor application performance
curl -w "@curl-format.txt" -o /dev/null -s "http://localhost:5000/"

# Database performance
sudo -u postgres psql cdn_monitoring -c "
SELECT schemaname,tablename,attname,n_distinct,correlation 
FROM pg_stats 
WHERE tablename IN ('server','server_metric','alert');
"
```

## Security Hardening

### Required Security Measures

1. **Strong Passwords**: Use 32+ character random passwords
2. **SSL/TLS**: Enable HTTPS with Let's Encrypt certificates
3. **Firewall**: Configure UFW or iptables rules
4. **Updates**: Regularly update all dependencies
5. **Access Control**: Restrict database and API access
6. **Monitoring**: Log and monitor failed authentication attempts

### Security Configuration

```bash
# Enable UFW firewall
sudo ufw enable
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (redirects to HTTPS)
sudo ufw allow 443/tcp     # HTTPS

# Configure PostgreSQL security
sudo nano /etc/postgresql/*/main/pg_hba.conf
# Add: local cdn_monitoring cdn_user md5

# Set proper file permissions
sudo chown -R www-data:www-data /opt/cdn-monitor
sudo chmod 600 /opt/cdn-monitor/.env
sudo chmod 755 /opt/cdn-monitor
```

### SSL Certificate Setup (Let's Encrypt)

```bash
# Install Certbot
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

## Backup and Maintenance

### Automated Backup Script

Create `/opt/cdn-monitor/backup.sh`:

```bash
#!/bin/bash
# CDN Monitor Backup Script

BACKUP_DIR="/var/backups/cdn-monitor"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Create backup directory
mkdir -p $BACKUP_DIR

# Database backup
echo "Creating database backup..."
pg_dump -h localhost -U cdn_user -d cdn_monitoring > $BACKUP_DIR/database_$DATE.sql

# Application backup
echo "Creating application backup..."
tar -czf $BACKUP_DIR/application_$DATE.tar.gz \
    --exclude='venv' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    /opt/cdn-monitor

# Cleanup old backups
echo "Cleaning up old backups..."
find $BACKUP_DIR -name "database_*.sql" -mtime +$RETENTION_DAYS -delete
find $BACKUP_DIR -name "application_*.tar.gz" -mtime +$RETENTION_DAYS -delete

echo "Backup completed: $DATE"
```

Make executable and schedule:
```bash
sudo chmod +x /opt/cdn-monitor/backup.sh

# Add to crontab for daily backups at 2 AM
sudo crontab -e
# Add: 0 2 * * * /opt/cdn-monitor/backup.sh >> /var/log/cdn-monitor-backup.log 2>&1
```

### Update Procedure

```bash
# Create update script
cat > /opt/cdn-monitor/update.sh << 'EOF'
#!/bin/bash
set -e

echo "Starting CDN Monitor update..."

# Stop service
sudo systemctl stop cdn-monitor

# Backup current version
cp -r /opt/cdn-monitor /opt/cdn-monitor.backup.$(date +%Y%m%d)

# Update code
cd /opt/cdn-monitor
git pull origin main

# Update dependencies
source venv/bin/activate
pip install --upgrade -r requirements.txt

# Run migrations
python3 migrate_database.py

# Restart service
sudo systemctl start cdn-monitor
sudo systemctl status cdn-monitor

echo "Update completed successfully!"
EOF

chmod +x /opt/cdn-monitor/update.sh
```

### Health Monitoring

Create monitoring script `/opt/cdn-monitor/health-check.sh`:

```bash
#!/bin/bash
# Health check script for CDN Monitor

SERVICE_URL="http://localhost:5000/"
EMAIL_RECIPIENT="admin@obedtv.com"

# Check service status
if ! systemctl is-active --quiet cdn-monitor; then
    echo "CDN Monitor service is not running!" | mail -s "CDN Monitor Alert" $EMAIL_RECIPIENT
    exit 1
fi

# Check HTTP response
if ! curl -f -s $SERVICE_URL > /dev/null; then
    echo "CDN Monitor web interface is not responding!" | mail -s "CDN Monitor Alert" $EMAIL_RECIPIENT
    exit 1
fi

# Check database connectivity
if ! python3 -c "from app import app, db; app.app_context().push(); db.engine.execute('SELECT 1')" 2>/dev/null; then
    echo "CDN Monitor database connection failed!" | mail -s "CDN Monitor Alert" $EMAIL_RECIPIENT
    exit 1
fi

echo "All health checks passed"
```

Schedule health checks:
```bash
# Add to crontab for every 5 minutes
sudo crontab -e
# Add: */5 * * * * /opt/cdn-monitor/health-check.sh
```

## Performance Optimization

### Expected Performance Metrics

- **Dashboard Load Time**: < 2 seconds
- **API Response Time**: < 500ms
- **Database Query Time**: < 100ms
- **Email Delivery**: < 30 seconds via SendGrid
- **Mobile Interface**: Optimized for 3G networks

### Scaling Recommendations

#### Small Deployment (1-10 servers)
- 1 application worker
- 2GB RAM, 2 CPU cores
- Basic PostgreSQL configuration

#### Medium Deployment (10-50 servers)
- 2-4 application workers
- 4GB RAM, 4 CPU cores
- Optimized PostgreSQL with connection pooling

#### Large Deployment (50+ servers)
- 4+ application workers
- 8GB+ RAM, 8+ CPU cores
- PostgreSQL cluster with read replicas
- Redis caching layer
- Load balancer for multiple app instances

### Database Optimization

```sql
-- Optimize PostgreSQL for CDN Monitor
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
ALTER SYSTEM SET checkpoint_completion_target = 0.9;
ALTER SYSTEM SET wal_buffers = '16MB';
ALTER SYSTEM SET default_statistics_target = 100;

-- Reload configuration
SELECT pg_reload_conf();

-- Analyze tables for better query planning
ANALYZE server;
ANALYZE server_metric;
ANALYZE alert;
```

## Support and Documentation

### Regular Maintenance Schedule

#### Daily
- [ ] Check service status and logs
- [ ] Verify email notifications working
- [ ] Monitor disk space usage

#### Weekly  
- [ ] Review alert logs and patterns
- [ ] Check for security updates
- [ ] Verify backup completion

#### Monthly
- [ ] Update dependencies and packages
- [ ] Review performance metrics
- [ ] Database maintenance and optimization

#### Quarterly
- [ ] SSL certificate renewal check
- [ ] Security audit and penetration testing
- [ ] Capacity planning review

### Troubleshooting Checklist

When issues occur, check in this order:

1. **Service Status**: `sudo systemctl status cdn-monitor`
2. **Application Logs**: `sudo journalctl -u cdn-monitor -f`
3. **Database Connectivity**: Test database connection
4. **Network Connectivity**: Test API endpoints
5. **Resource Usage**: Check CPU, memory, disk
6. **Email Service**: Verify SendGrid configuration

### Getting Help

For technical support:

1. **Check Logs**: Always review application and system logs first
2. **Verify Configuration**: Double-check environment variables and database settings
3. **Test Components**: Isolate the problem by testing individual components
4. **Documentation**: Review this guide and any error-specific documentation

### Version Information

- **Application Version**: 2.0
- **Database Schema Version**: See `migrate_database.py`
- **API Version**: Compatible with SRS v4+ and Nginx 1.18+
- **Python Requirements**: 3.8+
- **PostgreSQL Requirements**: 12+

---

This deployment guide covers all aspects of the enhanced CDN Monitoring Dashboard. Follow the steps carefully and refer to the troubleshooting section for any issues during deployment.