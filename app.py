import csv
from flask import Flask, render_template, request, abort, current_app
from flask_session import Session
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
import pandas as pd

# Configure application
app = Flask(__name__)

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
def index():
    return render_template("index.html")

# Define available parameters and their CSV column names
AVAILABLE_PARAMETERS = {
    'humidity': 'rht_humidity',
    'temperature': 'rht_temperature',
    'eco2': 'gas_eco2',
    'tvoc': 'gas_tvoc',
    'lux': 'light_lux',
    'uvi': 'light_uvi'
    }

# Common timeframe options
TIMEFRAME_OPTIONS = {
    'last_hour': timedelta(hours=1),
    'last_day': timedelta(days=1),
    'last_week': timedelta(days=7),
    'last_month': timedelta(days=30),
    'custom': None  # For custom date range
}

@app.route("/table", methods=["POST"])
def table():

    selected_params = [param for param in AVAILABLE_PARAMETERS.keys()
                      if param in request.form]

    timeframe = request.form.get('timeframe', 'last_day')


    if not selected_params:
        return "No parameters selected", 404

    if not timeframe:
        return "No timeframe selected", 404

    if timeframe == 'custom':
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        if not start_date or not end_date:
            return "If selected custom, must provide date", 404



    try:
        # Get the corresponding CSV column names
        selected_columns = [AVAILABLE_PARAMETERS[param] for param in selected_params]

        # Always include timestamp column
        if 'timestamp' not in selected_columns:
            selected_columns.insert(0, 'timestamp')

        # Read CSV with timestamp parsing
        df = pd.read_csv('synth_sensor_data.csv',
                        usecols=selected_columns,
                        parse_dates=['timestamp'])


        # Filter data based on timeframe
        if timeframe == 'custom' and start_date and end_date:
            # Convert date strings to datetime objects
            start_datetime = pd.to_datetime(start_date)
            end_datetime = pd.to_datetime(end_date) + timedelta(days=1) - timedelta(seconds=1)
            # This makes end_datetime be 23:59:59 of the selected end date

            mask = (df['timestamp'] >= start_datetime) & (df['timestamp'] <= end_datetime)
        else:
            current_time = datetime.now()
            delta = TIMEFRAME_OPTIONS.get(timeframe, TIMEFRAME_OPTIONS['last_day'])
            start_time = current_time - delta
            mask = df['timestamp'] >= start_time

        # Apply the time filter
        df = df[mask]

        # Format timestamp for display
        df['timestamp'] = df['timestamp'].dt.strftime('%Y-%m-%d %H:%M')

         # Round all numeric columns to 2 decimal places
        numeric_columns = df.select_dtypes(include=['float64', 'float32', 'int64', 'int32']).columns
        df[numeric_columns] = df[numeric_columns].round(2)

        column_renames = {
            'timestamp': 'Time',
            'rht_humidity': 'Humidity (%)',
            'rht_temperature': 'Temperature (°C)',
            'gas_eco2': 'CO2 Concentration (ppm)',
            'gas_tvoc': "Total Volatile Organic Compounds (ppb)",
            'light_lux': "Light Intensity",
            'light_uvi': "UV Index"
        }

        df = df.rename(columns={col: column_renames[col] for col in df.columns if col in column_renames})

        #convert dataframe to html and modificate
        table_html = df.to_html(
            classes='table',
            index = False,
            justify='left'
        )

        return render_template('result_table.html',
                             table=table_html,
                             parameters=selected_params,
                             timeframe=timeframe,
                             start_date=start_date if timeframe == 'custom' else None,
                             end_date=end_date if timeframe == 'custom' else None)

    except Exception as e:
        return f"Error processing data: {str(e)}", 500


