-- ==================================================================
-- PRODUCTION DATABASE MIGRATION SCRIPT
-- ==================================================================
-- Purpose: Make Alert.server_id nullable and add proper CASCADE behavior
-- Changes: 
--   1. ALTER alert.server_id to allow NULL values
--   2. Update FK constraint to ON DELETE SET NULL
-- Author: CDN Monitoring Dashboard
-- Date: 2025-09-20
-- ==================================================================

-- SAFETY SETTINGS
-- Set safe timeouts to prevent long-running locks
SET lock_timeout = '5s';
SET statement_timeout = '60s';

-- STEP 1: PRE-MIGRATION CHECKS
-- ==================================================================
\echo '=== PRE-MIGRATION CHECKS ==='

-- Check current schema state
\echo 'Current alert table schema:'
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'alert' 
    AND column_name = 'server_id';

-- Check existing foreign key constraints
\echo 'Current foreign key constraints:'
SELECT 
    tc.constraint_name, 
    tc.table_name, 
    kcu.column_name, 
    ccu.table_name AS foreign_table_name,
    ccu.column_name AS foreign_column_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc 
JOIN information_schema.key_column_usage AS kcu
    ON tc.constraint_name = kcu.constraint_name
    AND tc.table_schema = kcu.table_schema
JOIN information_schema.constraint_column_usage AS ccu
    ON ccu.constraint_name = tc.constraint_name
    AND ccu.table_schema = tc.table_schema
LEFT JOIN information_schema.referential_constraints AS rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = 'alert'
    AND kcu.column_name = 'server_id';

-- Count affected records
\echo 'Current alert records that reference servers:'
SELECT 
    COUNT(*) as total_alerts,
    COUNT(server_id) as alerts_with_server,
    COUNT(*) - COUNT(server_id) as alerts_without_server
FROM alert;

-- STEP 2: MIGRATION EXECUTION
-- ==================================================================
\echo '=== STARTING MIGRATION ==='

BEGIN;

\echo 'Step 1: Making server_id column nullable...'
-- Allow NULL values in server_id column
ALTER TABLE alert ALTER COLUMN server_id DROP NOT NULL;

\echo 'Step 2: Updating foreign key constraint...'
-- Remove existing foreign key constraint if it exists
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints tc
        WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_name = 'alert'
            AND tc.constraint_name = 'alert_server_id_fkey'
    ) THEN
        \echo 'Dropping existing foreign key constraint...';
        ALTER TABLE alert DROP CONSTRAINT alert_server_id_fkey;
    END IF;
END$$;

-- Add new foreign key constraint with ON DELETE SET NULL
\echo 'Creating new foreign key constraint with ON DELETE SET NULL...'
ALTER TABLE alert
    ADD CONSTRAINT alert_server_id_fkey
    FOREIGN KEY (server_id) REFERENCES server(id)
    ON DELETE SET NULL;

-- STEP 3: POST-MIGRATION VERIFICATION
-- ==================================================================
\echo '=== POST-MIGRATION VERIFICATION ==='

-- Verify column is now nullable
\echo 'Verifying server_id is now nullable:'
SELECT 
    column_name, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'alert' 
    AND column_name = 'server_id';

-- Verify foreign key constraint
\echo 'Verifying new foreign key constraint:'
SELECT 
    tc.constraint_name,
    rc.delete_rule
FROM information_schema.table_constraints AS tc
LEFT JOIN information_schema.referential_constraints AS rc
    ON tc.constraint_name = rc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' 
    AND tc.table_name = 'alert'
    AND tc.constraint_name = 'alert_server_id_fkey';

-- Check data integrity
\echo 'Verifying data integrity:'
SELECT 
    COUNT(*) as total_alerts,
    COUNT(server_id) as alerts_with_server,
    COUNT(*) - COUNT(server_id) as alerts_without_server
FROM alert;

COMMIT;

\echo '=== MIGRATION COMPLETED SUCCESSFULLY ==='

-- STEP 4: FUNCTIONAL TEST (OPTIONAL - RUN MANUALLY)
-- ==================================================================
-- \echo '=== FUNCTIONAL TEST (MANUAL) ==='
-- 
-- -- Create a test server
-- INSERT INTO server (hostname, ip_address, port, role, status, created_at, updated_at)
-- VALUES ('test-migration-server', '127.0.0.1', 8080, 'edge', 'down', NOW(), NOW());
-- 
-- -- Get the test server ID
-- SELECT id as test_server_id FROM server WHERE hostname = 'test-migration-server';
-- 
-- -- Create a test alert for this server
-- INSERT INTO alert (server_id, alert_type, severity, message, created_at)
-- SELECT id, 'test_alert', 'info', 'Migration test alert', NOW()
-- FROM server WHERE hostname = 'test-migration-server';
-- 
-- -- Delete the test server (should set alert.server_id to NULL)
-- DELETE FROM server WHERE hostname = 'test-migration-server';
-- 
-- -- Verify alert still exists with NULL server_id
-- SELECT id, server_id, alert_type, message FROM alert WHERE alert_type = 'test_alert';
-- 
-- -- Clean up test alert
-- DELETE FROM alert WHERE alert_type = 'test_alert';
-- 
-- \echo '=== FUNCTIONAL TEST COMPLETED ==='