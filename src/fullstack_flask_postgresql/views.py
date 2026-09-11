"""Supermarket views — products, customers, purchases, receipts."""
import psycopg
from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from .db import get_db

bp = Blueprint("views", __name__, url_prefix="/views")


# ---------- Dashboard ----------

@bp.route("/")
def dashboard():
    return render_template("dashboard.html")


# ---------- Products ----------

@bp.route("/create-product", methods=("GET", "POST"))
def create_product():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO products (name, barcode, category, price, stock) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                request.form["name"],
                request.form.get("barcode") or None,
                request.form.get("category") or None,
                request.form["price"],
                request.form["stock"],
            ),
        )
        db.commit()
        return redirect(url_for("views.list_products"))
    return render_template("views/create-product.html")


@bp.route("/list-products")
def list_products():
    products = get_db().execute("SELECT * FROM products ORDER BY id").fetchall()
    return render_template("views/list-products.html", products=products)


@bp.route("/edit-product/<int:product_id>", methods=("GET", "POST"))
def edit_product(product_id):
    db = get_db()
    if request.method == "POST":
        db.execute(
            "UPDATE products SET name=%s, barcode=%s, category=%s, price=%s, stock=%s "
            "WHERE id=%s",
            (
                request.form["name"],
                request.form.get("barcode") or None,
                request.form.get("category") or None,
                request.form["price"],
                request.form["stock"],
                product_id,
            ),
        )
        db.commit()
        return redirect(url_for("views.list_products"))
    product = db.execute(
        "SELECT * FROM products WHERE id = %s", (product_id,)
    ).fetchone()
    if product is None:
        abort(404)
    return render_template("views/edit-product.html", product=product)


@bp.route("/delete-product/<int:product_id>", methods=("GET", "POST"))
def delete_product(product_id):
    db = get_db()
    db.execute("DELETE FROM products WHERE id = %s", (product_id,))
    db.commit()
    return redirect(url_for("views.list_products"))


# ---------- Customers ----------

@bp.route("/create-customer", methods=("GET", "POST"))
def create_customer():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO customers (name, tax_id, email, phone, address) "
            "VALUES (%s, %s, %s, %s, %s)",
            (
                request.form["name"],
                request.form.get("tax_id") or None,
                request.form.get("email") or None,
                request.form.get("phone") or None,
                request.form.get("address") or None,
            ),
        )
        db.commit()
        return redirect(url_for("views.list_customers"))
    return render_template("views/create-customer.html")


@bp.route("/list-customers")
def list_customers():
    customers = get_db().execute("SELECT * FROM customers ORDER BY id").fetchall()
    return render_template("views/list-customers.html", customers=customers)


@bp.route("/edit-customer/<int:customer_id>", methods=("GET", "POST"))
def edit_customer(customer_id):
    db = get_db()
    if request.method == "POST":
        db.execute(
            "UPDATE customers SET name=%s, tax_id=%s, email=%s, phone=%s, address=%s "
            "WHERE id=%s",
            (
                request.form["name"],
                request.form.get("tax_id") or None,
                request.form.get("email") or None,
                request.form.get("phone") or None,
                request.form.get("address") or None,
                customer_id,
            ),
        )
        db.commit()
        return redirect(url_for("views.list_customers"))
    customer = db.execute(
        "SELECT * FROM customers WHERE id = %s", (customer_id,)
    ).fetchone()
    if customer is None:
        abort(404)
    return render_template("views/edit-customer.html", customer=customer)


@bp.route("/delete-customer/<int:customer_id>", methods=("GET", "POST"))
def delete_customer(customer_id):
    db = get_db()
    db.execute("DELETE FROM customers WHERE id = %s", (customer_id,))
    db.commit()
    return redirect(url_for("views.list_customers"))


# ---------- Cashier (purchases) ----------