@app.route("/chart/", methods=["GET", "POST"])
@app.route("/chart/<period>", methods=["GET", "POST"])
@app.route("/chart/<period>/<date>", methods=["GET", "POST"])
#if theres no period, set it to day
def chart(period = "day", date=None):

    if request.method == "POST":
        #check values omitted
        if not request.form.get("datatype"):
            datatype = "rht_humidity"

        if request.form.get("datatype") not in ["rht_humidity", "rht_temperature", "gas_eco2", "gas_tvoc", "light_lux", "light_uvi"]:
            abort(404)

        datatype = request.form.get("datatype")

    else: #if method=GET
        datatype = "rht_humidity"

    #this will be executed no matter the method:

    #validate period
    valid_periods = ['day','week','month','year']
    if period not in valid_periods:
        abort(404)

    #get current date
    if date == None:
        current_date = datetime.now()
    else:
        try:
            current_date = datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            current_date = datetime.now()

    #calculate start date based on the period and current_date
    if period == "day":
        start_date = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(days=1)
    elif period == "week":
        # Set to the beginning of the current week (assuming week starts on Monday)
        start_date = (current_date - timedelta(days=current_date.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date + timedelta(weeks=1)
    elif period == 'month':
        # Set to the beginning of the current month
        start_date = current_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = (start_date + timedelta(days=32)).replace(day=1)
    else:  # year
        # Set to the beginning of the current year
        start_date = current_date.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        end_date = start_date.replace(year=start_date.year + 1)


    #fetch and process data
    data = fetch_data(start_date, end_date, datatype)

    values = [item[datatype] for item in data]
    try:
        avg = round(np.mean(values), 2)
        mini = round(min(values), 2)
        maxi = round(max(values), 2)
    except ValueError:
        avg = None
        mini = None
        maxi = None

    num = len(data)


    processed_data = process_data(data, period, start_date, end_date, datatype)

    #define dictionary for transmitting datatypeinfo
    datatype_info = {
        "rht_humidity": {"name": "Humidity", "unit": "%"},
        "rht_temperature": {"name": "Temperature", "unit": "°C"},
        "gas_eco2": {"name": "CO2 concentration", "unit": "ppm"},
        "gas_tvoc": {"name": "Total volatile compounds", "unit": "ppb"},
        "light_lux": {"name": "Light intensity", "unit": "lux"},
        "light_uvi": {"name": "UV index", "unit": ""}
    }
    #get infos based on current datatype
    current_info = datatype_info.get(datatype, {"name": "Unknown", "unit": "Unknown"})

    context = {
        'selected_period': period,
        'current_date': current_date,
        'start_date': start_date,
        'end_date': end_date,
        'sensor_data': processed_data,
        'periods': valid_periods,  # Add this to make periods available in template
        'timedelta': timedelta,
        'datatype': datatype,
        'name': current_info["name"],
        'unit': current_info["unit"],
        'mini' : mini,
        'maxi' : maxi,
        'avg' : avg,
        'num' : num
        }


      # Determine which template to use
    template_name = f'chart_{period}.html' if f'chart_{period}.html' in current_app.jinja_env.list_templates() else 'chart.html'

    return render_template(template_name, **context)

def fetch_data(start_date, end_date, datatype):
    csv_file ="synth_sensor_data.csv"
    sensor_data = []
    with open(csv_file) as file:
        reader = csv.DictReader(file)
        for row in reader:
            row_timestamp = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")
            if start_date <= row_timestamp <= end_date:
                sensor_data.append({
                    "timestamp": datetime.fromisoformat(row["timestamp"]),
                    datatype: float(row[datatype])
                    })
    return sensor_data

    #timestamp,rht_humidity,rht_temperature,gas_eco2,gas_tvoc,light_lux,light_uvi

def process_data(data, period, start_date, end_date, datatype):

    aggregated_data = defaultdict(lambda: {'count': 0, datatype: 0})

    # Define time delta and formatting based on period
    if period == 'day':
        delta = timedelta(hours=1)
        format_key = lambda dt: dt.replace(minute=0, second=0, microsecond=0)
    elif period == 'week':
        delta = timedelta(days=1)
        format_key = lambda dt: dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'month':
        delta = timedelta(days=1)
        format_key = lambda dt: dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == 'year':
        #delta = timedelta(days=1)
        #format_key = lambda dt: dt.replace(hour=0, minute=0, second=0, microsecond=0)
        format_key = lambda dt: dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    else:
        raise ValueError(f"Invalid period: {period}")

    # Aggregate data
    for item in data:
        key = format_key(item['timestamp'])
        aggregated_data[key]['count'] += 1
        aggregated_data[key][datatype] += item[datatype]

    # Prepare result with all time points
    result = []
    current_time = format_key(start_date)

    if period == 'year':
        # For year view, always create 12 monthly data points
        for month in range(1, 13):
            month_date = start_date.replace(month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
            if month_date in aggregated_data:
                value = aggregated_data[month_date]
                result.append({
                    'timestamp': month_date.isoformat(),
                    datatype: value[datatype] / value['count'],
                })
            else:
                result.append({
                    'timestamp': month_date.isoformat(),
                    datatype: None
                })
    else:

        while current_time < end_date:
            if current_time in aggregated_data:
                value = aggregated_data[current_time]
                result.append({
                    'timestamp': current_time.isoformat(),
                    datatype: value[datatype] / value['count'],
                })
            else:
                result.append({
                    'timestamp': current_time.isoformat(),
                    datatype: None
                })
            current_time += delta

    return result


if __name__ == '__main__':
    app.run(debug=True)
