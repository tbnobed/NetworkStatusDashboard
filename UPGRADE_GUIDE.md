# CDN Monitoring Dashboard - Upgrade Guide

This guide helps existing installations upgrade to include the new bandwidth monitoring and stream count features.

## What's New

- **Separate Bandwidth Tracking**: Upload and download bandwidth displayed as distinct metrics
- **Stream Count Monitoring**: Real-time tracking of active streams per server and total
- **Enhanced Dashboard Layout**: Reorganized statistics in two clean rows
- **Auto-refresh Improvements**: All metrics update every 30 seconds automatically
- **Database Schema Updates**: New columns for bandwidth and stream data

## Pre-Upgrade Checklist

1. **Backup your database**:
   ```bash
   sudo -u postgres pg_dump cdnmonitor > /backup/cdnmonitor_pre_upgrade_$(date +%Y%m%d).sql
   ```

2. **Backup application files**:
   ```bash
   sudo tar -czf /backup/cdnmonitor_app_pre_upgrade_$(date +%Y%m%d).tar.gz /opt/cdnmonitor
   ```

3. **Note current server configurations** for reference

## Upgrade Steps

### 1. Update Application Files

Replace all application files with the new version, maintaining your existing `.env` configuration file.

### 2. Install New Dependencies

```bash
cd /opt/cdnmonitor
sudo -u www-data bash
source venv/bin/activate
pip install -r deployment_requirements.txt
exit
```

### 3. Run Database Migration

The application includes a migration script to add new database columns:

```bash
cd /opt/cdnmonitor
sudo -u www-data bash
source venv/bin/activate

# Run the migration script
python3 migrate_database.py
```

The migration will:
- Add `bandwidth_in` column to `server_metric` table
- Add `bandwidth_out` column to `server_metric` table  
- Add `stream_count` column to `server_metric` table
- Create performance indexes
- Verify the migration completed successfully

### 4. Update Environment Configuration

Ensure your `.env` file includes the new configuration options:

```bash
sudo nano /opt/cdnmonitor/.env
```

Add if missing:
```env
# Monitoring Configuration
MONITORING_INTERVAL=30
ALERT_RETENTION_DAYS=30
```

### 5. Update Service Configuration

Replace the systemd service file:

```bash
sudo cp cdnmonitor.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### 6. Restart Services

```bash
# Restart the monitoring service
sudo systemctl restart cdnmonitor

# Check service status
sudo systemctl status cdnmonitor

# Restart nginx if needed
sudo systemctl restart nginx
```

## Verification

### 1. Check Database Schema

Verify new columns exist:

```bash
sudo -u postgres psql cdnmonitor -c "\d server_metric"
```

You should see `bandwidth_in`, `bandwidth_out`, and `stream_count` columns.

### 2. Test Data Collection

Check that new metrics are being collected:

```bash
sudo -u postgres psql cdnmonitor -c "
SELECT hostname, bandwidth_in, bandwidth_out, stream_count, timestamp 
FROM server_metric 
JOIN server ON server_metric.server_id = server.id 
ORDER BY timestamp DESC 
LIMIT 5;"
```

### 3. Verify Dashboard

1. Open your dashboard in a browser
2. Confirm you see the new layout with 7 statistics cards in 2 rows
3. Check that bandwidth values show actual Mbps measurements
4. Verify stream counts are displaying correctly
5. Watch for automatic updates every 30 seconds

## Troubleshooting

### Migration Issues

If the migration script fails:

```bash
# Manual column addition
sudo -u postgres psql cdnmonitor -c "
ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS bandwidth_in FLOAT DEFAULT 0;
ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS bandwidth_out FLOAT DEFAULT 0;
ALTER TABLE server_metric ADD COLUMN IF NOT EXISTS stream_count INTEGER DEFAULT 0;
"
```

### Service Won't Start

Check logs for errors:

```bash
sudo journalctl -u cdnmonitor -f
```

Common issues:
- Missing `.env` file - ensure database URL is properly configured
- Permission issues - verify `/opt/cdnmonitor` is owned by `www-data`
- Port conflicts - ensure port 5000 is available

### Dashboard Not Updating

1. Check browser console for JavaScript errors (F12)
2. Verify API endpoints are responding:
   ```bash
   curl http://localhost:5000/api/dashboard/stats
   ```
3. Check monitoring logs:
   ```bash
   sudo journalctl -u cdnmonitor | grep -i monitoring
   ```

### Missing Bandwidth Data

1. Verify SRS server API endpoints are correctly configured
2. Check API authentication tokens are valid
3. Test API connectivity manually:
   ```bash
   curl -H "Authorization: Bearer YOUR_TOKEN" http://server-ip:1985/api/v1/streams
   ```

## Rollback Procedure

If you need to rollback:

1. **Stop the service**:
   ```bash
   sudo systemctl stop cdnmonitor
   ```

2. **Restore database backup**:
   ```bash
   sudo -u postgres psql cdnmonitor < /backup/cdnmonitor_pre_upgrade_YYYYMMDD.sql
   ```

3. **Restore application files**:
   ```bash
   sudo rm -rf /opt/cdnmonitor
   sudo tar -xzf /backup/cdnmonitor_app_pre_upgrade_YYYYMMDD.tar.gz -C /
   ```

4. **Restart with old configuration**:
   ```bash
   sudo systemctl start cdnmonitor
   ```

## Post-Upgrade Benefits

After successful upgrade, you'll have:

- **Enhanced Monitoring**: Detailed bandwidth analysis with separate upload/download metrics
- **Stream Analytics**: Real-time stream count tracking across your CDN infrastructure  
- **Improved Performance**: Optimized database queries with new indexes
- **Better User Experience**: Auto-refreshing dashboard with organized layout
- **Future-Ready**: Database schema prepared for additional monitoring features

## Support

If you encounter issues during upgrade:

1. Check the troubleshooting section above
2. Review service logs: `sudo journalctl -u cdnmonitor -f`
3. Verify database connectivity and permissions
4. Ensure all API endpoints and authentication are properly configured

The upgrade maintains full backward compatibility with existing server configurations while adding the new bandwidth and stream monitoring capabilities.