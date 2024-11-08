from flask import Flask, render_template, request
import requests
import pygal
import csv
from datetime import datetime
import os

app = Flask(__name__)
app.config["DEBUG"] = True


# Function checks date inputs
def validate_dates(start_date, end_date):
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')
        if end < start:
            return False, "End date must be after start date"
        if end > datetime.now():
            return False, "End date cannot be in the future"
        return True, ""
    except ValueError:
        return False, "Invalid date format. Use YYYY-MM-DD"


# Function gets data from Slpha Vantage
def get_stock_data(symbol, function):
    api_key = "3B5JUABSNGNCK67I"
    url = f'https://www.alphavantage.co/query?function={function}&symbol={symbol}&apikey={api_key}'
    if function == "TIME_SERIES_INTRADAY":
        url += "&interval=5min"
    response = requests.get(url)
    return response.json()

# Load ticker symbols from CSV
def load_stock_symbols():
    stock_symbols = []
    try:
        with open('stocks.csv', newline='') as csvfile:
            reader = csv.DictReader(csvfile)
            return [row['Symbol'] for row in reader]
    except FileNotFoundError:
        return []

# Main route
@app.route('/', methods=['GET', 'POST'])
def index():
    stock_data, chart_file, error_message = None, None, None
    stock_symbols = load_stock_symbols()
    
    if request.method == 'POST':
        try:
            symbol, chart_type, function, start_date, end_date = (
                request.form.get('stock_symbols'),
                request.form.get('chartType'),
                request.form.get('timeSeries'),
                request.form.get('startDate'),
                request.form.get('endDate')
            )

            if not all([symbol, function, start_date, end_date, chart_type]):
                raise ValueError("All fields are required")
            is_valid, date_error = validate_dates(start_date, end_date)
            if not is_valid:
                raise ValueError(date_error)
            stock_data = get_stock_data(symbol, function)
            
            if 'Error Message' in stock_data:
                raise ValueError("API Error: Invalid symbol or function.")
            dates, open_prices, high_prices, low_prices, closing_prices = process_data(stock_data, start_date, end_date, function)
            if dates:
                chart_file = plot_data(dates, open_prices, high_prices, low_prices, closing_prices, chart_type, symbol)
            else:
                raise ValueError("No data available for the selected date range")

        except ValueError as e:
            error_message = str(e)
    
    return render_template('index.html', 
                           stock_symbols=stock_symbols,
                           stock_data=stock_data,
                           chart_file=chart_file,
                           error_message=error_message)

# Process data 
def process_data(data, start_date, end_date, function):
    time_series_key = {
        "TIME_SERIES_DAILY": "Time Series (Daily)",
        "TIME_SERIES_WEEKLY": "Weekly Time Series",
        "TIME_SERIES_MONTHLY": "Monthly Time Series",
        "TIME_SERIES_INTRADAY": "Time Series (5min)"
    }.get(function, None)

    time_series = data.get(time_series_key, {})
    dates, open_prices, high_prices, low_prices, closing_prices = [], [], [], [], []
    
    for date, values in time_series.items():
        compare_date = date.split()[0] if function == "TIME_SERIES_INTRADAY" else date
        if start_date <= compare_date <= end_date:
            dates.append(date)
            open_prices.append(float(values.get('1. open', 0)))
            high_prices.append(float(values.get('2. high', 0)))
            low_prices.append(float(values.get('3. low', 0)))
            closing_prices.append(float(values.get('4. close', 0)))

    return dates, open_prices, high_prices, low_prices, closing_prices

# Plot stock data
def plot_data(dates, open_prices, high_prices, low_prices, closing_prices, chart_type, symbol):
    chart = pygal.Line(title=f'Stock Price for {symbol}', x_title='Date', y_title='Price', x_label_rotation=45) if chart_type.lower() == 'line' else pygal.Bar(title=f'Stock Price for {symbol}', x_title='Date', y_title='Price', x_label_rotation=45)
    chart.x_labels = [datetime.strptime(date, '%Y-%m-%d %H:%M:%S').strftime('%Y-%m-%d %H:%M') if ' ' in date else date for date in dates]
    chart.add('Open', open_prices)
    chart.add('High', high_prices)
    chart.add('Low', low_prices)
    chart.add('Close', closing_prices)
    chart_file = 'static/stock_price_chart.svg'
    chart.render_to_file(chart_file)
    return chart_file

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)