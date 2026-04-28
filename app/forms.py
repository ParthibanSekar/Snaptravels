from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, IntegerField, FloatField, TextAreaField, DateField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, EqualTo, NumberRange, ValidationError, Optional
import re
from datetime import datetime, date, timedelta

def email_validator(form, field):
    """Custom email validator that doesn't require email_validator package"""
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_pattern, field.data):
        raise ValidationError('Invalid email address')

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), email_validator])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

def strong_password(form, field):
    """Enforce: min 8 chars, at least one uppercase, one digit, one special char."""
    pw = field.data or ''
    errors = []
    if len(pw) < 8:
        errors.append('at least 8 characters')
    if not re.search(r'[A-Z]', pw):
        errors.append('one uppercase letter')
    if not re.search(r'[0-9]', pw):
        errors.append('one number')
    if not re.search(r'[^A-Za-z0-9]', pw):
        errors.append('one special character (!@#$%^&* etc.)')
    if errors:
        raise ValidationError('Password must contain: ' + ', '.join(errors) + '.')


class SignupForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), email_validator])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=8, max=128, message='Password must be at least 8 characters'),
        strong_password,
    ])
    password2 = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match')
    ])
    submit = SubmitField('Create Account')


class FlightSearchForm(FlaskForm):
    origin = StringField('From', validators=[Optional(), Length(max=100)],
                        render_kw={'placeholder': 'Origin city (e.g., Chennai, Mumbai)', 'list': 'cities'})
    destination = StringField('To', validators=[Optional(), Length(max=100)],
                             render_kw={'placeholder': 'Destination city (e.g., Delhi, Bangalore)', 'list': 'cities'})
    depart_date = DateField('Departure Date', validators=[Optional()], 
                           default=lambda: date.today() + timedelta(days=1))
    passengers = IntegerField('Passengers', validators=[Optional(), NumberRange(min=1, max=9)], default=1)
    cabin_class = SelectField('Class', choices=[
        ('any', 'Any Class'),
        ('Economy', 'Economy'),
        ('Business', 'Business'), 
        ('First', 'First')
    ], default='any')
    submit = SubmitField('Search Flights')

class HotelSearchForm(FlaskForm):
    city = StringField('City', validators=[DataRequired(), Length(max=100)])
    checkin = DateField('Check-in Date', validators=[DataRequired()])
    checkout = DateField('Check-out Date', validators=[DataRequired()])
    guests = IntegerField('Guests', validators=[DataRequired(), NumberRange(min=1, max=10)], default=2)
    rooms = IntegerField('Rooms', validators=[DataRequired(), NumberRange(min=1, max=5)], default=1)
    submit = SubmitField('Search Hotels')

    def validate_checkout(self, checkout):
        if self.checkin.data and checkout.data <= self.checkin.data:
            raise ValidationError('Check-out date must be after check-in date.')

class BookingForm(FlaskForm):
    customer_name = StringField('Full Name', validators=[
        DataRequired(message='Full name is required'),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters')
    ])
    customer_email = StringField('Email', validators=[
        DataRequired(message='Email is required'),
        email_validator
    ])
    customer_phone = StringField('Phone Number', validators=[
        DataRequired(message='Phone number is required'),
        Length(min=10, max=15, message='Phone number must be between 10 and 15 digits')
    ])

    # Payment method selector
    payment_method = StringField('Payment Method', default='card')

    # Payment fields — validated only when payment_method == 'card'
    card_name = StringField('Name on Card', validators=[
        Optional(),
        Length(min=2, max=100, message='Name must be between 2 and 100 characters')
    ])
    card_number = StringField('Card Number', validators=[Optional()])
    expiry_month = SelectField('Month', choices=[('', '--')] + [(str(i).zfill(2), str(i).zfill(2)) for i in range(1, 13)], validators=[
        Optional()
    ])
    expiry_year = SelectField('Year', choices=[('', '--')] + [(str(i), str(i)) for i in range(2024, 2035)], validators=[
        Optional()
    ])
    cvv = StringField('CVV', validators=[
        Optional(),
        Length(min=3, max=4, message='CVV must be 3 or 4 digits')
    ])

    submit = SubmitField('Complete Booking')

    def validate_customer_name(self, customer_name):
        # Check if name contains only letters and spaces
        if not re.match(r'^[a-zA-Z\s]+$', customer_name.data):
            raise ValidationError('Name must contain only letters and spaces.')

    def validate_customer_email(self, customer_email):
        # Additional email validation
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, customer_email.data):
            raise ValidationError('Please enter a valid email address.')

    def validate_customer_phone(self, customer_phone):
        # Remove all non-digit characters and check if it's all digits
        cleaned_phone = re.sub(r'\D', '', customer_phone.data)
        if not cleaned_phone.isdigit():
            raise ValidationError('Phone number must contain only digits.')
        if len(cleaned_phone) < 10 or len(cleaned_phone) > 15:
            raise ValidationError('Phone number must be between 10 and 15 digits.')

    def validate_card_name(self, card_name):
        if self.payment_method.data != 'card':
            return  # Skip card validation for non-card payments
        if not card_name.data:
            raise ValidationError('Name on card is required.')
        if not re.match(r'^[a-zA-Z\s]+$', card_name.data):
            raise ValidationError('Name on card must contain only letters and spaces.')

    def validate_card_number(self, card_number):
        if self.payment_method.data != 'card':
            return
        if not card_number.data:
            raise ValidationError('Card number is required.')
        cleaned = re.sub(r'\s+', '', card_number.data)
        if not cleaned.isdigit():
            raise ValidationError('Card number must contain only digits.')
        if len(cleaned) < 13 or len(cleaned) > 19:
            raise ValidationError('Card number must be between 13 and 19 digits.')

    def validate_cvv(self, cvv):
        if self.payment_method.data != 'card':
            return
        if not cvv.data:
            raise ValidationError('CVV is required.')
        if not cvv.data.isdigit():
            raise ValidationError('CVV must contain only digits.')
        if len(cvv.data) not in [3, 4]:
            raise ValidationError('CVV must be 3 or 4 digits.')

    def validate_expiry_month(self, expiry_month):
        if self.payment_method.data != 'card':
            return
        try:
            month = int(expiry_month.data)
            if month < 1 or month > 12:
                raise ValidationError('Please select a valid month.')
        except (ValueError, TypeError):
            raise ValidationError('Please select a valid month.')

    def validate_expiry_year(self, expiry_year):
        if self.payment_method.data != 'card':
            return
        try:
            year = int(expiry_year.data)
            current_year = datetime.now().year
            if year < current_year:
                raise ValidationError('Card has expired. Please use a valid card.')
            if year > current_year + 20:
                raise ValidationError('Please select a valid expiry year.')
        except (ValueError, TypeError):
            raise ValidationError('Please select a valid year.')

