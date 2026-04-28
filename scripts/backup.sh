#!/bin/bash
# SnapTravels Backup Script

BACKUP_DIR="/var/backups/snaptravels"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp snaptravels.db $BACKUP_DIR/snaptravels_$DATE.db

# Backup application
tar -czf $BACKUP_DIR/snaptravels_app_$DATE.tar.gz --exclude='venv' --exclude='__pycache__' .

# Keep only last 7 days
find $BACKUP_DIR -name "snaptravels_*" -mtime +7 -delete

echo "✅ Backup completed: $DATE"