@bp.route("/create-purchase", methods=("GET", "POST"))
def create_purchase():
    db = get_db()
    if request.method == "POST":
        product = db.execute(
            "SELECT * FROM products WHERE id = %s", (request.form["product_id"],)
        ).fetchone()
        if product is None:
            abort(404)
        quantity = int(request.form["quantity"])
        if product["stock"] < quantity:
            flash("Estoque insuficiente.")
            return redirect(url_for("views.create_purchase"))
        unit_price = product["price"]
        total = unit_price * quantity
        db.execute(
            "INSERT INTO purchases "
            "(customer_id, product_id, quantity, unit_price, total, payment_method) "
            "VALUES (%s, %s, %s, %s, %s, %s)",
            (
                request.form["customer_id"],
                request.form["product_id"],
                quantity,
                unit_price,
                total,
                request.form["payment_method"],
            ),
        )
        db.execute(
            "UPDATE products SET stock = stock - %s WHERE id = %s",
            (quantity, request.form["product_id"]),
        )
        db.commit()
        flash("Compra registrada com sucesso!")
        return redirect(url_for("views.list_purchases"))
    customers = db.execute("SELECT * FROM customers ORDER BY name").fetchall()
    products = db.execute("SELECT * FROM products WHERE stock > 0 ORDER BY name").fetchall()
    return render_template(
        "views/create-purchase.html", customers=customers, products=products
    )


@bp.route("/list-purchases")
def list_purchases():
    purchases = get_db().execute(
        """
        SELECT purchases.*,
               customers.name AS customer_name,
               products.name  AS product_name
        FROM purchases
        JOIN customers ON customers.id = purchases.customer_id
        JOIN products  ON products.id  = purchases.product_id
        ORDER BY purchases.created_at DESC
        """
    ).fetchall()
    return render_template("views/list-purchases.html", purchases=purchases)


# ---------- Receipts ----------

@bp.route("/create-receipt", methods=("GET", "POST"))
def create_receipt():
    db = get_db()
    if request.method == "POST":
        try:
            db.execute(
                "INSERT INTO receipts (purchase_id, number, issue_date, notes) "
                "VALUES (%s, %s, %s, %s)",
                (
                    request.form["purchase_id"],
                    request.form["number"],
                    request.form["issue_date"],
                    request.form.get("notes") or None,
                ),
            )
            db.commit()
        except psycopg.IntegrityError:
            db.rollback()
            flash(f"Nota fiscal {request.form['number']} já existe.")
            return redirect(url_for("views.create_receipt"))
        flash("Nota fiscal emitida com sucesso!")
        return redirect(url_for("views.list_receipts"))
    purchases = db.execute(
        """
        SELECT purchases.*, customers.name AS customer_name
        FROM purchases
        JOIN customers ON customers.id = purchases.customer_id
        WHERE purchases.id NOT IN (SELECT purchase_id FROM receipts)
        ORDER BY purchases.created_at DESC
        """
    ).fetchall()
    return render_template("views/create-receipt.html", purchases=purchases)


@bp.route("/list-receipts")
def list_receipts():
    receipts = get_db().execute(
        """
        SELECT receipts.*,
               customers.name AS customer_name,
               purchases.total
        FROM receipts
        JOIN purchases ON purchases.id = receipts.purchase_id
        JOIN customers ON customers.id = purchases.customer_id
        ORDER BY receipts.issue_date DESC, receipts.id DESC
        """
    ).fetchall()
    return render_template("views/list-receipts.html", receipts=receipts)


@bp.route("/view-receipt/<int:receipt_id>")
def view_receipt(receipt_id):
    row = get_db().execute(
        """
        SELECT r.number, r.issue_date, r.notes,
               p.quantity, p.unit_price, p.total, p.payment_method,
               c.name AS customer_name, c.tax_id AS customer_tax_id,
               pr.name AS product_name
        FROM receipts r
        JOIN purchases p  ON p.id  = r.purchase_id
        JOIN customers c  ON c.id  = p.customer_id
        JOIN products  pr ON pr.id = p.product_id
        WHERE r.id = %s
        """,
        (receipt_id,),
    ).fetchone()
    if row is None:
        abort(404)
    receipt = {
        "number": row["number"],
        "issue_date": row["issue_date"],
        "customer_name": row["customer_name"],
        "customer_tax_id": row["customer_tax_id"],
        "total": row["total"],
        "payment_method": row["payment_method"],
        "notes": row["notes"],
        "items": [
            {
                "product_name": row["product_name"],
                "quantity": row["quantity"],
                "unit_price": row["unit_price"],
                "subtotal": row["total"],
            }
        ],
    }
    return render_template("views/view-receipt.html", receipt=receipt)


# ponytail: small helper to keep the edit-customer branch honest