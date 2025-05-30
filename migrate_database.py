#!/usr/bin/env python3
"""
Database Migration Script for CDN Monitoring Dashboard
Adds new columns for bandwidth and stream monitoring features
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError

def get_database_url():
    """Get database URL from environment or prompt user"""
    db_url = os.getenv('DATABASE_URL')
    if not db_url:
        print("DATABASE_URL environment variable not found.")
        print("Please provide database connection details:")
        host = input("Database host (localhost): ") or "localhost"
        port = input("Database port (5432): ") or "5432"
        database = input("Database name (cdnmonitor): ") or "cdnmonitor"
        username = input("Database username (cdnmonitor): ") or "cdnmonitor"
        password = input("Database password: ")
        
        db_url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
    
    return db_url

def check_database_connection(engine):
    """Test database connectivity"""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("✓ Database connection successful")
        return True
    except OperationalError as e:
        print(f"✗ Database connection failed: {e}")
        return False

def check_table_exists(engine, table_name):
    """Check if a table exists"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    return table_name in tables

def get_table_columns(engine, table_name):
    """Get list of columns for a table"""
    inspector = inspect(engine)
    columns = inspector.get_columns(table_name)
    return [col['name'] for col in columns]

def add_column_if_not_exists(engine, table_name, column_name, column_type, default_value=None):
    """Add a column to a table if it doesn't already exist"""
    columns = get_table_columns(engine, table_name)
    
    if column_name in columns:
        print(f"  ✓ Column '{column_name}' already exists in '{table_name}'")
        return False
    
    try:
        default_clause = f" DEFAULT {default_value}" if default_value is not None else ""
        sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}{default_clause}"
        
        with engine.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        
        print(f"  ✓ Added column '{column_name}' to '{table_name}'")
        return True
    except Exception as e:
        print(f"  ✗ Failed to add column '{column_name}' to '{table_name}': {e}")
        return False

def run_migration():
    """Run the database migration"""
    print("CDN Monitoring Dashboard - Database Migration")
    print("=" * 50)
    
    # Get database connection
    db_url = get_database_url()
    engine = create_engine(db_url)
    
    # Test connection
    if not check_database_connection(engine):
        sys.exit(1)
    
    # Check if required tables exist
    required_tables = ['server', 'server_metric', 'alert']
    missing_tables = []
    
    for table in required_tables:
        if not check_table_exists(engine, table):
            missing_tables.append(table)
    
    if missing_tables:
        print(f"✗ Missing required tables: {missing_tables}")
        print("Please run initial database setup first:")
        print("python3 -c \"from app import app, db; db.create_all()\"")
        sys.exit(1)
    
    print("✓ All required tables exist")
    
    # Add new columns for bandwidth and stream monitoring
    print("\nAdding new columns for bandwidth and stream monitoring...")
    
    migrations = [
        ('server_metric', 'bandwidth_in', 'FLOAT', '0.0'),
        ('server_metric', 'bandwidth_out', 'FLOAT', '0.0'),
        ('server_metric', 'stream_count', 'INTEGER', '0'),
    ]
    
    changes_made = False
    for table, column, col_type, default in migrations:
        if add_column_if_not_exists(engine, table, column, col_type, default):
            changes_made = True
    
    # Verify migration
    print("\nVerifying migration...")
    server_metric_columns = get_table_columns(engine, 'server_metric')
    required_columns = ['bandwidth_in', 'bandwidth_out', 'stream_count']
    
    missing_columns = [col for col in required_columns if col not in server_metric_columns]
    
    if missing_columns:
        print(f"✗ Migration incomplete. Missing columns: {missing_columns}")
        sys.exit(1)
    
    print("✓ All required columns are present")
    
    # Create indexes for better performance
    print("\nCreating performance indexes...")
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_server_metric_timestamp ON server_metric(timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_server_metric_server_id ON server_metric(server_id)",
        "CREATE INDEX IF NOT EXISTS idx_server_metric_server_timestamp ON server_metric(server_id, timestamp)",
        "CREATE INDEX IF NOT EXISTS idx_alert_server_id ON alert(server_id)",
        "CREATE INDEX IF NOT EXISTS idx_alert_created_at ON alert(created_at)",
    ]
    
    for index_sql in indexes:
        try:
            with engine.connect() as conn:
                conn.execute(text(index_sql))
                conn.commit()
            print(f"  ✓ Created index")
        except Exception as e:
            if "already exists" in str(e):
                print(f"  ✓ Index already exists")
            else:
                print(f"  ⚠ Index creation warning: {e}")
    
    # Test data insertion
    print("\nTesting new column functionality...")
    try:
        test_sql = """
        SELECT COUNT(*) as total_metrics,
               AVG(bandwidth_in) as avg_bandwidth_in,
               AVG(bandwidth_out) as avg_bandwidth_out,
               AVG(stream_count) as avg_streams
        FROM server_metric 
        WHERE timestamp > NOW() - INTERVAL '1 hour'
        """
        
        with engine.connect() as conn:
            result = conn.execute(text(test_sql)).fetchone()
            print(f"  ✓ Recent metrics: {result.total_metrics} records")
            print(f"  ✓ Average bandwidth in: {result.avg_bandwidth_in:.2f} Mbps")
            print(f"  ✓ Average bandwidth out: {result.avg_bandwidth_out:.2f} Mbps")
            print(f"  ✓ Average streams: {result.avg_streams:.1f}")
            
    except Exception as e:
        print(f"  ⚠ Test query warning: {e}")
    
    if changes_made:
        print("\n" + "=" * 50)
        print("✓ Database migration completed successfully!")
        print("\nNew features available:")
        print("- Separate upload/download bandwidth monitoring")
        print("- Active stream count tracking")
        print("- Enhanced dashboard with real-time metrics")
        print("\nRestart your CDN monitoring service to apply changes:")
        print("sudo systemctl restart cdnmonitor")
    else:
        print("\n" + "=" * 50)
        print("✓ Database is already up to date!")
        print("No migration needed.")

if __name__ == "__main__":
    try:
        run_migration()
    except KeyboardInterrupt:
        print("\n\nMigration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nMigration failed: {e}")
        sys.exit(1)