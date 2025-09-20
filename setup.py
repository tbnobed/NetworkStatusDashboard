#!/usr/bin/env python3
"""
CDN Monitoring Dashboard Setup Script

This script initializes the CDN monitoring dashboard by:
1. Verifying environment configuration
2. Setting up the PostgreSQL database
3. Creating database tables and schema
4. Running initial system checks
5. Starting the monitoring service
"""

import os
import sys
import subprocess
import logging
import time
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_python_version():
    """Check if Python version is compatible"""
    logger.info("Checking Python version...")
    if sys.version_info < (3, 8):
        logger.error("Python 3.8 or higher is required")
        return False
    logger.info(f"Python {sys.version.split()[0]} - OK")
    return True

def check_environment_variables():
    """Check required environment variables"""
    logger.info("Checking environment variables...")
    
    required_vars = {
        'DATABASE_URL': 'PostgreSQL database connection string',
        'SESSION_SECRET': 'Flask session secret key'
    }
    
    optional_vars = {
        'SENDGRID_API_KEY': 'Email notifications (optional)',
        'PGHOST': 'PostgreSQL host',
        'PGDATABASE': 'PostgreSQL database name',
        'PGUSER': 'PostgreSQL username',
        'PGPASSWORD': 'PostgreSQL password',
        'PGPORT': 'PostgreSQL port'
    }
    
    missing_required = []
    
    # Check required variables
    for var, description in required_vars.items():
        if not os.environ.get(var):
            missing_required.append(f"{var} - {description}")
            logger.error(f"Missing required environment variable: {var}")
        else:
            logger.info(f"✓ {var} - configured")
    
    # Check optional variables
    for var, description in optional_vars.items():
        if os.environ.get(var):
            logger.info(f"✓ {var} - configured")
        else:
            logger.info(f"- {var} - not configured ({description})")
    
    if missing_required:
        logger.error("Missing required environment variables:")
        for var in missing_required:
            logger.error(f"  - {var}")
        return False
    
    return True

def check_database_connection():
    """Test database connection"""
    logger.info("Testing database connection...")
    
    try:
        # Import here to avoid circular imports
        from app import db, app
        
        with app.app_context():
            # Test the connection
            with db.engine.connect() as conn:
                conn.execute(db.text('SELECT 1')).scalar()
            logger.info("✓ Database connection - OK")
            return True
            
    except Exception as e:
        logger.error(f"Database connection failed: {str(e)}")
        return False

def setup_database():
    """Initialize database tables and schema"""
    logger.info("Setting up database schema...")
    
    try:
        from app import db, app
        from models import Server, ServerMetric, Alert
        
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("✓ Database tables created successfully")
            
            # Verify tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            expected_tables = ['server', 'server_metric', 'alert']
            missing_tables = [table for table in expected_tables if table not in tables]
            
            if missing_tables:
                logger.error(f"Missing database tables: {missing_tables}")
                return False
            
            logger.info(f"✓ Database tables verified: {expected_tables}")
            
            # Check for required columns in server_metric table
            columns = inspector.get_columns('server_metric')
            column_names = [col['name'] for col in columns]
            
            required_columns = [
                'bandwidth_in', 'bandwidth_out', 'stream_count',
                'active_connections', 'hls_connections', 'bytes_sent',
                'bytes_received', 'cpu_usage', 'memory_usage'
            ]
            
            missing_columns = [col for col in required_columns if col not in column_names]
            
            if missing_columns:
                logger.warning(f"Missing columns detected: {missing_columns}")
                logger.info("Running database migration...")
                
                # Add missing columns with proper defaults
                migrations = {
                    'bandwidth_in': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS bandwidth_in FLOAT DEFAULT 0',
                    'bandwidth_out': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS bandwidth_out FLOAT DEFAULT 0',
                    'stream_count': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS stream_count INTEGER DEFAULT 0',
                    'active_connections': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS active_connections INTEGER DEFAULT 0',
                    'hls_connections': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS hls_connections INTEGER DEFAULT 0',
                    'bytes_sent': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS bytes_sent BIGINT DEFAULT 0',
                    'bytes_received': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS bytes_received BIGINT DEFAULT 0',
                    'cpu_usage': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS cpu_usage FLOAT',
                    'memory_usage': 'ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS memory_usage FLOAT'
                }
                
                for column in missing_columns:
                    if column in migrations:
                        try:
                            with db.engine.connect() as conn:
                                conn.execute(db.text(migrations[column]))
                            logger.info(f"✓ Added column: {column}")
                        except Exception as e:
                            logger.error(f"Failed to add column {column}: {str(e)}")
                            return False
            
            logger.info("✓ Database schema setup completed")
            return True
            
    except Exception as e:
        logger.error(f"Database setup failed: {str(e)}")
        return False

