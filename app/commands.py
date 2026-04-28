"""
Flask CLI commands for SnapTravels.

Usage (from project root):
    flask seed-packages   # adds holiday packages + promo codes
    flask seed-reviews    # adds dummy reviews to hotels
    flask seed-all        # runs everything above
"""
import click
from flask import Blueprint
from app import db

seed_bp = Blueprint('seed', __name__, cli_group=None)


@seed_bp.cli.command('seed-packages')
def seed_packages():
    """Seed holiday packages and promo codes."""
    from app.models import Package, PromoCode
    click.echo('Seeding packages…')

    packages = [
        dict(
            name='Goa Beach Getaway',
            slug='goa-beach-getaway',
            image_path='/static/images/packages/package-goa.jpg',
            destination='Goa', country='India', tag='BESTSELLER',
            description='Sun, sand and sea — the ultimate Goa escape with beach resort, meals, and airport transfers.',
            duration_nights=4, base_price=18999, original_price=24999,
            includes_flight=True, includes_hotel=True, includes_meals=True, includes_transfers=True,
            highlights=[
                '4-star beachfront resort',
                'Daily breakfast & dinner included',
                'Complimentary airport transfers',
                'Water sports voucher',
                'Evening sunset cruise',
            ],
            itinerary=[
                {'title': 'Arrival & Beach', 'description': 'Arrive at Goa Airport, check in to your beachfront resort, relax by the pool.'},
                {'title': 'North Goa Sightseeing', 'description': 'Visit Calangute Beach, Fort Aguada, and Anjuna Flea Market.'},
                {'title': 'South Goa Day', 'description': 'Explore Palolem Beach, Dudhsagar waterfalls, and local spice plantations.'},
                {'title': 'Water Sports & Departure', 'description': 'Enjoy water sports in the morning, then transfer to airport.'},
            ],
        ),
        dict(
            name='Manali Snowscape',
            slug='manali-snowscape',
            image_path='/static/images/packages/package-himalayas.jpg',
            destination='Manali', country='India', tag='NEW',
            description='Breathtaking Himalayan views, snow adventures, and cozy mountain stays.',
            duration_nights=5, base_price=22500, original_price=28000,
            includes_flight=True, includes_hotel=True, includes_meals=False, includes_transfers=True,
            highlights=[
                'Stay at a luxury mountain lodge',
                'Snow adventure activities: skiing, snow tubing',
                'Rohtang Pass & Solang Valley tour',
                'Hadimba Temple and Old Manali walk',
                'Evening bonfire',
            ],
            itinerary=[
                {'title': 'Fly to Kullu, Drive to Manali', 'description': 'Arrive at Bhuntar Airport, scenic 45-min drive to Manali.'},
                {'title': 'Solang Valley Snow Fun', 'description': 'Full day at Solang Valley — skiing, sledging, snowmobile rides.'},
                {'title': 'Rohtang Pass', 'description': 'Subject to permit availability. Snow-covered pass at 3,978m. Stunning views.'},
                {'title': 'Old Manali & Mall Road', 'description': 'Explore old Manali village, Hadimba Temple, cafes, and local shopping.'},
                {'title': 'Departure', 'description': 'Morning leisure, transfer to airport for return flight.'},
            ],
        ),
        dict(
            name='Kerala Backwaters Bliss',
            slug='kerala-backwaters',
            image_path='/static/images/packages/package-kerala.jpg',
            destination='Kerala', country='India', tag='DEAL',
            description='Houseboat cruise through serene backwaters, Ayurvedic spa, and lush green landscapes.',
            duration_nights=6, base_price=26000, original_price=32000,
            includes_flight=True, includes_hotel=True, includes_meals=True, includes_transfers=True,
            highlights=[
                '2-night houseboat stay on Alleppey backwaters',
                'Ayurvedic massage session',
                'Munnar tea plantation tour',
                'All meals included',
                'Kathakali cultural show',
            ],
            itinerary=[
                {'title': 'Arrive Kochi', 'description': 'Land at Kochi, check into hotel. Evening at Marine Drive.'},
                {'title': 'Munnar', 'description': 'Drive to Munnar, tea estate tour, Eravikulam National Park.'},
                {'title': 'Thekkady', 'description': 'Periyar Wildlife Sanctuary boat ride, spice garden visit.'},
                {'title': 'Alleppey Houseboat Day 1', 'description': 'Board your private houseboat, cruise through canals.'},
                {'title': 'Alleppey Houseboat Day 2', 'description': 'Village walks, sunrise over backwaters, Ayurvedic massage.'},
                {'title': 'Kochi & Departure', 'description': 'Fort Kochi, Jewish Synagogue, Chinese fishing nets. Transfer to airport.'},
            ],
        ),
        dict(
            name='Rajasthan Royal Journey',
            slug='rajasthan-royal',
            image_path='/static/images/packages/package-rajasthan.jpg',
            destination='Rajasthan', country='India', tag='BESTSELLER',
            description='Palace hotels, desert safaris, and the golden colours of India\'s royal state.',
            duration_nights=7, base_price=35000, original_price=45000,
            includes_flight=True, includes_hotel=True, includes_meals=False, includes_transfers=True,
            highlights=[
                'Stay in heritage palace hotels',
                'Camel safari in Jaisalmer',
                'City Palace and Amber Fort tours',
                'Pushkar Lake sunrise',
                'Local bazaar shopping experience',
            ],
            itinerary=[
                {'title': 'Arrive Jaipur', 'description': 'Check into heritage hotel. Evening at Hawa Mahal.'},
                {'title': 'Amber Fort & City Palace', 'description': 'Elephant ride to Amber Fort, City Palace, Jantar Mantar.'},
                {'title': 'Pushkar', 'description': 'Drive to Pushkar, Brahma temple, camel fair grounds.'},
                {'title': 'Jodhpur', 'description': 'Mehrangarh Fort, blue city walk, Umaid Bhawan Palace.'},
                {'title': 'Jaisalmer', 'description': 'Golden Fort, Sam Sand Dunes, camel safari, cultural show.'},
                {'title': 'Bikaner', 'description': 'Junagarh Fort, camel research station.'},
                {'title': 'Return to Jaipur & Departure', 'description': 'Scenic drive, airport transfer.'},
            ],
        ),
        dict(
            name='Maldives Luxury Escape',
            slug='maldives-luxury',
            image_path='/static/images/packages/package-international.jpg',
            destination='Maldives', country='Maldives', tag='DEAL',
            description='Overwater villas, crystal-clear lagoons, and world-class snorkelling.',
            duration_nights=5, base_price=89000, original_price=110000,
            includes_flight=True, includes_hotel=True, includes_meals=True, includes_transfers=True,
            highlights=[
                'Overwater villa with direct lagoon access',
                'All-inclusive meals & non-alcoholic drinks',
                'Speedboat airport transfer',
                'Complimentary snorkelling gear',
                'Sunset dhoni cruise',
            ],
            itinerary=[
                {'title': 'Arrival & Check-in', 'description': 'Fly to Velana International, speedboat to resort. Dive into turquoise water.'},
                {'title': 'Beach & Snorkelling', 'description': 'House reef snorkel, beach volleyball, spa.'},
                {'title': 'Day Trip to Sandbank', 'description': 'Private sandbank picnic, dolphin cruise in the afternoon.'},
                {'title': 'Water Sports', 'description': 'Jet ski, paddleboard, kayak. Sunset dhoni cruise.'},
                {'title': 'Departure', 'description': 'Final dip, then speedboat to airport.'},
            ],
        ),
        dict(
            name='Bali Discovery',
            slug='bali-discovery',
            image_path='/static/images/packages/package-international.jpg',
            destination='Bali', country='Indonesia', tag='NEW',
            description='Rice terraces, ancient temples, surf beaches, and the ultimate island vibe.',
            duration_nights=6, base_price=55000, original_price=68000,
            includes_flight=True, includes_hotel=True, includes_meals=False, includes_transfers=True,
            highlights=[
                'Ubud rice terrace walks',
                'Uluwatu Kecak fire dance at sunset',
                'Tanah Lot temple tour',
                'Seminyak beachfront stay',
                'Balinese cooking class',
            ],
            itinerary=[
                {'title': 'Arrive Bali (Kuta)', 'description': 'Land at Ngurah Rai Airport, transfer to Seminyak beach resort.'},
                {'title': 'Ubud', 'description': 'Tegallalang rice terraces, Monkey Forest, local art galleries.'},
                {'title': 'Tanah Lot & Bedugul', 'description': 'Sea temple, Ulun Danu Beratan, Handara Gate.'},
                {'title': 'Uluwatu & Sunset', 'description': 'Uluwatu cliffs, Kecak fire dance, seafood dinner at Jimbaran.'},
                {'title': 'Seminyak Beach Day', 'description': 'Surfing lesson, spa treatment, sunset at Ku De Ta.'},
                {'title': 'Departure', 'description': 'Airport transfer, fly home.'},
            ],
        ),
    ]

    added = 0
    for p in packages:
        if Package.query.filter_by(slug=p['slug']).first():
            continue
        pkg = Package(
            name=p['name'], slug=p['slug'], destination=p['destination'],
            country=p['country'], tag=p.get('tag'), description=p.get('description'),
            duration_nights=p['duration_nights'], base_price=p['base_price'],
            original_price=p.get('original_price'),
            image_path=p.get('image_path'),
            includes_flight=p.get('includes_flight', True),
            includes_hotel=p.get('includes_hotel', True),
            includes_meals=p.get('includes_meals', False),
            includes_transfers=p.get('includes_transfers', True),
            max_persons=8, active=True,
        )
        pkg.highlights = p.get('highlights', [])
        pkg.itinerary = p.get('itinerary', [])
        db.session.add(pkg)
        added += 1

    click.echo(f'  Added {added} packages')

    # Promo codes
    promos = [
        dict(code='SNAP20', description='20% off on any booking', discount_type='PERCENT',
             discount_value=20, max_discount=5000, min_amount=5000, max_uses=None),
        dict(code='FLAT500', description='Flat ₹500 off on orders above ₹3,000', discount_type='FLAT',
             discount_value=500, min_amount=3000, max_uses=500),
        dict(code='HOLIDAY10', description='10% off on holiday packages', discount_type='PERCENT',
             discount_value=10, max_discount=3000, min_amount=10000, max_uses=None),
        dict(code='NEWUSER', description='Flat ₹1,000 off for first-time bookers', discount_type='FLAT',
             discount_value=1000, min_amount=2000, max_uses=1),
        dict(code='FLYDEAL', description='15% off flights above ₹4,000', discount_type='PERCENT',
             discount_value=15, max_discount=2000, min_amount=4000, max_uses=None),
    ]
    added_p = 0
    for pr in promos:
        if PromoCode.query.filter_by(code=pr['code']).first():
            continue
        pc = PromoCode(**pr)
        db.session.add(pc)
        added_p += 1
    click.echo(f'  Added {added_p} promo codes')

    db.session.commit()
    click.echo('Done ✓')


