#!/usr/bin/env python3
"""
Restore server configurations that were lost during database reset
"""
from app import app, db
from models import Server

with app.app_context():
    # Add OTV Svr1 (Origin server)
    server1 = Server(
        hostname='OTV Svr1',
        ip_address='cdn1.obedtv.live',
        port=2022,
        role='origin',
        status='up',
        api_endpoint='http://cdn1.obedtv.live:2022/api/v1/streams',
        api_type='srs',
        api_token='Bearer your_token_here'  # You'll need to update this
    )
    
    # Add CDN3 Srv1 (Edge server) 
    server2 = Server(
        hostname='CDN3 Srv1',
        ip_address='98.191.147.191',
        port=2022,
        role='edge',
        status='up',
        api_endpoint='http://98.191.147.191:2022/api/v1/streams',
        api_type='srs',
        api_token='Bearer your_token_here'  # You'll need to update this
    )
    
    db.session.add(server1)
    db.session.add(server2)
    db.session.commit()
    
    print("Server configurations restored:")
    print(f"- {server1.hostname} ({server1.ip_address}:{server1.port}) - {server1.role}")
    print(f"- {server2.hostname} ({server2.ip_address}:{server2.port}) - {server2.role}")