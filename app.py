from flask import Flask, render_template, request, redirect, url_for, session,flash,jsonify
from cs50 import SQL
from flask_session import Session
from werkzeug.security import check_password_hash, generate_password_hash
from helpers import apology, login_required
import sqlite3
import json

app = Flask(__name__)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///manager.db")

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/', methods=["GET", "POST"])
def home():
    return render_template('login.html')

@app.route("/signup", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "POST":
        n = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        naam = request.form.get("name")
        names = db.execute("SELECT username FROM users;")
        if n in names or not n:
            return apology("username already exist")
        if not password or password != confirm:
            return apology("password do not match")
        db.execute("INSERT INTO users (username, hash, name) VALUES(?, ?, ?)", n, generate_password_hash(password), naam)
        return redirect("/")

    else:
        return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to dashboard page
        return redirect('/dashboard')

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("dashboard.html")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")
import datetime
@app.route('/dashboard', methods=["GET", "POST"])
@login_required
def dashboard():
    user_id = session.get('user_id')
    total_sales, num_orders = get_total_sales(user_id)
    avg_order_value = total_sales / num_orders if num_orders != 0 else 0
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()

    # Fetch total quantity sold for each product
    c.execute('''
        SELECT pd_name, SUM(quantity) AS total_quantity
        FROM bills
        WHERE id = ?
        GROUP BY pd_name
    ''', (session['user_id'],))
    total_quantity_per_product = c.fetchall()
    # Sort the list in descending order based on the total quantity
    total_quantity_per_product = sorted(total_quantity_per_product, key=lambda x: x[1], reverse=True)

    # Store the first three elements in the top list
    top = total_quantity_per_product[:3]

    # Get current month and year
    current_month = datetime.datetime.now().strftime('%B')
    current_year = datetime.datetime.now().year

    # Fetch expenses data for each category for the current month
    expenses_categories = ['Rent', 'Inventory cost', 'Utility bills', 'Salary', 'Taxes', 'Insurance']
    expenses = {}
    for category in expenses_categories:
        c.execute('''
            SELECT SUM(amount)
            FROM expenses
            WHERE id = ? AND category = ? AND month = ? AND year = ?
        ''', (user_id, category, current_month, current_year))
        expense_amount = c.fetchone()[0]
        expenses[category] = expense_amount if expense_amount else 0

    # Close the database connection
    conn.close()
    return render_template("dashboard.html", total_sales=total_sales, num_orders=num_orders,
                           avg_order_value=avg_order_value, top=top, expenses=expenses, current_month=current_month)




# Define a function to fetch total sales from the database
def get_total_sales(user_id):
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT order_id, bill_total FROM bills WHERE id=?', (user_id,))
    total_sales = c.fetchall()
    conn.close()
    num_orders = len(set(row[0] for row in total_sales))
    total = sum(row[1] for row in total_sales)
    return total, num_orders

@app.route('/history', methods=['GET', 'POST'])
def history():
    if request.method == 'POST':
        selected_date = request.form['selected_date']
        # Connect to the database
        conn = sqlite3.connect('manager.db')
        c = conn.cursor()

        # Fetch orders based on the selected date
        c.execute('SELECT order_id, pd_name, quantity, amount, bill_total, date FROM bills WHERE id = ? AND date = ?', (session['user_id'], selected_date))
        orders = c.fetchall()

        # Close the database connection
        conn.close()

        # Pass the fetched data to the HTML template
        return render_template('history.html', orders=orders, selected_date=selected_date)
    else:
        # Connect to the database
        conn = sqlite3.connect('manager.db')
        c = conn.cursor()

        # Fetch all orders for the current user
        c.execute('SELECT order_id, pd_name, quantity, amount, bill_total, date FROM bills WHERE id = ?', (session['user_id'],))
        orders = c.fetchall()

        # Close the database connection
        conn.close()

        # Pass the fetched data to the HTML template
        return render_template('history.html', orders=orders)


@app.route("/add", methods=["GET","POST"])
def add_p():
    if request.method == "POST":
        p=request.form.get("name")
        q=request.form.get("brand")
        r=request.form.get("quantity")
        s=request.form.get("price")
        db.execute("INSERT INTO inventory (id,pd_name,brand,stock,price) VALUES (?,?,?,?,?)",session['user_id'],p,q,r,s)

        return redirect('/dashboard')


# Route for updating stock details
@app.route('/update_stock', methods=['GET', 'POST'])
def update_stock():
    if request.method == 'POST':
        pd_name = request.form['pd_name']
        new_stock = int(request.form['new_stock'])
        update_price = request.form.get('update_price', False)  # Check if user wants to update price
        new_price = None

        if update_price:
            new_price = float(request.form['new_price'])

        conn = sqlite3.connect('manager.db')
        c = conn.cursor()

        if update_price:
            c.execute('UPDATE inventory SET stock = ?, price = ? WHERE pd_name = ? AND id = ?', (new_stock, new_price, pd_name, session['user_id']))
        else:
            c.execute('UPDATE inventory SET stock = ? WHERE pd_name = ? AND id = ?', (new_stock, pd_name, session['user_id']))

        conn.commit()
        conn.close()

        return redirect('/dashboard')

    conn = sqlite3.connect('manager.db')
    c = conn.cursor()
    c.execute('SELECT pd_name FROM inventory WHERE id = ?', (session['user_id'],))
    products = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template('update_stock.html', products=products)



# Flask route to remove a product from the inventory
@app.route('/remove_product', methods=['GET', 'POST'])
def remove_product():
    # Establish connection to SQLite database
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()

    if request.method == 'POST':
        pd_name = request.form['pd_name']
        # Remove the product from the database
        c.execute('DELETE FROM inventory WHERE pd_name=? AND id=?', (pd_name, session['user_id']))
        conn.commit()
        flash('Product removed successfully', 'success')
        return redirect("/dashboard")

    # Fetch product names from the database to populate the dropdown menu
    c.execute('SELECT pd_name FROM inventory WHERE id=?', (session['user_id'],))
    products = c.fetchall()
    c.close()
    conn.close()

    return render_template('remove_product.html', products=products)


# Function to fetch brand names from the database
def get_brands():
    conn = sqlite3.connect('manager.db')  # Replace 'your_database.db' with your actual database path
    c = conn.cursor()
    c.execute('SELECT DISTINCT brand FROM inventory')
    brands = [row[0] for row in c.fetchall()]
    conn.close()
    return brands

# Function to fetch all products from the database
def get_all_products():
    conn = sqlite3.connect('manager.db')  # Replace 'your_database.db' with your actual database path
    c = conn.cursor()
    c.execute('SELECT pd_name, brand, stock, price FROM inventory')
    products = [{'pd_name': row[0], 'brand': row[1], 'stock': row[2], 'price': row[3]} for row in c.fetchall()]
    conn.close()
    return products

@app.route('/inventory', methods=['GET', 'POST'])
def inventory():
    if request.method == 'POST':
        selected_brand = request.form.get('selected_brand')
        if selected_brand:
            conn = sqlite3.connect('manager.db')  # Replace 'your_database.db' with your actual database path
            c = conn.cursor()
            c.execute('SELECT pd_name, brand, stock, price FROM inventory WHERE brand=?', (selected_brand,))
            products = [{'pd_name': row[0], 'brand': row[1], 'stock': row[2], 'price': row[3]} for row in c.fetchall()]
            conn.close()
        else:
            products = get_all_products()
        return render_template('inventory.html', brands=get_brands(), products=products, selected_brand=selected_brand)
    else:
        return render_template('inventory.html', brands=get_brands(), products=get_all_products(), selected_brand='')


def get_product_info():
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()
    c.execute('SELECT pd_name, price FROM inventory WHERE id=?', (session['user_id'],))

    product_info = c.fetchall()
    conn.close()
    return product_info

@app.route('/billing')
def billing():
    product_info = get_product_info()
    return render_template('billing.html', product_info=product_info)

@app.route('/process_billing', methods=['POST'])
def process_billing():
    # Get form data
    import datetime
    num_products = int(request.form['num_products'])
    selected_products = json.loads(request.form['selected_products'])
    quantities = json.loads(request.form['quantities'])
    amounts = json.loads(request.form['amounts'])
    bill_total = float(request.form['total_bill_amount'])

    # Connect to the database
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()

    # Check if any product's order quantity exceeds its available stock
    exceeded_products = []
    for i in range(num_products):
        pd_name = selected_products[i]
        quantity = quantities[i]

        c.execute('SELECT stock FROM inventory WHERE pd_name = ?', (pd_name,))
        available_stock = c.fetchone()[0]
        if int(quantity) > int(available_stock):
            exceeded_products.append((pd_name, quantity, available_stock))

    if exceeded_products:
        conn.close()
        message = "The following products have order quantities that exceed available stock:\n"
        for product in exceeded_products:
            message += f"Product: {product[0]}, Ordered Quantity: {product[1]}, Available Stock: {product[2]}\n"
        return message

    # Get the maximum order_id for the current user
    c.execute('SELECT MAX(order_id) FROM bills WHERE id = ?', (session['user_id'],))
    max_order_id = c.fetchone()[0]
    if max_order_id is None:
        order_id = 1
    else:
        order_id = max_order_id + 1

    current_date = datetime.date.today()  # Get current date

    # Insert billing records
    for i in range(num_products):
        pd_name = selected_products[i]
        quantity = quantities[i]
        total = amounts[i]

        c.execute('INSERT INTO bills (id, order_id, pd_name, quantity, amount, bill_total, date) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (session['user_id'], order_id, pd_name, quantity, total, bill_total, current_date))

    conn.commit()
    conn.close()
    update_inventory(selected_products, quantities)
    return redirect('/dashboard')


# Function to update the quantity of products sold in the inventory table
def update_inventory(selected_products, quantities):
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()
    for pd_name, quantity in zip(selected_products, quantities):
        c.execute('UPDATE inventory SET stock = stock - ? WHERE pd_name = ? AND id = ?', (quantity, pd_name, session['user_id']))
    conn.commit()
    conn.close()

@app.route('/sales')
def sales():

    return render_template('sales.html')

@app.route('/get_sales_data')
def get_sales_data():
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()
    c.execute("SELECT date, COUNT(*) FROM bills WHERE id = ? GROUP BY date", (session['user_id'],))
    rows = c.fetchall()
    dates = [row[0] for row in rows]
    orders = [row[1] for row in rows]
    conn.close()
    return jsonify({'dates': dates, 'orders': orders})

@app.route('/get_product_names', methods=['GET'])
def get_product_names():
    user_id = session.get('user_id')
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()
    c.execute('SELECT DISTINCT pd_name FROM inventory WHERE id = ?', (user_id,))
    product_names = c.fetchall()
    conn.close()
    return jsonify({'products': product_names})

@app.route('/get_sales_report', methods=['POST'])
def get_sales_report():
  # Get product name from the AJAX request
    product_name = request.form.get('product_name')

    # Connect to the SQLite database
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()

    # Fetch sales data for the selected product
    c.execute('SELECT SUM(quantity), SUM(amount) FROM bills WHERE pd_name = ? AND id = ?', (product_name, session['user_id']))
    sales_data = c.fetchall()

    # Calculate total quantity sold and total revenue generated
    total_quantity_sold = sum(row[0] for row in sales_data)
    total_revenue_generated = sum(row[1] for row in sales_data)

    # Close database connection
    conn.close()

    # Return sales data as JSON response
    return jsonify({
        'total_quantity_sold': total_quantity_sold,
        'total_revenue_generated': total_revenue_generated
    })


@app.route('/expenses', methods=['GET', 'POST'])
def expenses():
    if request.method == 'POST':
        # Handle form submission for custom month and year selection
        selected_month = request.form.get('month')
        selected_year = request.form.get('year')
    else:
        # Get current month and year
        selected_month = datetime.datetime.now().strftime('%B')
        selected_year = datetime.datetime.now().year

    # Connect to the database
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()

    # Get the current session user ID
    user_id = session.get('user_id')

    if selected_month != 'all' and selected_year != 'all':
        # Query expenses for the selected month and year
        c.execute('''
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE month = ? AND year = ? AND id = ?
            GROUP BY category
        ''', (selected_month, selected_year, user_id))
    else:
        # Query expenses for all months till now
        c.execute('''
            SELECT category, SUM(amount) AS total_amount
            FROM expenses
            WHERE id = ?
            GROUP BY category
        ''', (user_id,))

    expenses_data = c.fetchall()

    # Calculate total expenses
    total_expenses = sum(amount for category, amount in expenses_data)

    # Determine the share of each expense category
    expenses_share = [(category, amount / total_expenses * 100) for category, amount in expenses_data]

    # Create a dictionary to store the amount for each category
    category_amount = {category: amount for category, amount in expenses_data}

    conn.close()

    return render_template('expenses.html', expenses_share=expenses_share, category_amount=category_amount,
                            selected_month=selected_month, selected_year=selected_year)


"""@app.route('/add_expense', methods=['POST'])
def add_expense():
    # Get user_id from session
    user_id = session.get('user_id')

    # Extract data from the form
    category = request.form['category']
    amount = request.form['amount']
    month = request.form['month']
    year = request.form['year']

    # Connect to the SQLite database
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()

    # Insert expense data into the expenses table
    c.execute('INSERT INTO expenses (id, category, amount, month, year) VALUES (?, ?, ?, ?, ?)',
              (user_id, category, amount, month, year))

    # Commit changes and close connection
    conn.commit()
    conn.close()

    # Redirect to the expenses page
    return redirect(url_for('expenses'))"""

import sqlite3
from flask import session, request, redirect, url_for, render_template

@app.route('/add_expense', methods=['POST'])
def add_expense():
    if 'user_id' in session:
        user_id = session['user_id']
        category = request.form['category']
        amount = request.form['amount']
        month = request.form['month']
        year = request.form['year']

        # Connect to the SQLite database
        conn = sqlite3.connect('manager.db')
        c = conn.cursor()

        # Check if expense entry already exists for the same category, month, and year
        c.execute("SELECT amount FROM expenses WHERE id=? AND category=? AND month=? AND year=?",
                  (user_id, category, month, year))
        existing_amount = c.fetchone()

        if existing_amount:
            # Prompt the user to confirm adding the new amount to the existing one
            return render_template('confirm.html', category=category, month=month, year=year,
                                   existing_amount=existing_amount[0], new_amount=amount)
        else:
            # Insert the new expense directly
            c.execute('INSERT INTO expenses (id, category, amount, month, year) VALUES (?, ?, ?, ?, ?)',
                      (user_id, category, amount, month, year))
            conn.commit()
            conn.close()
            return redirect('/dashboard')
    else:
        return redirect(url_for('login'))  # Redirect to login page if user not authenticated


@app.route('/confirm_add_expense', methods=['POST'])
def confirm_add_expense():
    if 'user_id' in session:
        if request.method == 'POST':
            action = request.form['action']
            if action == 'add':
                user_id = session['user_id']
                category = request.form['category']
                month = request.form['month']
                year = request.form['year']
                existing_amount = request.form['existing_amount']
                new_amount = request.form['new_amount']

                # Connect to the SQLite database
                conn = sqlite3.connect('manager.db')
                c = conn.cursor()

                # Update the existing expense amount
                updated_amount = float(existing_amount) + float(new_amount)
                c.execute('UPDATE expenses SET amount=? WHERE id=? AND category=? AND month=? AND year=?',
                          (updated_amount, user_id, category, month, year))
                conn.commit()
                conn.close()

                # Return JSON response for action completed
                return redirect("/expenses")

            elif action == 'cancel':
                return 'Expense addition cancelled.'

            else:
                return 'Invalid action.'
    else:
        return redirect(url_for('login'))  # Redirect to login page if user not authenticated








@app.route('/get_sales_details', methods=['POST'])
def get_sales_details():
    selected_product = request.form.get('product')

    # Connect to SQLite database
    conn = sqlite3.connect('manager.db')
    c = conn.cursor()

    # Query to fetch sales data for the selected product
    c.execute("SELECT SUM(quantity) AS total_quantity_sold, SUM(amount) AS total_revenue_generated FROM bills WHERE pd_name = ?", (selected_product,))
    sales_data = c.fetchone()

    # Query to fetch stock left for the selected product
    c.execute("SELECT stock FROM inventory WHERE pd_name = ?", (selected_product,))
    stock_left_data = c.fetchone()

    # Close connection
    conn.close()

    # Check if sales data and stock left are found for the selected product
    if sales_data and stock_left_data:
        total_quantity_sold = sales_data[0] if sales_data[0] else 0
        total_revenue_generated = sales_data[1] if sales_data[1] else 0
        stock_left = stock_left_data[0]

        # Construct the response JSON object
        response = {
            'total_quantity_sold': total_quantity_sold,
            'total_revenue_generated': total_revenue_generated,
            'stock_left': stock_left
        }
        return jsonify(response)
    else:
        return jsonify({'error': 'No sales data or stock left found for the selected product'})










