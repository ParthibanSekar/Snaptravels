from app.models import Flight, Hotel, User
from app import db
import hashlib, re
from datetime import datetime, timedelta
import random


def _slugify(text):
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    text = re.sub(r'[\s_-]+', '-', text)
    return text.strip('-')


def seed_blog():
    """Seed travel guide blog posts — safe to call repeatedly (skips duplicates)."""
    from app.models import BlogPost

    POSTS = [
        {
            'title': 'Goa Beach Guide: Best Beaches, Shacks & Hidden Gems',
            'destination': 'Goa', 'category': 'Beach',
            'summary': "From the party vibes of Baga to the serene shores of Palolem, discover everything Goa has to offer — complete with food tips, nightlife, and the best time to visit.",
            'cover_image': '/static/images/destinations/goa.jpg',
            'author_name': 'SnapTravels Team', 'views': 1842, 'days_ago': 5,
            'tags': ['beach', 'goa', 'nightlife', 'seafood'],
            'content': '<p>Goa packs sun, sea, culture, and cuisine into a tiny coastal strip. Whether you\'re a backpacker or a honeymooner, Goa delivers. North Goa (Baga, Calangute, Anjuna) is where the action is — beach clubs, flea markets, all-night parties. South Goa (Palolem, Agonda) is quieter and more peaceful.</p><h3>Top Beaches</h3><ul><li><strong>Palolem</strong> — crescent-shaped, calm water, perfect for kayaking</li><li><strong>Anjuna</strong> — Wednesday flea market, rocky coves</li><li><strong>Arambol</strong> — hippy haven, drum circles at sunset</li></ul><p>Best time: November to February. Fly into Dabolim Airport (GOI).</p>',
        },
        {
            'title': 'Kerala Backwaters: The Complete Houseboat Experience',
            'destination': 'Kerala', 'category': 'Nature',
            'summary': 'Drift through 900 km of canals on a traditional kettuvallam. Here is everything you need to plan the perfect Kerala backwaters houseboat trip.',
            'cover_image': '/static/images/destinations/kerala.jpg',
            'author_name': 'Priya Nair', 'views': 2310, 'days_ago': 12,
            'tags': ['kerala', 'houseboat', 'backwaters', 'alleppey'],
            'content': '<p>The Kerala backwaters are a network of canals, rivers, lakes, and inlets. Gliding through Alleppey on a houseboat at sunrise is one of those rare travel experiences that lives up to every expectation.</p><h3>Houseboat Tips</h3><ul><li>Book in advance — good boats fill up fast in November–January</li><li>Rates range ₹6,000–₹25,000/night; always compare 3 options</li><li>Meals included — the onboard cook makes fresh Kerala fish curry and appam</li></ul><p>Fly into Kochi (COK). Take a taxi to Alleppey (1.5 hours).</p>',
        },
        {
            'title': 'Rajasthan Road Trip: Jaipur → Jodhpur → Jaisalmer in 10 Days',
            'destination': 'Rajasthan', 'category': 'Road Trip',
            'summary': "The golden triangle of Rajasthan is one of India's great road trips — palaces, sand dunes, camel safaris, and the bluest city on earth.",
            'cover_image': '/static/images/destinations/rajasthan.jpg',
            'author_name': 'Arjun Sharma', 'views': 3105, 'days_ago': 18,
            'tags': ['rajasthan', 'jaipur', 'jodhpur', 'jaisalmer', 'road trip'],
            'content': '<p>Few journeys in India match driving through Rajasthan — Mughal forts dissolving into sand dunes, vivid turbans against ochre walls. This 10-day itinerary covers the three jewels: the Pink City, the Blue City, and the Golden City.</p><h3>Days 1–3: Jaipur</h3><p>Start at Amber Fort at 8 AM. Spend the afternoon at City Palace. Day 2: Hawa Mahal at sunrise, then Bapu Bazaar.</p><h3>Days 4–6: Jodhpur</h3><p>Anchored by the breathtaking Mehrangarh Fort. The blue-painted old city beneath it is magical.</p><h3>Days 7–10: Jaisalmer</h3><p>The Jaisalmer Fort is a living fort. Spend an evening at Sam Sand Dunes for a camel safari.</p>',
        },
        {
            'title': 'Manali in December: Snow, Solang Valley & the Rohtang Pass',
            'destination': 'Manali', 'category': 'Mountains',
            'summary': "December in Manali means heavy snowfall, ski slopes opening at Solang Valley, and a surreal quiet that summer tourists never get to see.",
            'cover_image': '/static/images/destinations/manali.jpg',
            'author_name': 'Vikram Bhatia', 'views': 1567, 'days_ago': 22,
            'tags': ['manali', 'snow', 'skiing', 'himalayas', 'winter'],
            'content': '<p>December through February is when Manali is truly magical — thick snow on the Old Manali rooftops and Solang Valley transformed into a ski resort. Crowds drop to a fraction of peak season.</p><h3>Solang Valley</h3><p>Skiing lessons start at ₹1,500/hour including equipment. Snowboarding, zorbing, and snow scooters are all available — perfect for first-timers.</p><h3>Where to Stay</h3><p>Stay in Old Manali — guesthouses drop to ₹400–800/night in winter and you\'ll have the village to yourself.</p>',
        },
        {
            'title': "Andaman Islands: A First-Timer's Complete Guide",
            'destination': 'Andaman', 'category': 'Beach',
            'summary': "Crystal-clear water, coral reefs, WWII history, and Asia's best snorkelling — the Andaman Islands are wildly underrated.",
            'cover_image': '/static/images/destinations/andaman.jpg',
            'author_name': 'SnapTravels Team', 'views': 2088, 'days_ago': 30,
            'tags': ['andaman', 'scuba', 'snorkelling', 'beach', 'islands'],
            'content': '<p>The Andaman archipelago sits in the Bay of Bengal and offers a quality of beaches and underwater visibility that rivals Thailand at a fraction of the cost.</p><h3>Havelock Island</h3><p>Radhanagar Beach is consistently rated one of Asia\'s best beaches. Elephant Beach is the snorkelling spot — corals, sea turtles, and reef fish in impossibly clear water.</p><h3>Scuba Diving</h3><p>Andaman is one of India\'s best scuba destinations. Visibility can reach 30m+. PADI Open Water courses cost ₹18,000–22,000.</p>',
        },
        {
            'title': 'Delhi Food Guide: 20 Dishes You Must Eat in Old Delhi',
            'destination': 'Delhi', 'category': 'Food & Culture',
            'summary': "Chandni Chowk is one of the world's great street food destinations — nihari at Karim's, jalebis at Old Famous, paranthe at Paranthe Wali Gali.",
            'cover_image': '/static/images/destinations/delhi.jpg',
            'author_name': 'Meera Kapoor', 'views': 4200, 'days_ago': 8,
            'tags': ['delhi', 'food', 'street food', 'old delhi', 'mughlai'],
            'content': '<p>Old Delhi was built in 1639 and its food culture has been perfecting itself ever since. This is the heart of Mughal cuisine in India.</p><h3>The Morning Circuit</h3><p>Start at Paranthe Wali Gali — families have been frying stuffed parathas in pure ghee here since 1875. Then walk to Old Famous Jalebi Wala on Dariba Corner.</p><h3>Karim\'s</h3><p>Founded in 1913 near Jama Masjid — order mutton nihari, seekh kebabs, and brain masala. Budget ₹400–600 per head.</p>',
        },
        {
            'title': 'Mumbai in 48 Hours: The Ultimate Weekend Guide',
            'destination': 'Mumbai', 'category': 'City Guide',
            'summary': "Two days, one city, zero boredom. From the Gateway of India at sunrise to late-night vada pav at Juhu — the perfect 48-hour Mumbai itinerary.",
            'cover_image': '/static/images/destinations/mumbai.jpg',
            'author_name': 'SnapTravels Team', 'views': 3850, 'days_ago': 15,
            'tags': ['mumbai', 'weekend', 'city guide', 'bollywood', 'marine drive'],
            'content': '<p>Mumbai never sleeps, never slows down, and never stops surprising. This 48-hour itinerary goes straight for what makes Mumbai worth the visit: the food, the sea, and the sheer energy of 20 million people living at full velocity.</p><h3>Day 1: South Mumbai</h3><p>Start at the Gateway of India at 7 AM. Ferry to Elephanta Island for the UNESCO cave temples. Walk north to Marine Drive for the iconic sunset view.</p><h3>Day 2: Dharavi & Juhu</h3><p>Book a Dharavi walking tour with Reality Tours (₹750). End at Juhu Beach for pav bhaji and bhel puri.</p>',
        },
        {
            'title': 'Himalayas Trekking for Beginners: Top 5 Easy Treks',
            'destination': 'Himalayas', 'category': 'Adventure',
            'summary': "You don't need to be an expert mountaineer to experience the Himalayas. These five beginner-friendly treks offer stunning views and unforgettable experiences.",
            'cover_image': '/static/images/packages/package-himalayas.jpg',
            'author_name': 'Rohan Mehta', 'views': 2750, 'days_ago': 25,
            'tags': ['himalayas', 'trekking', 'adventure', 'beginner', 'uttarakhand'],
            'content': '<p>The Himalayas are not just for seasoned mountaineers. These five routes are where most trekkers start.</p><h3>1. Triund Trek, Dharamsala (Easy)</h3><p>9 km one-way, max 2,875m. The most popular beginner trek in Himachal with impossible views from the meadow.</p><h3>2. Kedarkantha, Uttarakhand (Easy–Moderate)</h3><p>Best done December–April in snow. Summit views include Swargarohini and Bandarpunch peaks.</p><h3>3. Kheerganga, Parvati Valley (Easy)</h3><p>12–14 km. The reward: a natural hot spring at 3,000m. Walk through Kasol through pine forest and waterfalls.</p>',
        },
    ]

    added = 0
    for p in POSTS:
        slug = _slugify(p['title'])
        if BlogPost.query.filter_by(slug=slug).first():
            continue
        post = BlogPost(
            title        = p['title'],
            slug         = slug,
            destination  = p['destination'],
            category     = p['category'],
            summary      = p['summary'],
            content      = p['content'],
            cover_image  = p['cover_image'],
            author_name  = p['author_name'],
            views        = p['views'],
            published    = True,
            published_at = datetime.utcnow() - timedelta(days=p['days_ago']),
        )
        post.tags = p['tags']
        db.session.add(post)
        added += 1
    if added:
        db.session.commit()
        print(f'  Seeded {added} travel guide posts.')