def verify_dependencies():
    """Verify required Python packages are installed"""
    logger.info("Verifying Python dependencies...")
    
    required_packages = [
        'flask',
        'flask_sqlalchemy',
        'sqlalchemy',
        'psycopg2-binary',
        'python-dotenv',
        'apscheduler',
        'requests',
        'werkzeug',
        'email-validator',
        'gunicorn'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            logger.info(f"✓ {package} - installed")
        except ImportError:
            missing_packages.append(package)
            logger.error(f"✗ {package} - missing")
    
    if missing_packages:
        logger.error(f"Missing packages: {missing_packages}")
        logger.info("Install missing packages with: pip install " + " ".join(missing_packages))
        return False
    
    logger.info("✓ All dependencies verified")
    return True

def create_sample_server():
    """Create a sample server entry for testing"""
    logger.info("Creating sample server configuration...")
    
    try:
        from app import db, app
        from models import Server
        
        with app.app_context():
            # Check if any servers already exist
            existing_servers = Server.query.count()
            
            if existing_servers > 0:
                logger.info(f"Found {existing_servers} existing servers - skipping sample creation")
                return True
            
            # Create a sample server entry
            sample_server = Server(
                hostname="Sample CDN Server",
                ip_address="127.0.0.1",
                port=1985,
                role="origin",
                status="unknown",
                api_endpoint="http://127.0.0.1:1985/api/v1/streams",
                api_type="srs",
                api_token=""
            )
            
            db.session.add(sample_server)
            db.session.commit()
            
            logger.info("✓ Sample server created")
            logger.info("Note: Update server configuration via the web interface at /servers")
            return True
            
    except Exception as e:
        logger.error(f"Failed to create sample server: {str(e)}")
        return False

def run_system_checks():
    """Run comprehensive system checks"""
    logger.info("Running system checks...")
    
    checks = [
        ("Python version", check_python_version),
        ("Environment variables", check_environment_variables),
        ("Dependencies", verify_dependencies),
        ("Database connection", check_database_connection),
        ("Database setup", setup_database),
        ("Sample configuration", create_sample_server)
    ]
    
    failed_checks = []
    
    for check_name, check_func in checks:
        logger.info(f"\n--- {check_name} ---")
        try:
            if not check_func():
                failed_checks.append(check_name)
        except Exception as e:
            logger.error(f"{check_name} failed with exception: {str(e)}")
            failed_checks.append(check_name)
    
    return failed_checks

def display_startup_info():
    """Display startup information and next steps"""
    logger.info("\n" + "="*60)
    logger.info("CDN MONITORING DASHBOARD SETUP COMPLETE")
    logger.info("="*60)
    
    logger.info("\n📊 Dashboard Features:")
    logger.info("  • Real-time CDN server monitoring")
    logger.info("  • Bandwidth and stream analytics")
    logger.info("  • Automated alert system")
    logger.info("  • Mobile-responsive interface")
    logger.info("  • PostgreSQL data persistence")
    
    logger.info("\n🌐 Web Interface:")
    logger.info("  • Dashboard: http://localhost:5000/")
    logger.info("  • Server Management: http://localhost:5000/servers")
    logger.info("  • Mobile View: http://localhost:5000/mobile")
    
    logger.info("\n⚙️ Next Steps:")
    logger.info("  1. Add your CDN servers via the web interface")
    logger.info("  2. Configure API endpoints and authentication")
    logger.info("  3. Set up email alerts (optional)")
    logger.info("  4. Monitor your infrastructure in real-time")
    
    logger.info("\n🔧 Configuration Files:")
    logger.info("  • Database models: models.py")
    logger.info("  • Routes and views: routes.py")
    logger.info("  • Monitoring logic: monitoring.py")
    logger.info("  • Email alerts: email_notifications.py")
    
    logger.info("\n📝 Logs and Monitoring:")
    logger.info("  • Application logs: Check console output")
    logger.info("  • Background monitoring: Automated every 30 seconds")
    logger.info("  • Database metrics: Stored in server_metric table")
    
    logger.info(f"\n✅ Setup completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("="*60)

def main():
    """Main setup function"""
    print("\n🚀 CDN Monitoring Dashboard Setup")
    print("=====================================")
    
    # Run all system checks
    failed_checks = run_system_checks()
    
    if failed_checks:
        logger.error(f"\n❌ Setup failed. The following checks failed:")
        for check in failed_checks:
            logger.error(f"  - {check}")
        logger.error("\nPlease resolve the above issues and run setup again.")
        sys.exit(1)
    
    # Display success information
    display_startup_info()
    
    logger.info("\n🎯 Ready to start the application!")
    logger.info("Run: gunicorn --bind 0.0.0.0:5000 --reuse-port --reload main:app")
    logger.info("Or use the Replit 'Start application' workflow")

if __name__ == "__main__":
    main()