class RoundTripSearchForm(FlaskForm):
    trip_type = SelectField('Trip Type', choices=[
        ('one_way', 'One Way'),
        ('round_trip', 'Round Trip'),
    ], default='one_way')
    origin = StringField('From', validators=[Optional(), Length(max=100)],
                         render_kw={'placeholder': 'Origin city (e.g., Chennai, Mumbai)'})
    destination = StringField('To', validators=[Optional(), Length(max=100)],
                              render_kw={'placeholder': 'Destination city'})
    depart_date = DateField('Departure', validators=[Optional()],
                            default=lambda: date.today() + timedelta(days=1))
    return_date = DateField('Return', validators=[Optional()])
    passengers = IntegerField('Passengers', validators=[Optional(), NumberRange(min=1, max=9)], default=1)
    cabin_class = SelectField('Class', choices=[
        ('any', 'Any Class'),
        ('Economy', 'Economy'),
        ('Business', 'Business'),
        ('First', 'First'),
    ], default='any')
    submit = SubmitField('Search Flights')


class ReviewForm(FlaskForm):
    rating = SelectField('Rating', choices=[
        ('5', '★★★★★  Excellent'),
        ('4', '★★★★☆  Good'),
        ('3', '★★★☆☆  Average'),
        ('2', '★★☆☆☆  Poor'),
        ('1', '★☆☆☆☆  Terrible'),
    ], validators=[DataRequired()])
    title = StringField('Review Title', validators=[Optional(), Length(max=150)])
    comment = TextAreaField('Your Review', validators=[Optional(), Length(max=2000)])
    submit = SubmitField('Submit Review')


class PackageBookingForm(FlaskForm):
    customer_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    customer_email = StringField('Email', validators=[DataRequired(), email_validator])
    customer_phone = StringField('Phone', validators=[DataRequired(), Length(min=10, max=15)])
    persons = IntegerField('Number of Persons', validators=[DataRequired(), NumberRange(min=1, max=8)], default=2)
    travel_date = DateField('Preferred Travel Date', validators=[DataRequired()])
    promo_code = StringField('Promo Code', validators=[Optional(), Length(max=30)])
    special_requests = TextAreaField('Special Requests', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Confirm Booking')


class FlightFormAdmin(FlaskForm):
    airline = StringField('Airline', validators=[DataRequired(), Length(max=100)])
    flight_no = StringField('Flight Number', validators=[DataRequired(), Length(max=20)])
    origin = StringField('Origin', validators=[DataRequired(), Length(max=100)])
    destination = StringField('Destination', validators=[DataRequired(), Length(max=100)])
    depart_time = StringField('Departure Time (HH:MM)', validators=[DataRequired()])
    arrive_time = StringField('Arrival Time (HH:MM)', validators=[DataRequired()])
    duration_mins = IntegerField('Duration (minutes)', validators=[DataRequired(), NumberRange(min=30, max=1440)])
    price = FloatField('Price', validators=[DataRequired(), NumberRange(min=0)])
    seats_left = IntegerField('Available Seats', validators=[DataRequired(), NumberRange(min=0, max=500)])
    cabin_class = SelectField('Cabin Class', choices=[
        ('Economy', 'Economy'),
        ('Business', 'Business'),
        ('First', 'First Class')
    ], default='Economy')
    submit = SubmitField('Save Flight')

    def validate_depart_time(self, depart_time):
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', depart_time.data):
            raise ValidationError('Time must be in HH:MM format.')

    def validate_arrive_time(self, arrive_time):
        if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', arrive_time.data):
            raise ValidationError('Time must be in HH:MM format.')