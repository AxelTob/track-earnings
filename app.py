from flask import Flask, jsonify, request, render_template
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
from flask_cors import CORS

app = Flask(__name__)
# CORS(app, resources={r"/earnings/*": {"origins": "http://localhost:3000"}})


# use database earnings.db, if it doesn't exist, create it
basedir = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(basedir, 'earnings.db')
db_uri = 'sqlite:///' + db_path
app.config['SQLALCHEMY_DATABASE_URI'] = db_uri

# initialize the database
db = SQLAlchemy(app)

# Default values
view = "monthly"
# current year and month with day 1
global date_state

date_state = datetime.now().replace(day=1)


class Earnings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Float, nullable=False)


# run create all in order to create the database, run in application context
with app.app_context():
    db.create_all()


@app.route('/')
def home():
    return get_monthly_earnings()


@app.route('/yearly', methods=['GET'])
def get_yearly_earnings(command):
    if command == "next":
        year = int(year) + 1
    elif command == "prev":
        year = int(year) - 1
    # Parse the year string to a date object
    year_date = datetime.strptime(year, '%Y')
    # Get the first and last day of the year
    start_date = year_date.replace(month=1, day=1)
    end_date = year_date.replace(month=12, day=31)

    # Query the database for earnings within the date range
    yearly_earnings = Earnings.query.filter(
        Earnings.date >= start_date, Earnings.date <= end_date).all()
    if not yearly_earnings:
        return jsonify({'error': 'Earning not found'}), 404
    # sum the earnings for each month using yearly_earnings
    result = [{'month': earning.date.strftime('%B'), 'amount': earning.amount}
              for earning in yearly_earnings]
    # Get the total amount of earnings for the year
    response = jsonify({'year': year, 'data': result})
    return render_template('index.html', values=response,
                           labels=["January", "February", "March", "April", "May", "June",
                                   "July", "August", "September", "October", "November", "December"],
                           max=max(result, key=lambda x: x['amount'])[
                               'amount'],
                           min=min(result, key=lambda x: x['amount'])[
                               'amount'],
                           avg=sum([x['amount'] for x in result])/len(result),
                           legend='Yearly Earnings',
                           chart_type='bar')


@app.route('/monthly', methods=['GET'])
def get_monthly_earnings(command=None):
    global date_state
    # command is a parameter that is passed in when the user clicks on the next or previous button
    command = request.args.get('command')
    if command == "next":
        # add one month to date_state
        date_state = date_state.replace(month=date_state.month + 1)
    if command == "prev":
        date_state = date_state.replace(month=date_state.month - 1)

    print(date_state)
    # Get the first and last day of the month
    start_date = date_state.replace(day=1)
    end_date = date_state.replace(day=monthrange(
        date_state.year, date_state.month)[1])

    # Query the database for earnings within the date range
    monthly_earnings = Earnings.query.filter(
        Earnings.date >= start_date, Earnings.date <= end_date).all()
    result = []
    days_in_month = monthrange(date_state.year, date_state.month)[1]
    dates = [date_state.replace(day=day).strftime('%Y-%m-%d')
             for day in range(1, days_in_month + 1)]
    amounts = [
        next((earning.amount for earning in monthly_earnings if earning.date.strftime(
            '%Y-%m-%d') == date), 0)
        for date in dates
    ]
    # Get the total amount of earnings for the month
    return render_template('index.html', values=amounts,
                           labels=dates,
                           max=max(amounts),
                           avg=sum(amounts)/len(amounts),
                           legend='Monthly Earnings',
                           chart_type='line',
                           year=date_state.year,
                           month=date_state.strftime('%B'),
                           total=sum(amounts))


@ app.route('/add_earning', methods=['POST'])
def add_earnings():
    # get date and amount from parameters
    print(request.args.get('date'))
    print(request.args.get('amount'))
    try:
        date = datetime.strptime(request.args.get('date'), '%Y-%m-%d')
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400
    try:
        amount = float(request.args.get('amount'))
    except ValueError:
        return jsonify({'error': 'Invalid amount format'}), 400

    if not date or not amount:
        return jsonify({'error': 'Invalid data'}), 400

    earning = Earnings(date=date, amount=amount)
    db.session.add(earning)
    db.session.commit()
    response = jsonify({'message': 'Earning added successfully'})
    response.headers.add('Access-Control-Allow-Origin', '*')
    return response, 201


def monthrange(year, month):
    """Return weekday (0-6 ~ Mon-Sun) and number of days (28-31) for year,month."""
    year = int(year)
    month = int(month)
    import calendar
    return calendar.monthrange(year, month)


if __name__ == '__main__':
    app.run(debug=True)
