-- ==================================================================
-- FIXED PRODUCTION DATABASE MIGRATION SCRIPT
-- ==================================================================
-- Purpose: Make Alert.server_id nullable and add proper CASCADE behavior
-- Fixed: Removed \echo commands from DO blocks that caused syntax errors
-- ==================================================================

-- SAFETY SETTINGS
SET lock_timeout = '5s';
SET statement_timeout = '60s';

-- STEP 1: PRE-MIGRATION CHECKS
\echo 'Current alert table schema:'
SELECT 
    column_name, 
    data_type, 
    is_nullable, 
    column_default
FROM information_schema.columns 
WHERE table_name = 'alert' 
    AND column_name = 'server_id';

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

-- STEP 2: MIGRATION EXECUTION
\echo 'Starting migration...'

BEGIN;

\echo 'Making server_id column nullable...'
ALTER TABLE alert ALTER COLUMN server_id DROP NOT NULL;

\echo 'Dropping existing foreign key constraint...'
-- Remove existing foreign key constraint
ALTER TABLE alert DROP CONSTRAINT IF EXISTS alert_server_id_fkey;

\echo 'Creating new foreign key constraint with ON DELETE SET NULL...'
-- Add new foreign key constraint with ON DELETE SET NULL
ALTER TABLE alert
    ADD CONSTRAINT alert_server_id_fkey
    FOREIGN KEY (server_id) REFERENCES server(id)
    ON DELETE SET NULL;

-- STEP 3: VERIFICATION
\echo 'Verifying server_id is now nullable:'
SELECT 
    column_name, 
    is_nullable 
FROM information_schema.columns 
WHERE table_name = 'alert' 
    AND column_name = 'server_id';

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

COMMIT;

\echo 'Migration completed successfully!'