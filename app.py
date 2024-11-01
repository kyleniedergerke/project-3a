from flask import Flask, render_template, request
import requests
import pygal
import csv
from lxml import etree
from datetime import datetime

app = Flask(__name__)
app.config["DEBUG"] = True

# Function to get stock data from Alpha Vantage
def get_stock_data(symbol, function):
    api_key = "3B5JUABSNGNCK67I"
    url = f'https://www.alphavantage.co/query?function={function}&symbol={symbol}&apikey={api_key}'
    response = requests.get(url)
    data = response.json()
    return data

# Load stock symbols from a CSV file using the csv module
def load_stock_symbols():
    stock_symbols = []
    with open('stocks.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            stock_symbols.append(row['Symbol'])  # Assuming the header is 'Symbol'
    return stock_symbols

# Route for the main page
@app.route('/', methods=['GET', 'POST'])
def index():
    stock_data = None
    chart_file = None
    stock_symbols = load_stock_symbols()  # Load stock symbols
    
    if request.method == 'POST':  # Only process form data if it's a POST request
        print("Form data:", request.form)
        try:
            symbol = request.form.get('stock_symbols')
            chart_type = request.form.get('chartType')
            function = request.form.get('timeSeries')
            start_date = request.form.get('startDate')
            end_date = request.form.get('endDate')

            # Validate input
            if not all([symbol, function, start_date, end_date, chart_type]):
                raise ValueError("All fields are required.")

            stock_data = get_stock_data(symbol, function)
            
            #print("Function:", function)  # Log function type
            #print(f"Symbol: {symbol}, Chart type: {chart_type}")  # Log stock symbol and chart type
            #print("Stock data received:", stock_data)

            # Check for errors in the stock data
            if 'Error Message' in stock_data:
                raise ValueError("Invalid stock symbol or function.")

            #print(f"Start date: {start_date}, End date: {end_date}")  # Log date range
            
            # Process and plot data
            dates, open_prices, high_prices, low_prices, closing_prices = process_data(stock_data, start_date, end_date)
            #print("Processed data:", dates, open_prices, high_prices, low_prices, closing_prices)
            
            # Check if any data was returned
            if not dates:
                # Adjust the end date to the last available date in the API response
                last_available_date = max(stock_data["Time Series (Daily)"].keys())
                print(f"No data for the given range. Adjusting end date to: {last_available_date}")
                dates, open_prices, high_prices, low_prices, closing_prices = process_data(stock_data, start_date, last_available_date)

            if not dates:
                raise ValueError("No data available for the adjusted date range.")  # Log processed data

            if dates and open_prices and high_prices and low_prices and closing_prices:
                chart_file = plot_data(dates, open_prices, high_prices, low_prices, closing_prices, chart_type, symbol)
            else:
                raise ValueError("No data available for the given date range.")

        except Exception as e:
            print(f"Error processing request: {str(e)}")
            stock_data = {"error": str(e)}

    return render_template('index.html', stock_symbols=stock_symbols, stock_data=stock_data, chart_file=chart_file)

# Keep the rest of your functions unchanged
def process_data(data, start_date, end_date):
    time_series = data.get("Time Series (Daily)", {})
    print("Available dates in API response:", time_series.keys())  # Log available dates
    dates = []
    open_prices = []
    high_prices = []
    low_prices = []
    closing_prices = []
    
    for date, values in time_series.items():
        if start_date <= date <= end_date:
            dates.append(date)
            open_prices.append(float(values['1. open']))  # Use '1. open' for open price
            high_prices.append(float(values['2. high']))   # Use '2. high' for high price
            low_prices.append(float(values['3. low']))     # Use '3. low' for low price
            closing_prices.append(float(values['4. close']))  # Use '4. close' for closing price

    return dates, open_prices, high_prices, low_prices, closing_prices

def plot_data(dates, open_prices, high_prices, low_prices, closing_prices, chart_type, symbol):
    if chart_type.lower() == 'line':
        chart = pygal.Line(title=f'Stock Price for {symbol}', x_title='Date', y_title='Price')

    elif chart_type.lower() == 'bar':
        chart = pygal.Bar(title=f'Stock Price for {symbol}', x_title='Date', y_title='Price')
    else:
        print("Unsupported chart type.")
        return None
    
    chart.x_labels = dates
    chart.add('Open', open_prices)
    chart.add('High', high_prices)
    chart.add('Low', low_prices)
    chart.add('Close', closing_prices)

    # Save to static folder
    chart_file = 'static/stock_price_chart.svg'
    chart.render_to_file(chart_file)
    return chart_file

# Main program section
app.run(host='0.0.0.0', port=8080)
