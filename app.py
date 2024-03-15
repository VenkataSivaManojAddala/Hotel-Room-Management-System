# app.py

from flask import Flask, request, jsonify, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hotel.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'vennaalluri3@gmail.com'
app.config['MAIL_PASSWORD'] = 'athgoogle'
app.config['MAIL_DEFAULT_SENDER'] = 'vennaalluri3@gmail.com'
mail = Mail(app)
db = SQLAlchemy(app)

# Define SQLAlchemy models
class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_type = db.Column(db.String(10), nullable=False)
    room_number = db.Column(db.String(10), nullable=False, unique=True)
    total = db.Column(db.Integer, nullable=False)
    available = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Float, nullable=False)
    bookings = db.relationship('Booking', backref='room', lazy=True)

class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    email = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    room_number = db.Column(db.String(10))  # Make sure this line exists

# Initialize database and add initial rooms
@app.before_first_request
def setup():
    db.create_all()
    if not Room.query.all():
        initial_rooms = [
    {
        'room_type': 'A',
        'room_number': 'A101',  # Add room number here
        'total': 2,
        'available': 2,
        'price': 100
    },
    {
        'room_type': 'B',
        'room_number': 'B201',  # Add room number here
        'total': 3,
        'available': 3,
        'price': 80
    },
    {
        'room_type': 'C',
        'room_number': 'C301',  # Add room number here
        'total': 5,
        'available': 5,
        'price': 50
    }
]

        for room_data in initial_rooms:
            room = Room(**room_data)
            db.session.add(room)
        db.session.commit()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/book', methods=['POST'])
def book():
    data = request.json
    room_type = data['room_type']
    room_number = data['room_number']  # Ensure room_number is properly extracted
    start_time = datetime.strptime(data['start_time'], '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(data['end_time'], '%Y-%m-%dT%H:%M')
    email = data['email']

    # Check if start time is after the current time
    if start_time < datetime.now() or start_time>end_time:
        return jsonify({'error': 'Check your dates.'}), 400

    # Check for overlapping bookings
    if Booking.query.filter(Booking.room.has(room_type=room_type), 
                             Booking.room_number == room_number,
                             Booking.start_time < end_time,
                             Booking.end_time > start_time).first():
        return jsonify({'error': 'Booking overlaps with existing booking.'}), 400

    # Calculate price
    duration_hours = (end_time - start_time).total_seconds() / 3600
    room_price = Room.query.filter_by(room_type=room_type).first().price
    price = duration_hours * room_price

    # Book the room
    room = Room.query.filter_by(room_type=room_type).first()
    if room.available > 0:
        booking = Booking(room_id=room.id, start_time=start_time, end_time=end_time, email=email, price=price, room_number=room_number)
        db.session.add(booking)
        db.session.commit()
        room.available -= 1
        db.session.commit()
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'No available rooms of this type.'}), 400

@app.route('/bookings')
def get_bookings():
    bookings = Booking.query.all()
    booking_data = []
    for booking in bookings:
        booking_data.append({
            'id': booking.id,
            'email': booking.email,
            'room_type': booking.room.room_type,
            'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M:%S'),
            'price':booking.price
        })
    return jsonify(booking_data)

@app.route('/get_price', methods=['POST'])
def get_price():
    data = request.json
    room_type = data['room_type']
    start_time = datetime.strptime(data['start_time'], '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(data['end_time'], '%Y-%m-%dT%H:%M')

    # Check if start time is after the current time
    if start_time < datetime.now():
        return jsonify({'error': 'Start time must be in the future.'}), 400

    # Calculate price
    duration_hours = (end_time - start_time).total_seconds() / 3600
    room_price = Room.query.filter_by(room_type=room_type).first().price
    price = duration_hours * room_price

    return jsonify({'price': price}), 200

@app.route('/edit', methods=['POST'])
def edit_booking():
    data = request.json
    email = data['email']
    room_number = data['room_number']
    booking_id = data['booking_id']
    start_time = datetime.strptime(data['start_time'], '%Y-%m-%dT%H:%M')
    end_time = datetime.strptime(data['end_time'], '%Y-%m-%dT%H:%M')

    # Calculate updated price
    duration = (end_time - start_time).total_seconds() / 3600
    updated_price = duration * Booking.query.get(booking_id).room.price

    # Update the booking
    booking = Booking.query.get(booking_id)
    if booking:
        booking.email = email
        booking.room_number = room_number
        booking.start_time = start_time
        booking.end_time = end_time
        booking.price = updated_price
        db.session.commit()
        return jsonify({'success': True}), 200
    else:
        return jsonify({'error': 'Booking not found or cannot be edited.'}), 404
@app.route('/cancel/<int:booking_id>', methods=['POST'])
def cancel_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if booking:
        room_id = booking.room_id
        room = Room.query.get(room_id)
        if room:
            db.session.delete(booking)
            room.available += 1 
            db.session.commit()
            return jsonify({
                'success': True,
                'canceled_booking': {
                    'id': booking.id,
                    'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                    'price': booking.price
                },
                'updated_room_availability': {
                    'room_id': room.id,
                    'available': room.available
                }
            }), 200
        else:
            return jsonify({'error': 'Room not found.'}), 404
    else:
        return jsonify({'error': 'Booking not found or cannot be canceled.'}), 404

@app.route('/view')
def view():
    room_filter = request.args.get('room_filter')
    start_time_filter = request.args.get('start_time')
    end_time_filter = request.args.get('end_time')

    filtered_bookings = {}
    if room_filter:
        rooms = Room.query.filter_by(room_type=room_filter).all()
    else:
        rooms = Room.query.all()

    for room in rooms:
        filtered_bookings[room.room_type] = {
            'available': room.available,
            'booked': []
        }
        for booking in room.bookings:
            if (not start_time_filter or booking.start_time >= datetime.fromisoformat(start_time_filter)) and \
               (not end_time_filter or booking.end_time <= datetime.fromisoformat(end_time_filter)):
                filtered_bookings[room.room_type]['booked'].append({
                    'start_time': booking.start_time.isoformat(),
                    'end_time': booking.end_time.isoformat(),
                    'email': booking.email,
                    'price': booking.price,
                    'room_number': booking.room_number,
                    'id': booking.id
                })

    return jsonify(filtered_bookings)

@app.route('/booking/<int:booking_id>')
def get_booking(booking_id):
    booking = Booking.query.get(booking_id)
    if booking:
        # Return the booking details as JSON
        return jsonify({
            'email':booking.email,
            'room_number':booking.room_number,
            'id': booking.id,
            'start_time': booking.start_time.strftime('%Y-%m-%dT%H:%M'),  # Format as ISO 8601 datetime string
            'end_time': booking.end_time.strftime('%Y-%m-%dT%H:%M')  # Format as ISO 8601 datetime string
            # Add other fields as needed
        })
    else:
        # Return a 404 error if the booking is not found
        return jsonify({'error': 'Booking not found'}), 404

if __name__ == '__main__':
    app.run(debug=True)
