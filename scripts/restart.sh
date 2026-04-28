#!/bin/bash
# Restart SnapTravels services

echo "🔄 Restarting SnapTravels..."
sudo systemctl restart snaptravels
sudo systemctl restart nginx
echo "✅ Services restarted!"
