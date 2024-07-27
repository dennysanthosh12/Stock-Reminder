import time
import threading
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import schedule

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///stocks.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

sender_email = "s8602120@gmail.com"
sender_password = "wbjhagbzhroiiwno"
recipient_email = "dennysanthosh@gmail.com"
smtp_server = "smtp.gmail.com"  
smtp_port = 587  

class Stock(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    api = db.Column(db.String(200), nullable=False)
    threshold = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'Stock({self.name}, {self.api}, {self.threshold})'

with app.app_context():
    db.create_all()

@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        stock_name = request.form['stockname']
        stock_api = request.form['stockapi']
        
        new_stock = Stock(name=stock_name, api=stock_api)
        db.session.add(new_stock)
        db.session.commit()
        
        return redirect(url_for('home'))
    
    stocks = Stock.query.all()
    return render_template('index.html', stocks=stocks)

@app.route('/update_threshold/<int:stock_id>', methods=['POST'])
def update_threshold(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    threshold = request.form['threshold']
    stock.threshold = float(threshold)
    db.session.commit()
    return redirect(url_for('home'))

@app.route('/delete_stock/<int:stock_id>', methods=['POST'])
def delete_stock(stock_id):
    stock = Stock.query.get_or_404(stock_id)
    db.session.delete(stock)
    db.session.commit()
    return redirect(url_for('home'))

def check_api_and_send_email(stock):
    try:
        response = requests.get(stock.api)
        if response.status_code == 200:
            data = response.json()
            if data['candles']:
                last_candle = data['candles'][-1]  # Get the last list
                last_value = last_candle[1]  # Get the second element
                if last_value > stock.threshold:
                    send_email(stock, last_value)
                    with app.app_context():
                        db.session.delete(stock)
                        db.session.commit()
                    return True  # Indicate that an email was sent and stock was deleted
        return False
    except:
        errorMail('check_api_and_send_email')  # Indicate that no email was sent

def send_email(stock, value):
    subject = "Value Exceeded Threshold"
    body = f"The value {value} for {stock.name} has exceeded the threshold of {stock.threshold}."
    
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, recipient_email, text)
            print("Email sent successfully")
            return
    except Exception as e:
        print(f"Error sending email: {e}")

def errorMail(content):
    subject = 'Error occured'
    body=f'Error occured in the {content} phase !!'

    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            text = msg.as_string()
            server.sendmail(sender_email, recipient_email, text)
            print("Email sent successfully")
    except Exception as e:
        print(f"Error sending email: {e}")

def run_scheduler():
    schedule.every(5).seconds.do(check_all_stocks)
    while True:
        schedule.run_pending()
        time.sleep(1)

def check_all_stocks():
    try:

        with app.app_context():
            stocks = Stock.query.all()
            if stocks is None:
                check_all_stocks()
            for stock in stocks:
                if stock.threshold is not None:
                    if check_api_and_send_email(stock):
                        break 
        
    except:
       errorMail('check_all_stocks') # Stop further checks after sending an email and deleting a stock

if __name__ == '__main__':
    # Start the scheduler in a separate thread
    scheduler_thread = threading.Thread(target=run_scheduler)
    scheduler_thread.start()
    
    # Run the Flask app
    app.run(debug=True, host='0.0.0.0')
