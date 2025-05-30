#!/usr/bin/env python3
"""
Reset database session and refresh schema cache
"""
import os
from sqlalchemy import create_engine, MetaData, text

# Database URL
db_url = os.environ.get('DATABASE_URL') or 'postgresql://neondb_owner:npg_3gvyLfVEB1GW@ep-steep-wind-a5qt8u3t.us-east-2.aws.neon.tech/neondb?sslmode=require'

print("Connecting to database...")
engine = create_engine(db_url, echo=False)

print("Checking table structure...")
with engine.connect() as conn:
    # Check what columns exist
    result = conn.execute(text("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'server_metric' 
        ORDER BY ordinal_position;
    """))
    
    columns = result.fetchall()
    print(f"Found {len(columns)} columns in server_metric table:")
    for col in columns:
        print(f"  - {col[0]} ({col[1]})")
    
    # Check if bytes_sent exists specifically
    result = conn.execute(text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns 
            WHERE table_name = 'server_metric' 
            AND column_name = 'bytes_sent'
        );
    """))
    
    exists = result.fetchone()[0]
    print(f"\nbytes_sent column exists: {exists}")

print("\nDatabase schema check complete.")