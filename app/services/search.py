import logging
from app.models import Flight, Hotel
from datetime import datetime
from app import db
from sqlalchemy import func
from app.services.chaos import maybe_fail_search, maybe_fail_db, should_empty_search, should_wrong_search, should_fake_soldout

logger = logging.getLogger('snaptravels.search')

class SearchService:
    @staticmethod
    def search_flights(origin=None, destination=None, depart_date=None, cabin_class=None, passengers=1):
        maybe_fail_search('flight')
        maybe_fail_db('flight_search')
        query = Flight.query

        logger.debug("search_flights origin=%r destination=%r date=%s", origin, destination, depart_date)

        # Handle origin search with flexible matching
        if origin and origin.strip():
            origin_terms = origin.strip().lower()
            # Extract city name before parentheses if present
            if '(' in origin_terms:
                origin_terms = origin_terms.split('(')[0].strip()
            
            query = query.filter(Flight.origin.ilike(f'%{origin_terms}%'))
            logger.debug("  → origin filter: %s", origin_terms)

        # Handle destination search with flexible matching
        if destination and destination.strip():
            destination_terms = destination.strip().lower()
            # Extract city name before parentheses if present  
            if '(' in destination_terms:
                destination_terms = destination_terms.split('(')[0].strip()
                
            query = query.filter(Flight.destination.ilike(f'%{destination_terms}%'))
            logger.debug("  → destination filter: %s", destination_terms)

        # Handle date filtering (make it optional for now)
        if depart_date:
            try:
                if isinstance(depart_date, str):
                    depart_date = datetime.strptime(depart_date, '%Y-%m-%d').date()
                query = query.filter(Flight.depart_date == depart_date)
                logger.debug("  → date filter: %s", depart_date)
            except Exception as e:
                logger.warning("  date filter error: %s", e)

        # Handle cabin class (optional)
        if cabin_class and cabin_class.lower() not in ['any', 'all', '']:
            query = query.filter(Flight.cabin_class.ilike(f'%{cabin_class}%'))
            logger.debug("  → cabin class filter: %s", cabin_class)

        # Handle passenger count
        if passengers and passengers > 0:
            query = query.filter(Flight.seats_left >= passengers)
            logger.debug("  → passengers: %s", passengers)

        # func_search_empty chaos: return empty results immediately
        if should_empty_search():
            logger.info("[CHAOS] func_search_empty active — returning empty flight results")
            return []

        # func_fake_soldout chaos: wipe all results so nothing is bookable
        if should_fake_soldout():
            logger.info("[CHAOS] func_fake_soldout active — returning empty flight results (sold out)")
            return []

        flights = query.order_by(Flight.price.asc()).all()
        logger.debug("search_flights result count=%d", len(flights))

        # func_wrong_search chaos: shuffle results so they appear mismatched
        if flights and should_wrong_search():
            import random as _rnd
            _rnd.shuffle(flights)
            logger.info("[CHAOS] func_wrong_search active — flight results shuffled/mismatched")

        # If still no flights found, try a broader search
        if not flights and (origin or destination):
            logger.debug("No exact matches, broadening search")
            broader_query = Flight.query
            
            if origin and origin.strip():
                # Try partial matches for common city names
                city_variants = [origin.strip().lower()]
                if 'chennai' in origin.lower():
                    city_variants.extend(['chennai', 'madras', 'maa'])
                elif 'mumbai' in origin.lower():
                    city_variants.extend(['mumbai', 'bombay', 'bom'])
                elif 'delhi' in origin.lower():
                    city_variants.extend(['delhi', 'new delhi', 'del'])
                elif 'bangalore' in origin.lower():
                    city_variants.extend(['bangalore', 'bengaluru', 'blr'])
                
                origin_filters = [Flight.origin.ilike(f'%{variant}%') for variant in city_variants]
                broader_query = broader_query.filter(db.or_(*origin_filters))
            
            if destination and destination.strip():
                # Try partial matches for common city names
                city_variants = [destination.strip().lower()]
                if 'chennai' in destination.lower():
                    city_variants.extend(['chennai', 'madras', 'maa'])
                elif 'mumbai' in destination.lower():
                    city_variants.extend(['mumbai', 'bombay', 'bom'])
                elif 'delhi' in destination.lower():
                    city_variants.extend(['delhi', 'new delhi', 'del'])
                elif 'bangalore' in destination.lower():
                    city_variants.extend(['bangalore', 'bengaluru', 'blr'])
                
                dest_filters = [Flight.destination.ilike(f'%{variant}%') for variant in city_variants]
                broader_query = broader_query.filter(db.or_(*dest_filters))
            
            flights = broader_query.order_by(Flight.price.asc()).limit(20).all()
            logger.debug("Broader search found %d flights", len(flights))

        # If still no flights after broadened search, return empty list
        # so the template can show a proper "no results found" message
        if not flights:
            logger.debug("No flights found for search criteria — returning empty")

        return flights

    @staticmethod
    def search_hotels(city=None, checkin=None, checkout=None, guests=1, rooms=1):
        maybe_fail_search('hotel')
        maybe_fail_db('hotel_search')
        query = Hotel.query

        if city:
            query = query.filter(Hotel.city.ilike(f'%{city}%'))

        # func_search_empty chaos: return empty results immediately
        if should_empty_search():
            logger.info("[CHAOS] func_search_empty active — returning empty hotel results")
            return []

        # func_fake_soldout chaos: wipe all results so nothing is bookable
        if should_fake_soldout():
            logger.info("[CHAOS] func_fake_soldout active — returning empty hotel results (sold out)")
            return []

        hotels = query.order_by(Hotel.rating.desc(), Hotel.price_per_night.asc()).all()

        # func_wrong_search chaos: shuffle results so they appear mismatched
        if hotels and should_wrong_search():
            import random as _rnd
            _rnd.shuffle(hotels)
            logger.info("[CHAOS] func_wrong_search active — hotel results shuffled/mismatched")

        if not hotels and city:
            logger.debug("No hotels found for city=%r — returning empty", city)

        return hotels

    @staticmethod
    def get_popular_destinations():
        # Get cities with most flights
        destinations = Flight.query.with_entities(
            Flight.destination, 
            func.count(Flight.id).label('flight_count')
        ).group_by(Flight.destination).order_by(func.count(Flight.id).desc()).limit(6).all()

        return [dest[0] for dest in destinations]

    @staticmethod
    def get_default_flights():
        # Return popular flights sorted by price
        return Flight.query.order_by(Flight.price.asc()).limit(12).all()

    @staticmethod
    def get_default_hotels():
        # Return popular hotels sorted by rating and price
        return Hotel.query.order_by(Hotel.rating.desc(), Hotel.price_per_night.asc()).limit(12).all()