import uuid
import logging
from datetime import datetime
from app.models import Booking, BookingItem, Flight, Hotel, User
from app import db
from app.services.chaos import (
    maybe_fail_checkout, maybe_fail_payment, maybe_fail_db,
    CheckoutChaosError, PaymentChaosError, DatabaseChaosError,
)

logger = logging.getLogger('snaptravels.booking')


class BookingService:
    @staticmethod
    def create_booking(user_id, booking_type, item_id, customer_data, amount, payment_method='card'):
        """Create a new booking"""
        # Chaos hooks: simulate DB slowness, checkout crashes, payment failures.
        # Any ChaosInjectedError returns None so the caller shows the standard
        # "Booking failed" flash — but the APM agent will still capture the
        # exception + trace id before we swallow it.
        try:
            maybe_fail_db('create_booking')
            maybe_fail_checkout(booking_type=booking_type, amount=amount)
            maybe_fail_payment(amount=amount)
        except (CheckoutChaosError, PaymentChaosError, DatabaseChaosError) as ce:
            logger.exception(f"Chaos-induced booking failure: {ce}")
            return None

        try:
            # Generate unique booking code
            booking_code = generate_booking_code()

            # Get user to use email as fallback for name
            user = User.query.get(user_id)
            customer_name = customer_data.get('name', user.email if user else 'Guest')

            # Create booking
            booking = Booking(
                user_id=user_id,
                booking_code=booking_code,
                total_amount=amount,
                customer_name=customer_name,
                customer_email=customer_data.get('email', user.email if user else ''),
                customer_phone=customer_data.get('phone', ''),
                payment_method=payment_method or 'card',
            )
        except Exception as e:
            db.session.rollback()
            logger.error("Error creating booking: %s", e)
            return None

        try:
            db.session.add(booking)
            db.session.flush()  # Get the booking ID

            # Create booking items
            if booking_type == 'FLIGHT':
                flight = Flight.query.get(item_id)
                if flight:
                    booking_item = BookingItem(
                        booking_id=booking.id,
                        type='FLIGHT',
                        ref_id=flight.id,
                        flight_id=flight.id,
                        title=f"{flight.airline} {flight.flight_no}",
                        amount=flight.price
                    )
                    booking_item.details = {
                        'origin': flight.origin,
                        'destination': flight.destination,
                        'depart_time': flight.depart_time,
                        'arrive_time': flight.arrive_time,
                        'cabin_class': flight.cabin_class,
                        'selected_seats': customer_data.get('selected_seats', ''),
                    }
                    db.session.add(booking_item)

                    # Reduce available seats
                    flight.seats_left -= 1

            elif booking_type == 'HOTEL':
                hotel = Hotel.query.get(item_id)
                if hotel:
                    nights = customer_data.get('nights', 1)
                    rooms = customer_data.get('rooms', 1)
                    room_price = customer_data.get('room_price', hotel.price_per_night)
                    room_type = customer_data.get('room_type', 'standard')
                    room_name = customer_data.get('room_name', 'Standard Room')
                    item_amount = float(room_price) * int(nights) * int(rooms)
                    booking_item = BookingItem(
                        booking_id=booking.id,
                        type='HOTEL',
                        ref_id=hotel.id,
                        hotel_id=hotel.id,
                        title=f"{hotel.name} — {room_name}",
                        amount=item_amount
                    )
                    booking_item.details = {
                        'city': hotel.city,
                        'checkin': customer_data.get('checkin'),
                        'checkout': customer_data.get('checkout'),
                        'nights': nights,
                        'rooms': rooms,
                        'room_type': room_type,
                        'room_name': room_name,
                        'room_price_per_night': float(room_price),
                        'rating': hotel.rating
                    }
                    db.session.add(booking_item)

            db.session.commit()

            logger.info('BOOKING_CREATED code=%s user_id=%d type=%s amount=%.2f item_id=%d',
                        booking.booking_code, user_id, booking_type, amount, item_id)
            return booking

        except Exception as e:
            db.session.rollback()
            logger.error("BOOKING_FAILED user_id=%d type=%s error=%s", user_id, booking_type, e)
            return None


    @staticmethod
    def get_user_bookings(user_id):
        return Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc()).all()

# Dummy function to generate booking code, replace with your actual implementation
def generate_booking_code():
    return f"ST-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"