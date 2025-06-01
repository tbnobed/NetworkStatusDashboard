import os
import sys
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from app import app
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_alert_email(alert, server):
    """Send email notification for critical alerts"""
    sendgrid_key = os.environ.get('SENDGRID_API_KEY')
    
    if not sendgrid_key:
        logger.error('SENDGRID_API_KEY environment variable not set')
        return False
    
    try:
        sg = SendGridAPIClient(sendgrid_key)
        
        # Email configuration
        from_email = Email("alerts@obedtv.com", "OBTV CDN Alert System")
        to_email = To("obedtest@tbn.tv")
        
        # Create subject based on alert severity
        severity_labels = {
            'critical': '🚨 CRITICAL',
            'error': '⚠️ ERROR',
            'warning': '⚠️ WARNING',
            'info': 'ℹ️ INFO'
        }
        
        severity_label = severity_labels.get(alert.severity, alert.severity.upper())
        subject = f"{severity_label} Alert: {server.hostname} - {alert.alert_type}"
        
        # Create HTML email content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>OBTV CDN Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #007bff, #0056b3); color: white; padding: 20px; text-align: center; }}
                .header h1 {{ margin: 0; font-size: 24px; }}
                .content {{ padding: 30px; }}
                .alert-box {{ border-left: 4px solid; padding: 15px; margin: 20px 0; border-radius: 4px; }}
                .critical {{ border-color: #dc3545; background-color: #f8d7da; }}
                .error {{ border-color: #fd7e14; background-color: #fff3cd; }}
                .warning {{ border-color: #ffc107; background-color: #fff3cd; }}
                .info {{ border-color: #17a2b8; background-color: #d1ecf1; }}
                .details {{ background-color: #f8f9fa; padding: 15px; border-radius: 4px; margin: 20px 0; }}
                .details table {{ width: 100%; border-collapse: collapse; }}
                .details td {{ padding: 8px; border-bottom: 1px solid #dee2e6; }}
                .details td:first-child {{ font-weight: bold; width: 30%; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 12px; }}
                .btn {{ display: inline-block; padding: 10px 20px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 10px 0; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>OBTV CDN Alert</h1>
                    <p>Critical Infrastructure Notification</p>
                </div>
                
                <div class="content">
                    <div class="alert-box {alert.severity}">
                        <h2 style="margin: 0 0 10px 0; color: #333;">{severity_label} Alert</h2>
                        <p style="margin: 0; font-size: 16px;"><strong>{alert.message}</strong></p>
                    </div>
                    
                    <div class="details">
                        <h3 style="margin: 0 0 15px 0;">Alert Details</h3>
                        <table>
                            <tr><td>Server:</td><td>{server.hostname}</td></tr>
                            <tr><td>IP Address:</td><td>{server.ip_address}</td></tr>
                            <tr><td>Role:</td><td>{server.role.title()}</td></tr>
                            <tr><td>Alert Type:</td><td>{alert.alert_type}</td></tr>
                            <tr><td>Severity:</td><td>{alert.severity.title()}</td></tr>
                            <tr><td>Time:</td><td>{alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}</td></tr>
                            <tr><td>Status:</td><td>{'Acknowledged' if alert.acknowledged else 'Active'}</td></tr>
                        </table>
                    </div>
                    
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="http://localhost:5000" class="btn">View Dashboard</a>
                    </div>
                    
                    <div style="border-top: 1px solid #dee2e6; padding-top: 20px; margin-top: 30px; font-size: 14px; color: #6c757d;">
                        <p><strong>Immediate Actions Recommended:</strong></p>
                        <ul style="margin: 10px 0;">
                            <li>Check server connectivity and performance metrics</li>
                            <li>Verify service status and error logs</li>
                            <li>Contact technical team if issue persists</li>
                            <li>Acknowledge alert once resolved</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p>This is an automated alert from the OBTV CDN Monitoring System</p>
                    <p>For technical support, please contact your system administrator</p>
                    <p>&copy; 2025 OBTV. All rights reserved.</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        # Create plain text version
        text_content = f"""
OBTV CDN ALERT - {severity_label}

Server: {server.hostname} ({server.ip_address})
Alert: {alert.message}
Type: {alert.alert_type}
Severity: {alert.severity}
Time: {alert.created_at.strftime('%Y-%m-%d %H:%M:%S UTC')}
Status: {'Acknowledged' if alert.acknowledged else 'Active'}

Please check the dashboard: http://localhost:5000

This is an automated alert from the OBTV CDN Monitoring System.
        """
        
        # Create mail object
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content,
            plain_text_content=text_content
        )
        
        # Send email
        response = sg.send(message)
        logger.info(f"Alert email sent successfully. Status code: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"SendGrid error: {e}")
        return False

def should_send_email_alert(alert):
    """Determine if an alert should trigger an email notification"""
    # Only send emails for critical and error alerts
    return alert.severity in ['critical', 'error']

def send_server_down_alert(server):
    """Send immediate notification when a server goes down"""
    sendgrid_key = os.environ.get('SENDGRID_API_KEY')
    
    if not sendgrid_key:
        logger.error('SENDGRID_API_KEY environment variable not set')
        return False
    
    try:
        sg = SendGridAPIClient(sendgrid_key)
        
        from_email = Email("alerts@obedtv.com", "OBTV CDN Alert System")
        to_email = To("obedtest@tbn.tv")
        
        subject = f"🚨 CRITICAL: Server {server.hostname} is DOWN"
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Server Down Alert</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 600px; margin: 0 auto; background-color: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                .header {{ background: linear-gradient(135deg, #dc3545, #c82333); color: white; padding: 20px; text-align: center; }}
                .content {{ padding: 30px; }}
                .critical-alert {{ background-color: #f8d7da; border: 2px solid #dc3545; padding: 20px; border-radius: 8px; text-align: center; margin: 20px 0; }}
                .btn {{ display: inline-block; padding: 12px 24px; background-color: #dc3545; color: white; text-decoration: none; border-radius: 4px; margin: 15px 0; font-weight: bold; }}
                .footer {{ background-color: #f8f9fa; padding: 20px; text-align: center; color: #6c757d; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🚨 CRITICAL ALERT</h1>
                    <p>Server Outage Detected</p>
                </div>
                
                <div class="content">
                    <div class="critical-alert">
                        <h2 style="color: #721c24; margin: 0 0 15px 0;">SERVER DOWN</h2>
                        <p style="font-size: 18px; margin: 0;"><strong>{server.hostname}</strong> is not responding</p>
                        <p style="margin: 10px 0 0 0;">IP: {server.ip_address} | Role: {server.role.title()}</p>
                    </div>
                    
                    <div style="text-align: center;">
                        <a href="http://localhost:5000" class="btn">CHECK DASHBOARD IMMEDIATELY</a>
                    </div>
                    
                    <div style="background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 20px 0;">
                        <h3 style="color: #856404; margin: 0 0 10px 0;">Immediate Actions Required:</h3>
                        <ul style="color: #856404; margin: 0;">
                            <li>Verify server status and connectivity</li>
                            <li>Check network infrastructure</li>
                            <li>Contact technical team immediately</li>
                            <li>Monitor other servers for cascade failures</li>
                        </ul>
                    </div>
                </div>
                
                <div class="footer">
                    <p><strong>This is a critical automated alert from OBTV CDN Monitoring</strong></p>
                    <p>Time: {server.updated_at.strftime('%Y-%m-%d %H:%M:%S UTC') if server.updated_at else 'Unknown'}</p>
                </div>
            </div>
        </body>
        </html>
        """
        
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            html_content=html_content
        )
        
        response = sg.send(message)
        logger.info(f"Server down alert sent successfully. Status code: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send server down alert: {e}")
        return False