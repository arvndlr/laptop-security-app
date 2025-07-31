# Laptop Security App

## Description

The Laptop Security App is a web application built with Flask that allows you to monitor the security of your laptops using iBeacon and ultrasonic sensor data. The app tracks the proximity of registered laptops and alerts you if a laptop is moved beyond a safe distance.

## Features

* **User Authentication:** Secure user registration and login.
* **Laptop Management:** Add, view, and delete laptops with their serial numbers.
* **iBeacon Tagging:** Associate a Holyiot iBeacon tag with each laptop.
* **Real-time Monitoring:** Receives and processes sensor data from a Raspberry Pi.
* **RSSI Tracking:** Monitors the Received Signal Strength Indicator (RSSI) of the iBeacon.
* **Ultrasonic Distance:** Tracks the distance of the laptop from a secure location.
* **Security Status:** Automatically marks a laptop as 'stolen' if it is moved too far.

## Installation

### Prerequisites

* Python 3.8+
* pip (Python package installer)
* A running MySQL or SQLite database

### Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/arvndlr/laptop-security-app.git](https://github.com/arvndlr/laptop-security-app.git)
    cd laptop-security-app
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure the database:**
    Open the `config.py` file and update the `SQLALCHEMY_DATABASE_URI` to point to your database. For example:
    ```python
    # For MySQL
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://user:password@localhost/db_name'
    # For SQLite (default)
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///app.db'
    ```

5.  **Initialize the database:**
    ```bash
    flask db upgrade
    ```

6.  **Run the application:**
    ```bash
    flask run
    ```
    The application will be running at `http://127.0.0.1:5000`.

## Usage

1.  **Register an account:** Create a new user account on the website.
2.  **Add a new laptop:** Navigate to the "Add Laptop" page to register a laptop and associate it with a Holyiot iBeacon. The application will scan for nearby iBeacons and their RSSI values.
3.  **Monitor your dashboard:** The main dashboard will show the status of all your registered laptops.
4.  **Sending sensor data from a Raspberry Pi:** Your Raspberry Pi can send sensor data to the app's API endpoint.

### API Endpoint

The app provides an API endpoint for a Raspberry Pi sensor to post data:

**Endpoint:** `POST /api/sensor_data`
**URL:** `http://127.0.0.1:5000/api/sensor_data`
**Headers:** `Content-Type: application/json`
**Body:**
```json
{
    "serial_number": "YOUR_LAPTOP_SERIAL",
    "ibeacon_rssi": -65,
    "ultrasonic_distance_cm": 50.2
}