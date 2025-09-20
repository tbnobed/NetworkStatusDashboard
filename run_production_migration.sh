#!/bin/bash

# ==================================================================
# PRODUCTION DATABASE MIGRATION RUNNER
# ==================================================================
# Purpose: Safely run database migrations on production
# Author: CDN Monitoring Dashboard
# Date: 2025-09-20
# ==================================================================

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKUP_DIR="./backups"
MIGRATION_FILE="production_migration.sql"
TIMESTAMP=$(date '+%Y%m%d_%H%M%S')

echo -e "${BLUE}===================================================================${NC}"
echo -e "${BLUE}CDN MONITORING DASHBOARD - PRODUCTION MIGRATION${NC}"
echo -e "${BLUE}===================================================================${NC}"

# Step 1: Pre-flight checks
echo -e "\n${YELLOW}📋 PRE-FLIGHT CHECKS${NC}"

# Check if migration file exists
if [[ ! -f "$MIGRATION_FILE" ]]; then
    echo -e "${RED}❌ Error: Migration file '$MIGRATION_FILE' not found!${NC}"
    exit 1
fi

# Check if DATABASE_URL is set
if [[ -z "$DATABASE_URL" ]]; then
    echo -e "${RED}❌ Error: DATABASE_URL environment variable is not set!${NC}"
    echo -e "${YELLOW}💡 Please set your production database URL first:${NC}"
    echo -e "   export DATABASE_URL='postgresql://user:pass@host:port/dbname'"
    exit 1
fi

echo -e "${GREEN}✅ Migration file found${NC}"
echo -e "${GREEN}✅ DATABASE_URL is configured${NC}"

# Step 2: Create backup directory
echo -e "\n${YELLOW}📁 PREPARING BACKUP DIRECTORY${NC}"
mkdir -p "$BACKUP_DIR"
echo -e "${GREEN}✅ Backup directory ready: $BACKUP_DIR${NC}"

# Step 3: Confirmation prompt
echo -e "\n${YELLOW}⚠️  WARNING: PRODUCTION DATABASE MIGRATION${NC}"
echo -e "${YELLOW}This will modify your production database schema.${NC}"
echo -e "${YELLOW}Changes include:${NC}"
echo -e "  • Making alert.server_id column nullable"
echo -e "  • Adding ON DELETE SET NULL constraint"
echo -e ""
echo -e "${BLUE}Database: $(echo $DATABASE_URL | sed 's/postgresql:\/\/[^@]*@/postgresql:\/\/***:***@/')${NC}"
echo -e ""

read -p "Are you sure you want to proceed? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo -e "${YELLOW}Migration cancelled by user.${NC}"
    exit 0
fi

# Step 4: Create database backup
echo -e "\n${YELLOW}💾 CREATING DATABASE BACKUP${NC}"
BACKUP_FILE="$BACKUP_DIR/cdn_monitoring_backup_$TIMESTAMP.sql"

echo -e "Creating backup: $BACKUP_FILE"
if command -v pg_dump >/dev/null 2>&1; then
    pg_dump "$DATABASE_URL" > "$BACKUP_FILE"
    echo -e "${GREEN}✅ Database backup created successfully${NC}"
else
    echo -e "${YELLOW}⚠️  Warning: pg_dump not found. Please ensure you have a recent database backup.${NC}"
    read -p "Do you have a recent backup of your production database? (yes/no): " -r
    if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
        echo -e "${RED}❌ Please create a backup before proceeding with the migration.${NC}"
        exit 1
    fi
    echo -e "${GREEN}✅ User confirmed existing backup${NC}"
fi

# Step 5: Run the migration
echo -e "\n${YELLOW}🚀 RUNNING DATABASE MIGRATION${NC}"
echo -e "Executing: $MIGRATION_FILE"

if psql "$DATABASE_URL" -f "$MIGRATION_FILE"; then
    echo -e "\n${GREEN}✅ MIGRATION COMPLETED SUCCESSFULLY!${NC}"
else
    echo -e "\n${RED}❌ MIGRATION FAILED!${NC}"
    if [[ -f "$BACKUP_FILE" ]]; then
        echo -e "${YELLOW}💡 To restore from backup, run:${NC}"
        echo -e "   psql \"$DATABASE_URL\" < \"$BACKUP_FILE\""
    fi
    exit 1
fi

# Step 6: Post-migration recommendations
echo -e "\n${BLUE}===================================================================${NC}"
echo -e "${GREEN}🎉 MIGRATION COMPLETED SUCCESSFULLY!${NC}"
echo -e "${BLUE}===================================================================${NC}"

echo -e "\n${YELLOW}📋 NEXT STEPS:${NC}"
echo -e "1. ${GREEN}✅ Database schema updated${NC}"
echo -e "2. ${YELLOW}🔄 Restart your application to apply changes${NC}"
echo -e "3. ${YELLOW}🧪 Test server deletion functionality${NC}"
echo -e "4. ${YELLOW}👀 Monitor application logs for any issues${NC}"

echo -e "\n${YELLOW}📁 BACKUP INFORMATION:${NC}"
if [[ -f "$BACKUP_FILE" ]]; then
    echo -e "Backup saved to: ${GREEN}$BACKUP_FILE${NC}"
    echo -e "Backup size: $(du -h "$BACKUP_FILE" | cut -f1)"
fi

echo -e "\n${BLUE}Migration completed at: $(date)${NC}"
echo -e "${BLUE}===================================================================${NC}"