def seed_database():
    """Seed database with initial data if empty"""

    try:
        # Create admin user if doesn't exist
        if not User.query.filter_by(email='admin@snaptravels.online').first():
            admin = User(
                email='admin@snaptravels.online',
                role='admin',
                email_confirmed=True
            )
            admin.set_password('Admin@123')
            db.session.add(admin)
            db.session.flush()  # Flush to check for conflicts

        # Create test user if doesn't exist
        if not User.query.filter_by(email='parthiban@snaptravels.online').first():
            user = User(
                email='parthiban@snaptravels.online',
                role='user',
                email_confirmed=True
            )
            user.set_password('Test@123')
            db.session.add(user)
            db.session.flush()  # Flush to check for conflicts

    except Exception as e:
        print(f"Warning: User seeding skipped (users may already exist): {str(e)}")
        db.session.rollback()

    # Seed flights if none exist
    if Flight.query.count() == 0:
        # 50 comprehensive flight data
        flights_data = [
            # Domestic Flights (India)
            ('FL001', 'SpiceJet', 'Chennai (MAA)', 'Mumbai (BOM)', '06:45', '09:15', 150, 5299.99, 145),
            ('FL002', 'Indigo', 'Delhi (DEL)', 'Bangalore (BLR)', '14:30', '17:45', 195, 6450.50, 132),
            ('FL003', 'Air India', 'Mumbai (BOM)', 'Goa (GOI)', '10:20', '11:35', 75, 3199.99, 128),
            ('FL004', 'Vistara', 'Bangalore (BLR)', 'Delhi (DEL)', '18:15', '21:30', 195, 7520.75, 118),
            ('FL005', 'GoAir', 'Chennai (MAA)', 'Kochi (COK)', '08:00', '09:15', 75, 2180.00, 155),
            ('FL006', 'SpiceJet', 'Delhi (DEL)', 'Mumbai (BOM)', '12:45', '15:00', 135, 4399.99, 125),
            ('FL007', 'Air India', 'Mumbai (BOM)', 'Kolkata (CCU)', '16:30', '19:15', 165, 5899.00, 98),
            ('FL008', 'Indigo', 'Delhi (DEL)', 'Chennai (MAA)', '07:20', '10:05', 165, 6200.75, 187),
            ('FL009', 'Vistara', 'Bangalore (BLR)', 'Mumbai (BOM)', '09:40', '11:25', 105, 4750.50, 143),
            ('FL010', 'GoAir', 'Kochi (COK)', 'Delhi (DEL)', '22:15', '01:30', 195, 7100.25, 89),
            ('FL011', 'SpiceJet', 'Hyderabad (HYD)', 'Chennai (MAA)', '13:20', '14:35', 75, 3450.00, 167),
            ('FL012', 'Air India', 'Pune (PNQ)', 'Delhi (DEL)', '05:45', '07:55', 130, 5670.80, 156),
            ('FL013', 'Indigo', 'Jaipur (JAI)', 'Mumbai (BOM)', '11:10', '13:00', 110, 4890.60, 134),
            ('FL014', 'Vistara', 'Goa (GOI)', 'Bangalore (BLR)', '19:25', '20:40', 75, 3780.40, 178),
            ('FL015', 'GoAir', 'Kolkata (CCU)', 'Hyderabad (HYD)', '06:50', '09:20', 150, 5340.90, 123),
            ('FL016', 'SpiceJet', 'Ahmedabad (AMD)', 'Delhi (DEL)', '15:30', '17:15', 105, 4560.70, 189),
            ('FL017', 'Air India', 'Lucknow (LKO)', 'Mumbai (BOM)', '12:40', '15:10', 150, 6120.30, 145),
            ('FL018', 'Indigo', 'Bhubaneswar (BBI)', 'Delhi (DEL)', '08:15', '10:45', 150, 5890.20, 167),
            ('FL019', 'Vistara', 'Coimbatore (CJB)', 'Chennai (MAA)', '17:20', '18:15', 55, 2450.00, 198),
            ('FL020', 'GoAir', 'Nagpur (NAG)', 'Mumbai (BOM)', '20:30', '22:00', 90, 3670.50, 156),
            ('FL021', 'SpiceJet', 'Srinagar (SXR)', 'Delhi (DEL)', '14:45', '16:15', 90, 4890.75, 134),
            ('FL022', 'Air India', 'Thiruvananthapuram (TRV)', 'Bangalore (BLR)', '21:10', '22:25', 75, 3980.60, 145),
            ('FL023', 'Indigo', 'Vadodara (BDQ)', 'Delhi (DEL)', '07:50', '09:30', 100, 4560.40, 123),
            ('FL024', 'Vistara', 'Raipur (RPR)', 'Mumbai (BOM)', '16:25', '18:15', 110, 5230.80, 167),
            ('FL025', 'GoAir', 'Indore (IDR)', 'Delhi (DEL)', '11:35', '13:10', 95, 4780.90, 189),
            
            # International Flights
            ('FL026', 'Emirates', 'Mumbai (BOM)', 'Dubai (DXB)', '02:30', '04:45', 135, 18999.99, 112),
            ('FL027', 'Qatar Airways', 'Delhi (DEL)', 'Doha (DOH)', '01:15', '04:30', 195, 22750.50, 98),
            ('FL028', 'Etihad', 'Bangalore (BLR)', 'Abu Dhabi (AUH)', '23:45', '02:15', 150, 19890.75, 87),
            ('FL029', 'Emirates', 'Chennai (MAA)', 'Dubai (DXB)', '03:20', '05:45', 145, 20450.25, 94),
            ('FL030', 'Air India', 'Delhi (DEL)', 'London (LHR)', '14:30', '19:45', 555, 45890.00, 76),
            ('FL031', 'Qatar Airways', 'Mumbai (BOM)', 'Doha (DOH)', '08:15', '11:30', 195, 24650.80, 89),
            ('FL032', 'Emirates', 'Kochi (COK)', 'Dubai (DXB)', '04:40', '07:10', 150, 21340.60, 103),
            ('FL033', 'Singapore Airlines', 'Bangalore (BLR)', 'Singapore (SIN)', '11:25', '18:45', 440, 28970.30, 78),
            ('FL034', 'Thai Airways', 'Delhi (DEL)', 'Bangkok (BKK)', '16:50', '23:15', 385, 26780.90, 85),
            ('FL035', 'Lufthansa', 'Mumbai (BOM)', 'Frankfurt (FRA)', '01:40', '07:20', 580, 52340.70, 67),
            ('FL036', 'British Airways', 'Delhi (DEL)', 'London (LHR)', '02:15', '07:45', 570, 48920.50, 72),
            ('FL037', 'KLM', 'Bangalore (BLR)', 'Amsterdam (AMS)', '21:30', '05:15', 590, 49870.40, 69),
            ('FL038', 'Air France', 'Mumbai (BOM)', 'Paris (CDG)', '23:45', '06:30', 615, 51230.80, 74),
            ('FL039', 'Turkish Airlines', 'Delhi (DEL)', 'Istanbul (IST)', '05:20', '10:45', 385, 31450.60, 89),
            ('FL040', 'Swiss Air', 'Chennai (MAA)', 'Zurich (ZUR)', '12:30', '18:45', 615, 53670.90, 65),
            
            # US Domestic Flights
            ('FL041', 'American Airlines', 'New York (JFK)', 'Los Angeles (LAX)', '08:30', '11:45', 375, 24650.75, 134),
            ('FL042', 'Delta', 'Chicago (ORD)', 'Miami (MIA)', '14:20', '18:30', 250, 18970.50, 156),
            ('FL043', 'United', 'San Francisco (SFO)', 'Seattle (SEA)', '06:45', '09:15', 150, 15680.40, 167),
            ('FL044', 'Southwest', 'Dallas (DFW)', 'Denver (DEN)', '11:30', '12:45', 75, 12340.60, 189),
            ('FL045', 'JetBlue', 'Boston (BOS)', 'Orlando (MCO)', '16:15', '19:45', 210, 19780.80, 145),
            ('FL046', 'Alaska Airlines', 'Portland (PDX)', 'San Diego (SAN)', '07:20', '09:50', 150, 16890.70, 178),
            ('FL047', 'Spirit', 'Las Vegas (LAS)', 'Phoenix (PHX)', '20:40', '21:30', 50, 8970.30, 198),
            ('FL048', 'Frontier', 'Atlanta (ATL)', 'Nashville (BNA)', '13:50', '14:45', 55, 9450.90, 187),
            ('FL049', 'Hawaiian Airlines', 'Honolulu (HNL)', 'Maui (OGG)', '09:15', '09:45', 30, 7890.50, 134),
            ('FL050', 'Virgin America', 'Washington (DCA)', 'San Francisco (SFO)', '22:30', '01:45', 375, 23670.20, 123)
        ]

        base_date = datetime.now().date()
        for i, (flight_no, airline, origin, dest, depart, arrive, duration, price, seats) in enumerate(flights_data):
            if not Flight.query.filter_by(flight_no=flight_no).first():
                # Generate random departure dates for the next 30 days
                random_days = random.randint(0, 30)
                depart_date = base_date + timedelta(days=random_days)

                flight = Flight(
                    flight_no=flight_no,
                    airline=airline,
                    origin=origin,
                    destination=dest,
                    depart_time=depart,
                    arrive_time=arrive,
                    depart_date=depart_date,
                    duration_mins=duration,
                    price=price,
                    seats_left=seats
                )
                db.session.add(flight)

    # Seed hotels if none exist
    if Hotel.query.count() == 0:
        # 50 comprehensive hotels data
        hotels_data = [
            # Ultra Luxury Hotels (Above 20000)
            ('Taj Lake Palace Udaipur', 'Udaipur', 4.9, 35000, ['WiFi', 'Lake View', 'Spa', 'Heritage', 'Royal Treatment', 'Butler Service'], '/assets/images/taj_udaipur.jpg'),
            ('The St. Regis Mumbai', 'Mumbai', 4.9, 28000, ['WiFi', 'Spa', 'Pool', 'Butler Service', 'Fine Dining', 'Business Center'], '/assets/images/stregis_mumbai.jpg'),
            ('Oberoi Rajvilas Jaipur', 'Jaipur', 4.8, 32000, ['WiFi', 'Spa', 'Pool', 'Heritage', 'Royal Villa', 'Elephant Polo'], '/assets/images/oberoi_jaipur.jpg'),
            ('Taj Mahal Palace Mumbai', 'Mumbai', 4.8, 25000, ['WiFi', 'Heritage', 'Spa', 'Pool', 'Fine Dining', 'Harbor View'], '/assets/images/taj_mumbai.jpg'),
            ('The Leela Palace Goa', 'Goa', 4.7, 22000, ['WiFi', 'Beach', 'Spa', 'Pool', 'Golf Course', 'Casino'], '/assets/images/leela_goa.jpg'),
            
            # Luxury Hotels (15000-20000)
            ('The Ritz Carlton Bangalore', 'Bangalore', 4.8, 18000, ['WiFi', 'Spa', 'Pool', 'Gym', 'Butler Service', 'Club Lounge'], '/assets/images/ritz_bangalore.jpg'),
            ('JW Marriott Mumbai', 'Mumbai', 4.7, 19500, ['WiFi', 'Spa', 'Pool', 'Business Center', 'Executive Lounge'], '/assets/images/jw_mumbai.jpg'),
            ('The Leela Palace Delhi', 'Delhi', 4.8, 19500, ['WiFi', 'Spa', 'Pool', 'Heritage', 'Restaurant', 'Concierge'], '/assets/images/leela_delhi.jpg'),
            ('Grand Hyatt Mumbai', 'Mumbai', 4.6, 17500, ['WiFi', 'Spa', 'Pool', 'Multiple Restaurants', 'Grand Ballroom'], '/assets/images/grand_hyatt_mumbai.jpg'),
            ('The Oberoi Bengaluru', 'Bangalore', 4.7, 16800, ['WiFi', 'Spa', 'Pool', 'Fine Dining', 'Business Center'], '/assets/images/oberoi_bangalore.jpg'),
            
            # Premium Hotels (10000-15000)
            ('ITC Grand Central Mumbai', 'Mumbai', 4.6, 13800, ['WiFi', 'Spa', 'Business Center', 'Restaurant', 'Banquet'], '/assets/images/itc_mumbai.jpg'),
            ('Taj Falaknuma Palace Hyderabad', 'Hyderabad', 4.9, 15000, ['WiFi', 'Spa', 'Pool', 'Restaurant', 'Heritage', 'Palace Suites'], '/assets/images/taj_hyderabad.jpg'),
            ('The Leela Palace Chennai', 'Chennai', 4.6, 14500, ['WiFi', 'Pool', 'Gym', 'Spa', 'Business Center'], '/assets/images/leela_chennai.jpg'),
            ('Hyatt Regency Chennai', 'Chennai', 4.5, 12900, ['WiFi', 'Pool', 'Spa', 'Business Center', 'Convention Center'], '/assets/images/hyatt_chennai.jpg'),
            ('Marriott Executive Apartments Bengaluru', 'Bangalore', 4.4, 11200, ['WiFi', 'Pool', 'Gym', 'Kitchenette', 'Long Stay'], '/assets/images/marriott_bangalore.jpg'),
            ('Grand Hyatt Goa', 'Goa', 4.4, 11200, ['WiFi', 'Beach', 'Pool', 'Spa', 'Restaurant', 'Water Sports'], '/assets/images/hyatt_goa.jpg'),
            ('ITC Sonar Kolkata', 'Kolkata', 4.5, 12600, ['WiFi', 'Spa', 'Pool', 'Business Center', 'Kaya Kalp Spa'], '/assets/images/itc_kolkata.jpg'),
            ('The Westin Hyderabad', 'Hyderabad', 4.3, 10800, ['WiFi', 'Pool', 'Spa', 'WestinWORKOUT', 'Heavenly Bed'], '/assets/images/westin_hyderabad.jpg'),
            ('Conrad Pune', 'Pune', 4.4, 11500, ['WiFi', 'Pool', 'Spa', 'Business Center', 'Executive Lounge'], '/assets/images/conrad_pune.jpg'),
            ('Shangri-La Eros New Delhi', 'Delhi', 4.6, 13200, ['WiFi', 'Spa', 'Pool', 'Multiple Restaurants', 'Health Club'], '/assets/images/shangri_la_delhi.jpg'),
            
            # Upper Mid-Range Hotels (7000-10000)
            ('ITC Maurya Delhi', 'Delhi', 4.7, 9800, ['WiFi', 'Spa', 'Business Center', 'Restaurant', 'Bukhara Restaurant'], '/assets/images/itc_delhi.jpg'),
            ('Conrad Bangalore', 'Bangalore', 4.5, 9600, ['WiFi', 'Pool', 'Gym', 'Business Center', 'Executive Lounge'], '/assets/images/conrad_bangalore.jpg'),
            ('Hyatt Regency Delhi', 'Delhi', 4.4, 8500, ['WiFi', 'Pool', 'Spa', 'Business Center', 'La Piazza'], '/assets/images/hyatt_delhi.jpg'),
            ('Sheraton Grand Chennai', 'Chennai', 4.5, 8200, ['WiFi', 'Pool', 'Gym', 'Business Center', 'Dakshin Restaurant'], '/assets/images/sheraton_chennai.jpg'),
            ('Radisson Blu Goa', 'Goa', 4.3, 7800, ['WiFi', 'Beach', 'Pool', 'Restaurant', 'Calamari Restaurant'], '/assets/images/radisson_goa.jpg'),
            ('The Westin Pune', 'Pune', 4.4, 7200, ['WiFi', 'Pool', 'Gym', 'Spa', 'Seasonal Tastes'], '/assets/images/westin_pune.jpg'),
            ('DoubleTree by Hilton Goa', 'Goa', 4.2, 7200, ['WiFi', 'Beach', 'Pool', 'Spa', 'Panjim Inn'], '/assets/images/doubletree_goa.jpg'),
            ('Novotel Hyderabad', 'Hyderabad', 4.3, 6800, ['WiFi', 'Pool', 'Spa', 'Restaurant', 'The Square'], '/assets/images/novotel_hyderabad.jpg'),
            ('Marriott Jaipur', 'Jaipur', 4.3, 6800, ['WiFi', 'Pool', 'Spa', 'Restaurant', 'Sagar Ratna'], '/assets/images/marriott_jaipur.jpg'),
            ('The Park Kolkata', 'Kolkata', 4.3, 7500, ['WiFi', 'Restaurant', 'Bar', 'Gym', 'Someplace Else'], '/assets/images/park_kolkata.jpg'),
            
            # Mid-Range Hotels (5000-7000)
            ('Crowne Plaza Kochi', 'Kochi', 4.2, 6200, ['WiFi', 'Pool', 'Restaurant', 'Business Center', 'Mattancherry'], '/assets/images/crowne_kochi.jpg'),
            ('Vivanta by Taj Kochi', 'Kochi', 4.2, 5800, ['WiFi', 'Pool', 'Restaurant', 'Spa', 'Latitude'], '/assets/images/vivanta_kochi.jpg'),
            ('Four Points by Sheraton Pune', 'Pune', 4.1, 5800, ['WiFi', 'Pool', 'Gym', 'Business Center', 'Eatery'], '/assets/images/fourpoints_pune.jpg'),
            ('Holiday Inn Mumbai', 'Mumbai', 4.1, 5500, ['WiFi', 'Pool', 'Gym', 'Restaurant', 'Emerald Restaurant'], '/assets/images/holiday_mumbai.jpg'),
            ('Aloft Bangalore', 'Bangalore', 4.0, 5200, ['WiFi', 'Pool', 'Gym', 'Modern Design', 'W XYZ Bar'], '/assets/images/aloft_bangalore.jpg'),
            ('Radisson Blu Plaza Delhi', 'Delhi', 4.2, 6400, ['WiFi', 'Pool', 'Spa', 'Business Center', 'TK\'s Oriental Grill'], '/assets/images/radisson_delhi.jpg'),
            ('Courtyard by Marriott Mumbai', 'Mumbai', 4.0, 5900, ['WiFi', 'Pool', 'Gym', 'Business Center', 'Paprika'], '/assets/images/courtyard_mumbai.jpg'),
            ('Novotel Chennai', 'Chennai', 4.1, 5600, ['WiFi', 'Pool', 'Spa', 'Restaurant', 'Food Exchange'], '/assets/images/novotel_chennai.jpg'),
            ('Hilton Garden Inn Gurgaon', 'Gurgaon', 4.0, 5400, ['WiFi', 'Pool', 'Gym', 'Business Center', 'Garden Grille'], '/assets/images/hilton_gurgaon.jpg'),
            ('The Lalit New Delhi', 'Delhi', 4.3, 6800, ['WiFi', 'Spa', 'Pool', 'Business Center', 'Baluchi'], '/assets/images/lalit_delhi.jpg'),
            
            # Value Hotels (3000-5000)
            ('Lemon Tree Delhi', 'Delhi', 4.0, 4500, ['WiFi', 'Restaurant', 'Gym', 'Business Center'], '/assets/images/lemontree_delhi.jpg'),
            ('Sterling Resorts Goa', 'Goa', 4.1, 4800, ['WiFi', 'Beach Access', 'Pool', 'Restaurant', 'Water Sports'], '/assets/images/sterling_goa.jpg'),
            ('The Gateway Hotel Gangtok', 'Gangtok', 4.2, 4600, ['WiFi', 'Mountain View', 'Restaurant', 'Spa', 'Trekking'], '/assets/images/gateway_gangtok.jpg'),
            ('Hotel Clarks Agra', 'Agra', 4.0, 4500, ['WiFi', 'Pool', 'Restaurant', 'Near Taj Mahal', 'Travel Desk'], '/assets/images/clarks_agra.jpg'),
            ('Hotel Highlands Shimla', 'Shimla', 4.0, 4200, ['WiFi', 'Hill Station View', 'Restaurant', 'Fireplace', 'Mountain Activities'], '/assets/images/highlands_shimla.jpg'),
            ('Red Fox Hotel Jaipur', 'Jaipur', 3.9, 4200, ['WiFi', 'Pool', 'Restaurant', 'City Tours'], '/assets/images/redfox_jaipur.jpg'),
            ('Country Inn Kochi', 'Kochi', 3.9, 4100, ['WiFi', 'Pool', 'Restaurant', 'Parking', 'Backwater Tours'], '/assets/images/country_kochi.jpg'),
            ('Ibis Chennai', 'Chennai', 4.0, 4000, ['WiFi', 'Restaurant', 'Modern Rooms', 'Business Corner'], '/assets/images/ibis_chennai.jpg'),
            ('Ginger Mumbai', 'Mumbai', 3.8, 3800, ['WiFi', 'Restaurant', 'Business Center', 'Lean Luxury'], '/assets/images/ginger_mumbai.jpg'),
            ('Treebo Hotels Hyderabad', 'Hyderabad', 3.9, 3600, ['WiFi', 'Restaurant', 'Complimentary Breakfast', 'Travel Assistance'], '/assets/images/treebo_hyderabad.jpg'),
            ('Keys Hotel Bangalore', 'Bangalore', 3.8, 3500, ['WiFi', 'Restaurant', 'Business Center', 'Corporate Rates'], '/assets/images/keys_bangalore.jpg'),
            ('Zone Connect Pune', 'Pune', 3.8, 3400, ['WiFi', 'Restaurant', 'Modern Amenities', 'Co-working Space'], '/assets/images/zone_pune.jpg'),
            ('FabHotel Kolkata', 'Kolkata', 3.7, 3200, ['WiFi', 'Restaurant', 'AC', 'City Center Location'], '/assets/images/fab_kolkata.jpg')
        ]

        for hotel_data in hotels_data:
            hotel = Hotel(
                name=hotel_data[0],
                city=hotel_data[1],
                rating=hotel_data[2],
                price_per_night=hotel_data[3],
                image_path=hotel_data[5],
                description=f'Luxury hotel in {hotel_data[1]} with world-class amenities and exceptional service.'
            )
            hotel.amenities = hotel_data[4]
            db.session.add(hotel)

    try:
        db.session.commit()
        print("✅ Database seeded successfully")
    except Exception as e:
        db.session.rollback()
        print(f"⚠️  Database seeding completed with warnings: {str(e)}")