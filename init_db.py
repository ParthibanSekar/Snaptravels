
#!/usr/bin/env python3
"""
SnapTravels Database Initialization Script
=========================================

This script initializes the database and creates all required tables and seed data.
Run this script to set up your SnapTravels database from scratch.

Usage:
    python init_db.py

Features:
- Creates all database tables
- Seeds with sample flights, hotels, and users
- Safe to run multiple times (won't duplicate data)
- Provides detailed feedback on the initialization process
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def init_database():
    """Initialize the database with tables and seed data"""
    
    print("🚀 SnapTravels Database Initialization")
    print("=" * 50)
    
    # Remove existing database file to ensure clean start
    db_file = 'snaptravels.db'
    if os.path.exists(db_file):
        print("🗑️  Removing existing database...")
        os.remove(db_file)
        print("✅ Existing database removed")
    
    # Also remove any instance folder databases
    instance_db = 'instance/snaptravels.db'
    if os.path.exists(instance_db):
        print("🗑️  Removing instance database...")
        os.remove(instance_db)
        print("✅ Instance database removed")
    
    # Import after potential database removal
    from app import create_app, db
    from app.models import User, Flight, Hotel, Booking, BookingItem
    from app.services.seeder import seed_database
    
    # Create Flask app
    app = create_app()
    
    with app.app_context():
        try:
            # Create all tables
            print("🔧 Creating database tables...")
            db.create_all()
            print("✅ All tables created successfully")
            
            # Verify tables were created
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()
            print(f"📋 Created tables: {', '.join(tables)}")
            
            # Seed the database with initial data
            print("🌱 Seeding database with initial data...")
            seed_database()
            print("✅ Database seeded successfully")
            
            # Verify data was inserted
            print("\n📊 Database Summary:")
            print(f"   • Users: {User.query.count()}")
            print(f"   • Flights: {Flight.query.count()}")
            print(f"   • Hotels: {Hotel.query.count()}")
            print(f"   • Bookings: {Booking.query.count()}")
            
            # Display test accounts
            print("\n👤 Test Accounts Created:")
            print("   • Admin: admin@snaptravels.online / Admin@123")
            print("   • User:  parthiban@snaptravels.online / Test@123")
            
            # Display sample data info
            print("\n🏨 Sample Data Overview:")
            budget_hotels = Hotel.query.filter(Hotel.price_per_night < 3000).count()
            mid_range_hotels = Hotel.query.filter(
                Hotel.price_per_night >= 3000, 
                Hotel.price_per_night < 10000
            ).count()
            luxury_hotels = Hotel.query.filter(Hotel.price_per_night >= 10000).count()
            
            print(f"   • Budget Hotels (< ₹3,000): {budget_hotels}")
            print(f"   • Mid-range Hotels (₹3,000-₹10,000): {mid_range_hotels}")
            print(f"   • Luxury Hotels (> ₹10,000): {luxury_hotels}")
            
            domestic_flights = Flight.query.filter(~Flight.destination.contains('Dubai')).filter(~Flight.destination.contains('London')).count()
            international_flights = Flight.query.filter(
                (Flight.destination.contains('Dubai')) | 
                (Flight.destination.contains('London'))
            ).count()
            
            print(f"   • Domestic Flights: {domestic_flights}")
            print(f"   • International Flights: {international_flights}")
            
            print("\n🎉 Database initialization completed successfully!")
            print("🌐 You can now start the application with: python main.py")
            
        except Exception as e:
            print(f"❌ Error during database initialization: {str(e)}")
            db.session.rollback()
            return False
    
    return True

def verify_database():
    """Verify that the database is properly initialized"""
    
    print("\n🔍 Verifying database integrity...")
    
    from app import create_app, db
    from app.models import User, Flight, Hotel, Booking, BookingItem
    
    app = create_app()
    
    with app.app_context():
        try:
            # Check if all tables exist
            inspector = db.inspect(db.engine)
            existing_tables = inspector.get_table_names()
            required_tables = ['user', 'flight', 'hotel', 'booking', 'booking_item']
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            
            if missing_tables:
                print(f"❌ Missing tables: {', '.join(missing_tables)}")
                return False
            
            # Check if data exists
            if User.query.count() == 0:
                print("❌ No users found in database")
                return False
                
            if Flight.query.count() == 0:
                print("❌ No flights found in database")
                return False
                
            if Hotel.query.count() == 0:
                print("❌ No hotels found in database")
                return False
            
            # Test admin user login
            admin_user = User.query.filter_by(email='admin@snaptravels.online').first()
            if not admin_user or not admin_user.check_password('Admin@123'):
                print("❌ Admin user authentication failed")
                return False
            
            # Test regular user login
            test_user = User.query.filter_by(email='parthiban@snaptravels.online').first()
            if not test_user or not test_user.check_password('Test@123'):
                print("❌ Test user authentication failed")
                return False
            
            print("✅ Database verification completed successfully")
            print("✅ All tables exist and contain data")
            print("✅ User authentication working correctly")
            
            return True
            
        except Exception as e:
            print(f"❌ Database verification failed: {str(e)}")
            return False

def reset_database():
    """Reset the database (drop and recreate everything)"""
    
    print("⚠️  WARNING: This will delete all existing data!")
    response = input("Are you sure you want to reset the database? (yes/no): ")
    
    if response.lower() not in ['yes', 'y']:
        print("❌ Database reset cancelled")
        return False
    
    print("🔄 Resetting database...")
    return init_database()

def show_help():
    """Display help information"""
    
    print("SnapTravels Database Initialization Script")
    print("=" * 50)
    print("Usage: python init_db.py [command]")
    print("")
    print("Commands:")
    print("  init     Initialize database with tables and seed data (default)")
    print("  verify   Verify database integrity and data")
    print("  reset    Reset database (delete all data and reinitialize)")
    print("  help     Show this help message")
    print("")
    print("Examples:")
    print("  python init_db.py           # Initialize database")
    print("  python init_db.py init      # Initialize database")
    print("  python init_db.py verify    # Verify database")
    print("  python init_db.py reset     # Reset database")

def main():
    """Main function to handle command line arguments"""
    
    # Get command from arguments
    command = sys.argv[1] if len(sys.argv) > 1 else 'init'
    
    if command == 'init':
        success = init_database()
        if success:
            verify_database()
        sys.exit(0 if success else 1)
        
    elif command == 'verify':
        success = verify_database()
        sys.exit(0 if success else 1)
        
    elif command == 'reset':
        success = reset_database()
        if success:
            verify_database()
        sys.exit(0 if success else 1)
        
    elif command == 'help':
        show_help()
        sys.exit(0)
        
    else:
        print(f"❌ Unknown command: {command}")
        print("Use 'python init_db.py help' for usage information")
        sys.exit(1)

if __name__ == '__main__':
    main()
