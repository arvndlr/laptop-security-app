from flask import render_template, flash, redirect, url_for, request, jsonify
from flask_login import current_user, login_user, logout_user, login_required
from app import app, db
from app.forms import LoginForm, RegistrationForm, LaptopForm
from app.models import User, Laptop, SensorReading
from urllib.parse import urlparse
from app.ibeacon_scanner import scan_for_ibeacons
import asyncio

@app.route('/')
@app.route('/index')
@login_required # This decorator requires the user to be logged in
def index():
    # Fetch all laptops belonging to the current user
    laptops = current_user.laptops.all()
    return render_template('index.html', title='Dashboard', laptops=laptops, db=db,
        SensorReading=SensorReading)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)

@app.route('/add_laptop', methods=['GET', 'POST'])
@login_required
def add_laptop():
    form = LaptopForm()
    if form.validate_on_submit():
        ibeacon_uuid_data = request.form.get('ibeacon_uuid')
        ibeacon_major_data = request.form.get('ibeacon_major')
        ibeacon_minor_data = request.form.get('ibeacon_minor')
        ibeacon_rssi_data = request.form.get('ibeacon_rssi')

        if ibeacon_uuid_data and ibeacon_major_data and ibeacon_minor_data:
            laptop = Laptop(
                name=form.name.data,
                serial_number=form.serial_number.data,
                owner=current_user,
                ibeacon_uuid=ibeacon_uuid_data,
                ibeacon_major=int(ibeacon_major_data),
                ibeacon_minor=int(ibeacon_minor_data)
            )
            db.session.add(laptop)
            db.session.commit()

            # CREATE AN INITIAL SENSOR READING
            if ibeacon_rssi_data:
                initial_reading = SensorReading(
                    ibeacon_uuid=laptop.ibeacon_uuid,
                    ibeacon_major=laptop.ibeacon_major,
                    ibeacon_minor=laptop.ibeacon_minor,
                    ibeacon_rssi=int(ibeacon_rssi_data),
                    ultrasonic_distance_cm=0.0,  # Placeholder
                    laptop_id=laptop.id
                )
                db.session.add(initial_reading)
                db.session.commit()

            flash(f"Laptop '{laptop.name}' has been added!", 'success')
            return redirect(url_for('index'))
        else:
            flash('Please select an iBeacon from the list.', 'danger')
            return redirect(url_for('add_laptop'))

    return render_template('add_laptop.html', title='Add a New Laptop', form=form)

@app.route('/scan_ibeacons', methods=['POST'])
@login_required
def scan_ibeacons():
    try:
        # Use asyncio.run() to execute the async function
        beacons = asyncio.run(scan_for_ibeacons(scan_duration=10))
        if beacons:
            return jsonify({'success': True, 'beacons': beacons})
        else:
            return jsonify({'success': False, 'message': 'No iBeacons found.'})
    except Exception as e:
        app.logger.error(f"Error scanning for iBeacons: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/delete_laptop/<int:laptop_id>', methods=['POST'])
@login_required
def delete_laptop(laptop_id):
    laptop = Laptop.query.filter_by(id=laptop_id, user_id=current_user.id).first()
    if laptop is None:
        flash('Laptop not found or you do not have permission to delete it.', 'danger')
        return redirect(url_for('index'))
    
    db.session.delete(laptop)
    db.session.commit()
    flash('Laptop has been deleted.', 'success')
    return redirect(url_for('index'))

@app.route('/laptop_details/<int:laptop_id>')
@login_required
def laptop_details(laptop_id):
    laptop = Laptop.query.filter_by(id=laptop_id, user_id=current_user.id).first_or_404()
    last_reading = SensorReading.query.filter_by(laptop_id=laptop_id).order_by(db.desc(SensorReading.timestamp)).first()

    return render_template('laptop_details.html', title='Laptop Details', laptop=laptop, last_reading=last_reading)

@app.route('/api/sensor_data', methods=['POST'])
def receive_sensor_data():
    try:
        data = request.get_json()
        
        # Validate that required data is present
        required_fields = ['serial_number', 'ibeacon_rssi', 'ultrasonic_distance_cm']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields'}), 400

        # Find the laptop by its serial number
        laptop = Laptop.query.filter_by(serial_number=data['serial_number']).first()

        if laptop:
            # Create a new SensorReading object
            new_reading = SensorReading(
                ibeacon_uuid=laptop.ibeacon_uuid,
                ibeacon_major=laptop.ibeacon_major,
                ibeacon_minor=laptop.ibeacon_minor,
                ibeacon_rssi=data['ibeacon_rssi'],
                ultrasonic_distance_cm=data['ultrasonic_distance_cm'],
                laptop_id=laptop.id
            )
            db.session.add(new_reading)
            db.session.commit()
            
            # --- Place your security logic here ---
            # You can call a function to check if the laptop is stolen
            check_security_status(laptop, new_reading)
            
            return jsonify({'message': 'Sensor data received successfully'}), 200
        else:
            return jsonify({'error': 'Laptop not found'}), 404

    except Exception as e:
        return jsonify({'error': str(e)}), 500

def check_security_status(laptop, reading):
    # RSSI values are typically negative. A weaker signal is a smaller number (e.g., -90 is weaker than -50)
    # Define a threshold for "out of range" or "stolen"
    rssi_threshold = -80  # Adjust this value based on your testing
    ultrasonic_threshold = 200 # Adjust this to your desired distance in cm

    is_out_of_range = reading.ibeacon_rssi < rssi_threshold
    is_far_away = reading.ultrasonic_distance_cm > ultrasonic_threshold

    # A simple example of security logic:
    if is_out_of_range or is_far_away:
        laptop.is_stolen = True
        db.session.commit()
    elif not is_out_of_range and not is_far_away:
        laptop.is_stolen = False
        db.session.commit()

@app.route('/api/latest_reading/<int:laptop_id>', methods=['GET'])
@login_required
def get_latest_reading(laptop_id):
    laptop = Laptop.query.filter_by(id=laptop_id, owner=current_user).first_or_404()
    last_reading = SensorReading.query.filter_by(laptop_id=laptop.id).order_by(db.desc(SensorReading.timestamp)).first()
    
    if last_reading:
        return jsonify({
            'rssi': last_reading.ibeacon_rssi,
            'timestamp': last_reading.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    else:
        return jsonify({
            'rssi': 'N/A',
            'timestamp': 'N/A'
        })