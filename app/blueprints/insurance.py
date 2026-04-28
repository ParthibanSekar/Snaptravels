"""
Travel Insurance blueprint.
Browse plans, calculate premium, and purchase insurance.
"""
from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from app.models import InsurancePlan, Booking, BookingItem, Notification
from app.services.auth import login_required, get_current_user
from app import db
from datetime import datetime
import uuid

insurance_bp = Blueprint('insurance', __name__, url_prefix='/insurance')


@insurance_bp.route('/', methods=['GET', 'POST'])
def listing():
    plans = InsurancePlan.query.filter_by(active=True).order_by(InsurancePlan.price_per_person_per_day.asc()).all()
    trip_days = int(request.args.get('days', 5))
    persons = int(request.args.get('persons', 1))
    user = get_current_user()
    return render_template('insurance.html', plans=plans, trip_days=trip_days,
                           persons=persons, user=user)


@insurance_bp.route('/quote', methods=['POST'])
def quote():
    """AJAX endpoint to calculate premium."""
    plan_id = request.form.get('plan_id', type=int)
    days = request.form.get('days', 1, type=int)
    persons = request.form.get('persons', 1, type=int)

    plan = InsurancePlan.query.get(plan_id)
    if not plan:
        return jsonify({'error': 'Plan not found'}), 404

    premium = round(plan.price_per_person_per_day * days * persons, 2)
    return jsonify({'premium': premium, 'days': days, 'persons': persons,
                    'plan_name': plan.name})


@insurance_bp.route('/buy/<int:plan_id>', methods=['GET', 'POST'])
@login_required
def buy(plan_id):
    plan = InsurancePlan.query.get_or_404(plan_id)
    trip_days = int(request.args.get('days', 5))
    persons = int(request.args.get('persons', 1))
    premium = round(plan.price_per_person_per_day * trip_days * persons, 2)

    if request.method == 'POST':
        customer_name = request.form.get('customer_name', '').strip()
        customer_email = request.form.get('customer_email', '').strip()
        customer_phone = request.form.get('customer_phone', '').strip()
        start_date = request.form.get('start_date', '')
        end_date = request.form.get('end_date', '')
        destination = request.form.get('destination', '').strip()
        days_val = int(request.form.get('days', trip_days))
        persons_val = int(request.form.get('persons', persons))
        total = round(plan.price_per_person_per_day * days_val * persons_val, 2)

        if not customer_name or not customer_email:
            flash('Please fill in all required fields.', 'danger')
            return redirect(url_for('insurance.buy', plan_id=plan_id, days=days_val, persons=persons_val))

        payment_method = request.form.get('payment_method', 'card').strip() or 'card'
        booking_code = f"ST-INS-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        bk = Booking(
            user_id=session['user_id'],
            booking_code=booking_code,
            total_amount=total,
            customer_name=customer_name,
            customer_email=customer_email,
            customer_phone=customer_phone,
            payment_method=payment_method,
            status='CONFIRMED',
        )
        db.session.add(bk)
        db.session.flush()

        item = BookingItem(
            booking_id=bk.id,
            type='INSURANCE',
            ref_id=plan.id,
            title=f"Travel Insurance — {plan.name} Plan",
            amount=total,
        )
        item.details = {
            'plan_name': plan.name,
            'destination': destination,
            'start_date': start_date,
            'end_date': end_date,
            'days': days_val,
            'persons': persons_val,
            'price_per_person_per_day': plan.price_per_person_per_day,
        }
        db.session.add(item)

        notif = Notification(
            user_id=session['user_id'], type='BOOKING',
            title='Travel Insurance Purchased!',
            message=f"{plan.name} insurance plan confirmed for {persons_val} person(s), {days_val} days. Code: {booking_code}",
            link=url_for('public.booking_confirmation', booking_id=bk.id),
        )
        db.session.add(notif)
        db.session.commit()

        flash(f'Insurance purchased! Code: {booking_code}', 'success')
        return redirect(url_for('public.booking_confirmation', booking_id=bk.id))

    user = get_current_user()
    return render_template('insurance_buy.html', plan=plan, trip_days=trip_days,
                           persons=persons, premium=premium, user=user)