@seed_bp.cli.command('seed-reviews')
def seed_reviews():
    """Add sample reviews to hotels."""
    from app.models import Hotel, Review, User

    admin = User.query.filter_by(role='admin').first()
    if not admin:
        click.echo('No admin user found. Run seed-admin first.')
        return

    sample_reviews = [
        ('Excellent stay, very clean and comfortable!', 5, 'Great experience'),
        ('Good hotel, breakfast could be better.', 4, 'Nice stay'),
        ('Average. Room was smaller than expected.', 3, 'It was okay'),
        ('Beautiful location, amazing staff!', 5, 'Highly recommended'),
        ('Great value for money.', 4, 'Would return'),
    ]
    import random
    count = 0
    for hotel in Hotel.query.limit(10).all():
        existing = Review.query.filter_by(review_type='HOTEL', ref_id=hotel.id).count()
        if existing > 0:
            continue
        comment, rating, title = random.choice(sample_reviews)
        rev = Review(user_id=admin.id, review_type='HOTEL', ref_id=hotel.id,
                     rating=rating, title=title, comment=comment, verified_booking=False)
        db.session.add(rev)
        count += 1

    db.session.commit()
    click.echo(f'Added {count} reviews ✓')


@seed_bp.cli.command('seed-transport')
def seed_transport():
    """Seed Trains, Buses, Cabs, Activities, and InsurancePlans."""
    from app.models import Train, Bus, Cab, Activity, InsurancePlan

    # ── Trains ────────────────────────────────────────────────────────
    trains = [
        # (train_no, name, type, run_days, origin, dest, dep, arr, dist, dur, sl_f, tac_f, sac_f, fac_f, sl_s, tac_s, sac_s, fac_s)
        ('12001', 'Shatabdi Express',           'Superfast', 'Daily',      'New Delhi',          'Bhopal',             '06:00', '13:55', 475,  700,  450,  1100, 1500, 2800, 120, 56, 40, 20),
        ('12951', 'Mumbai Rajdhani',            'Rajdhani',  'Daily',      'Mumbai Central',     'New Delhi',          '16:55', '08:35', 1388, 940,  580,  1500, 2100, 3900, 200, 64, 46, 18),
        ('12009', 'Mumbai Shatabdi',            'Superfast', 'Daily',      'Mumbai Central',     'Ahmedabad',          '06:25', '12:55', 491,  390,  420,  1050, 1450, 2700, 150, 64, 46, 18),
        ('22691', 'Rajdhani Express',           'Rajdhani',  'Daily',      'Bengaluru City',     'Hazrat Nizamuddin',  '20:00', '06:05', 2444, 1815, 610,  1600, 2200, 4100, 200, 64, 46, 18),
        ('12041', 'NZM-BSB Garib Rath',         'Express',   'Mon Wed Fri','New Delhi',          'Mumbai Central',     '06:00', '22:00', 1386, 960,  490,  1200, 1650, 3100, 120, 56, 40, 16),
        ('12345', 'Saraighat Express',          'Express',   'Daily',      'Howrah',             'Guwahati',           '15:50', '05:45', 1002, 840,  380,  980,  1380, 2600, 200, 64, 46, 18),
        ('16526', 'Island Express',             'Express',   'Daily',      'Bangalore City',     'Kanniyakumari',      '21:10', '21:30', 724,  1440, 350,  900,  1250, 2400, 200, 64, 46, 18),
        ('12655', 'Navjeevan Express',          'Express',   'Daily',      'Ahmedabad',          'Chennai Central',    '18:10', '06:30', 1940, 1440, 420,  1080, 1490, 2800, 200, 56, 40, 16),
        ('12649', 'Karnataka Sampark Kranti',   'Superfast', 'Daily',      'Hazrat Nizamuddin',  'Yeshvantpur',        '21:40', '04:45', 2205, 1915, 520,  1350, 1850, 3500, 200, 64, 46, 18),
        ('12027', 'Chennai Shatabdi',           'Superfast', 'Daily',      'Chennai Central',    'Bangalore City',     '06:00', '11:00', 360,  300,  370,  950,  1300, 2450, 120, 56, 40, 16),
    ]
    added_t = 0
    for (train_no, name, ttype, run_days, origin, dest, dep, arr, dist, dur,
         sl_f, tac_f, sac_f, fac_f, sl_s, tac_s, sac_s, fac_s) in trains:
        if not Train.query.filter_by(train_no=train_no).first():
            db.session.add(Train(
                train_no=train_no, train_name=name, train_type=ttype, run_days=run_days,
                origin=origin, destination=dest,
                depart_time=dep, arrive_time=arr, distance_km=dist, duration_mins=dur,
                sleeper_fare=sl_f, third_ac_fare=tac_f, second_ac_fare=sac_f, first_ac_fare=fac_f,
                sleeper_seats=sl_s, third_ac_seats=tac_s, second_ac_seats=sac_s, first_ac_seats=fac_s,
            ))
            added_t += 1
    click.echo(f'  Trains added: {added_t}')

    # ── Buses ─────────────────────────────────────────────────────────
    buses = [
        ('BUS001', 'RedBus Travels', 'Mumbai', 'Goa', '21:00', '06:00', 540, 'Volvo AC Sleeper', 950, 34),
        ('BUS002', 'SRS Travels', 'Bangalore', 'Goa', '20:30', '10:30', 840, 'Multi-Axle AC Sleeper', 1100, 36),
        ('BUS003', 'Orange Tours', 'Delhi', 'Jaipur', '06:00', '12:00', 360, 'AC Seater', 450, 40),
        ('BUS004', 'Parveen Travels', 'Chennai', 'Pondicherry', '07:00', '10:00', 180, 'AC Seater', 280, 44),
        ('BUS005', 'Kallada Travels', 'Bangalore', 'Hyderabad', '22:00', '06:00', 480, 'Volvo Multi-Axle', 850, 40),
        ('BUS006', 'KSRTC', 'Bangalore', 'Mysore', '06:00', '10:30', 270, 'AC Seater', 320, 44),
        ('BUS007', 'IntrCity SmartBus', 'Mumbai', 'Pune', '07:00', '11:00', 240, 'Volvo AC Seater', 380, 40),
        ('BUS008', 'Neeta Tours', 'Ahmedabad', 'Mumbai', '20:00', '08:00', 720, 'Volvo AC Sleeper', 900, 36),
        ('BUS009', 'Chartered Speed', 'Hyderabad', 'Bangalore', '21:00', '05:00', 480, 'Volvo Sleeper', 850, 36),
        ('BUS010', 'VRL Travels', 'Mumbai', 'Bangalore', '18:00', '09:00', 900, 'Multi-Axle Sleeper', 1200, 40),
    ]
    added_b = 0
    for (bus_no, operator, origin, dest, dep, arr, dur, btype, price, seats) in buses:
        if not Bus.query.filter_by(bus_no=bus_no).first():
            db.session.add(Bus(
                bus_no=bus_no, operator=operator, origin=origin, destination=dest,
                depart_time=dep, arrive_time=arr, duration_mins=dur,
                bus_type=btype, price=price, seats_left=seats,
            ))
            added_b += 1
    click.echo(f'  Buses added: {added_b}')

    # ── Cabs ──────────────────────────────────────────────────────────
    cabs = [
        ('Hatchback', 'Maruti Suzuki WagonR', 8.0, 5.0, 80.0, 4),
        ('Sedan', 'Honda City', 12.0, 5.0, 120.0, 4),
        ('Sedan', 'Toyota Etios', 11.0, 5.0, 110.0, 4),
        ('SUV', 'Toyota Innova', 16.0, 5.0, 180.0, 7),
        ('SUV', 'Maruti Ertiga', 14.0, 5.0, 160.0, 6),
        ('Premium Sedan', 'Mercedes E-Class', 35.0, 5.0, 500.0, 4),
        ('Premium SUV', 'Toyota Fortuner', 28.0, 5.0, 400.0, 7),
        ('Mini', 'Maruti Alto', 7.0, 5.0, 70.0, 4),
        ('Sedan', 'Hyundai Xcent', 11.0, 5.0, 110.0, 4),
        ('SUV', 'Mahindra Bolero', 13.0, 5.0, 150.0, 8),
    ]
    added_c = 0
    for (vtype, brand, base_fare, base_km, base_amt, capacity) in cabs:
        if not Cab.query.filter_by(brand=brand, vehicle_type=vtype).first():
            db.session.add(Cab(
                vehicle_type=vtype, brand=brand,
                base_fare=base_fare, base_km=base_km,
                base_amount=base_amt, capacity=capacity,
                ac=True, available=True,
            ))
            added_c += 1
    click.echo(f'  Cabs added: {added_c}')

    # ── Activities ────────────────────────────────────────────────────
    # (name, city, category, description, price, duration_hrs, min_persons, max_persons, rating, image_path)
    activities = [
        ('Scuba Diving in Goa', 'Goa', 'Water Sports', 'Explore the vibrant underwater world of the Arabian Sea with certified instructors.', 2999, 3.0, 1, 12, 4.7, '/static/images/activities/beach.jpg'),
        ('Old Goa Heritage Walk', 'Goa', 'Cultural', 'A guided walk through the UNESCO-listed churches and Portuguese-era architecture.', 799, 3.0, 2, 20, 4.5, '/static/images/activities/heritage.jpg'),
        ('Jaipur Elephant Ride', 'Jaipur', 'Sightseeing', 'Experience a majestic elephant ride up to Amber Fort with a royal welcome.', 1499, 2.0, 1, 8, 4.6, '/static/images/activities/heritage.jpg'),
        ('Jaipur City Tuk-Tuk Tour', 'Jaipur', 'Sightseeing', 'Hop on a fun tuk-tuk and zip through palaces, markets and monuments.', 999, 4.0, 2, 6, 4.4, '/static/images/activities/activity-1.jpg'),
        ('Kerala Backwater Kayaking', 'Kochi', 'Adventure', 'Paddle through serene backwaters surrounded by coconut groves and village life.', 1299, 3.0, 1, 10, 4.8, '/static/images/activities/activity-2.jpg'),
        ('Kochi Sunset Dinner Cruise', 'Kochi', 'Food', 'Enjoy Kerala cuisine on a traditional houseboat as the sun sets over the harbour.', 2499, 3.0, 2, 30, 4.7, '/static/images/activities/beach.jpg'),
        ('Manali Snowmobile Safari', 'Manali', 'Adventure', 'Race across Solang Valley snow fields on a thrilling snowmobile ride.', 1999, 2.0, 1, 15, 4.6, '/static/images/activities/trekking.jpg'),
        ('Manali River Rafting', 'Manali', 'Adventure', 'Conquer the rapids of the Beas River in a guided white-water rafting session.', 1499, 3.0, 2, 20, 4.7, '/static/images/activities/trekking.jpg'),
        ('Udaipur Lake Pichola Boat Ride', 'Udaipur', 'Sightseeing', 'Glide across the shimmering Lake Pichola with panoramic views of the City Palace.', 899, 1.5, 1, 20, 4.8, '/static/images/activities/activity-2.jpg'),
        ('Mumbai Dharavi Slum Tour', 'Mumbai', 'Cultural', 'An eye-opening guided tour of Asia\'s largest slum and its thriving micro-industries.', 1299, 3.0, 2, 15, 4.5, '/static/images/activities/heritage.jpg'),
        ('Mumbai Street Food Walk', 'Mumbai', 'Food', 'Taste your way through Vada Pav, Bhel Puri, Pani Puri and more with a local guide.', 999, 3.0, 2, 12, 4.6, '/static/images/activities/activity-1.jpg'),
        ('Delhi Old City Walk', 'Delhi', 'Cultural', 'Explore Chandni Chowk\'s narrow lanes, Jama Masjid and Paranthe Wali Gali.', 799, 4.0, 2, 15, 4.5, '/static/images/activities/heritage.jpg'),
        ('Agra Taj Mahal Sunrise Tour', 'Agra', 'Sightseeing', 'Visit the Taj Mahal at golden hour with a skip-the-line guided tour.', 1999, 4.0, 2, 15, 4.9, '/static/images/activities/heritage.jpg'),
        ('Shimla Nature Trek', 'Shimla', 'Adventure', 'Trek through pine forests with panoramic Himalayan views and a picnic lunch.', 1299, 6.0, 2, 12, 4.6, '/static/images/activities/trekking.jpg'),
        ('Bangalore Brewery Tour', 'Bangalore', 'Food', 'Sample craft beers and learn the brewing process at Bangalore\'s top microbreweries.', 1499, 3.0, 2, 15, 4.4, '/static/images/activities/activity-1.jpg'),
    ]
    added_a = 0
    for (name, city, cat, desc, price, dur, min_p, max_p, rating, img) in activities:
        if not Activity.query.filter_by(name=name, city=city).first():
            db.session.add(Activity(
                name=name, city=city, category=cat, description=desc,
                price_per_person=price, duration_hours=dur,
                min_persons=min_p, max_persons=max_p, rating=rating,
                image_path=img, review_count=0, active=True,
            ))
            added_a += 1
    click.echo(f'  Activities added: {added_a}')

    # ── Insurance Plans ───────────────────────────────────────────────
    plans = [
        ('Basic', 'Essential cover for budget travellers. Includes emergency medical assistance.',
         45.0, 300000, False, False, False, False),
        ('Standard', 'Our most popular plan. Covers medical, trip cancellation and baggage loss.',
         90.0, 750000, True, True, True, False),
        ('Premium', 'Comprehensive cover including adventure sports. Ideal for frequent travellers.',
         150.0, 2000000, True, True, True, True),
    ]
    added_i = 0
    for (name, desc, ppd, medical, cancellation, baggage, delay, adventure) in plans:
        if not InsurancePlan.query.filter_by(name=name).first():
            db.session.add(InsurancePlan(
                name=name, description=desc,
                price_per_person_per_day=ppd, medical_cover=medical,
                trip_cancellation=cancellation, baggage_loss=baggage,
                flight_delay=delay, adventure_sports=adventure, active=True,
            ))
            added_i += 1
    click.echo(f'  Insurance plans added: {added_i}')

    db.session.commit()
    click.echo('Transport + activities seed done ✓')


@seed_bp.cli.command('seed-all')
@click.pass_context
def seed_all(ctx):
    """Run all seed commands."""
    ctx.invoke(seed_packages)
    ctx.invoke(seed_reviews)
    ctx.invoke(seed_transport)
    click.echo('All done ✓')
