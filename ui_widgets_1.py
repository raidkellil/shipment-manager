#!/usr/bin/env python3
"""
UI Widgets Module 1 - Shipments and Products (Hardened)
Handles shipments and products interface components with added security
Created by: Maou Houssem Eddine
Improvements: error handling, input validation, duplicate prevention,
safe date/decimal parsing, logging, numeric alignment, role checks.
"""

import logging
import traceback
from datetime import datetime
from decimal import Decimal, InvalidOperation

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QMessageBox, QHeaderView, QInputDialog
)
from PyQt6.QtCore import Qt

# ---------------------------
# Logging configuration
# ---------------------------
# Simple file logger. In a larger app consider RotatingFileHandler.
logging.basicConfig(
    filename='app_ui_widgets.log',
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger("ui_widgets_1")

# ---------------------------
# Helper utilities
# ---------------------------

MAX_INPUT_LENGTH = 200  # limit for user input strings
CURRENCY_LABEL = "DA"


def safe_decimal(value, default=Decimal("0.00")):
    """Safely convert a value to Decimal rounded to 2 decimal places."""
    try:
        # If value is already Decimal, str() will keep precision
        d = Decimal(str(value))
        return d.quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError) as e:
        logger.warning("safe_decimal conversion failed for value=%r: %s", value, e)
        return default


def safe_date_format(iso_str, fmt="%d/%m/%Y %H:%M", default="Unknown"):
    """Convert ISO datetime string to formatted string safely."""
    if not iso_str:
        return default
    try:
        # Accept both "YYYY-MM-DD HH:MM:SS" and ISO "T" formats
        # datetime.fromisoformat accepts both "YYYY-MM-DDTHH:MM:SS" and "YYYY-MM-DD HH:MM:SS"
        dt = datetime.fromisoformat(str(iso_str))
        return dt.strftime(fmt)
    except Exception as e:
        logger.warning("safe_date_format failed for %r: %s", iso_str, e)
        return "Invalid Date"


def show_db_error(parent, heading, exc):
    """Show DB error to user (non-sensitive) and log full traceback."""
    msg = f"{heading}.\nSee log for details."
    QMessageBox.critical(parent, "Database Error", msg)
    logger.error("%s\n%s", heading, traceback.format_exc())


# ---------------------------
# Widgets
# ---------------------------

class ShipmentsWidget(QWidget):
    """Shipments management widget (hardened)"""

    def __init__(self, db, current_user=None):
        """
        db: an object exposing execute_query(query, params=()) -> list[dict]
                         and execute_update(query, params=()) -> last_row_id/None
        current_user: optional dict e.g. {'username': 'admin', 'role': 'admin'}
        """
        super().__init__()
        self.db = db
        self.current_user = current_user or {'username': 'guest', 'role': 'viewer'}
        self.init_ui()
        self.load_shipments()

    def init_ui(self):
        """Initialize shipments UI"""
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Shipments</h2>"))
        header_layout.addStretch()

        self.add_button = QPushButton("Add New Shipment")
        self.add_button.clicked.connect(self.add_shipment)
        header_layout.addWidget(self.add_button)

        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date", "Products", "Customers", f"Total Paid ({CURRENCY_LABEL})"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _safe_query(self, query, params=()):
        """Execute a query safely and return results or [] on failure."""
        try:
            return self.db.execute_query(query, params) if params else self.db.execute_query(query)
        except Exception as e:
            logger.exception("DB query failed: %s | params=%r", query, params)
            return []

    def load_shipments(self):
        """Load shipments from database with error handling"""
        query = '''
            SELECT s.id, s.created_at, s.notes,
                   COUNT(DISTINCT sp.product_id) as product_count,
                   COUNT(DISTINCT fp.farmer_id) as farmer_count,
                   COALESCE(SUM(fp.total_paid), 0) as total_paid
            FROM shipments s
            LEFT JOIN shipment_products sp ON s.id = sp.shipment_id
            LEFT JOIN farmer_purchases fp ON s.id = fp.shipment_id
            GROUP BY s.id
            ORDER BY s.created_at DESC
        '''
        try:
            shipments = self._safe_query(query) or []
        except Exception as e:
            show_db_error(self, "Failed to load shipments", e)
            shipments = []

        # defensive: ensure it's a list
        if not isinstance(shipments, (list, tuple)):
            logger.error("load_shipments expected list, got %s", type(shipments))
            shipments = []

        self.table.setRowCount(len(shipments))

        for row, shipment in enumerate(shipments):
            try:
                # defensive get with defaults
                shipment_id = shipment.get('id', 'N/A')
                created_at = shipment.get('created_at', None)
                product_count = shipment.get('product_count', 0) or 0
                farmer_count = shipment.get('farmer_count', 0) or 0
                total_paid_raw = shipment.get('total_paid', 0) or 0

                # ID
                item_id = QTableWidgetItem(str(shipment_id))
                item_id.setFlags(item_id.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, item_id)

                # Date
                date_str = safe_date_format(created_at, fmt="%d/%m/%Y %H:%M", default="Unknown")
                item_date = QTableWidgetItem(date_str)
                item_date.setFlags(item_date.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 1, item_date)

                # Product count
                item_prod = QTableWidgetItem(f"{int(product_count)} products")
                item_prod.setFlags(item_prod.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, item_prod)

                # Farmer count
                item_farmer = QTableWidgetItem(f"{int(farmer_count)} farmers")
                item_farmer.setFlags(item_farmer.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, item_farmer)

                # Total paid (numeric alignment, safe decimal)
                total_paid = safe_decimal(total_paid_raw)
                item_paid = QTableWidgetItem(f"{total_paid:,.2f} {CURRENCY_LABEL}")
                item_paid.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_paid.setFlags(item_paid.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 4, item_paid)

            except Exception:
                logger.exception("Failed to render shipment row: %s", shipment)
                # show placeholder in row to keep table consistent
                self.table.setItem(row, 0, QTableWidgetItem("Error"))
                continue

    def add_shipment(self):
        """Open dialog to add new shipment (requires proper role)"""
        role = self.current_user.get('role', 'viewer')
        if role not in ('admin', 'manager'):
            QMessageBox.warning(self, "Permission Denied", "You do not have permission to add shipments.")
            logger.warning("User %s attempted to add shipment without permission", self.current_user.get('username'))
            return

        # For simplicity, this is a placeholder dialog. In a full app connect AddShipmentDialog.
        reply = QMessageBox.question(
            self, "Create Shipment", "Open shipment creation dialog now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            # In a real flow you'd open AddShipmentDialog here
            QMessageBox.information(self, "Add Shipment", "Shipment creation dialog would open here")
            logger.info("User %s initiated shipment creation", self.current_user.get('username'))


class ProductsWidget(QWidget):
    """Products management widget (hardened)"""

    def __init__(self, db, current_user=None):
        super().__init__()
        self.db = db
        self.current_user = current_user or {'username': 'guest', 'role': 'viewer'}
        self.init_ui()
        self.load_products()

    def init_ui(self):
        """Initialize products UI"""
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Products</h2>"))
        header_layout.addStretch()

        self.add_button = QPushButton("Add Product")
        self.add_button.clicked.connect(self.add_product)
        header_layout.addWidget(self.add_button)

        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Name", "Date Added", "Total Bought", "Total Cost", "Current Stock"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)

        layout.addWidget(self.table)
        self.setLayout(layout)

    def _safe_query(self, query, params=()):
        """Execute a query safely and return results or [] on failure."""
        try:
            return self.db.execute_query(query, params) if params else self.db.execute_query(query)
        except Exception:
            logger.exception("DB query failed: %s | params=%r", query, params)
            return []

    def load_products(self):
        """Load products from database with statistics and robust handling"""
        query = '''
            SELECT p.id, p.name, p.created_at,
                   COALESCE(SUM(sp.quantity), 0) as total_bought,
                   COALESCE(SUM(sp.subtotal), 0) as total_cost,
                   COALESCE(SUM(sp.quantity), 0) - 
                   COALESCE(SUM(fp.quantity), 0) - 
                   COALESCE(SUM(r.quantity), 0) as current_stock
            FROM products p
            LEFT JOIN shipment_products sp ON p.id = sp.product_id
            LEFT JOIN farmer_purchases fp ON p.id = fp.product_id
            LEFT JOIN returns r ON p.id = r.product_id
            GROUP BY p.id
            ORDER BY p.name
        '''
        try:
            products = self._safe_query(query) or []
        except Exception as e:
            show_db_error(self, "Failed to load products", e)
            products = []

        if not isinstance(products, (list, tuple)):
            logger.error("load_products expected list, got %s", type(products))
            products = []

        self.table.setRowCount(len(products))

        for row, product in enumerate(products):
            try:
                name = product.get('name', 'Unnamed') if isinstance(product, dict) else str(product)
                created_at = product.get('created_at', None)
                total_bought_raw = product.get('total_bought', 0) or 0
                total_cost_raw = product.get('total_cost', 0) or 0
                current_stock_raw = product.get('current_stock', 0) or 0

                item_name = QTableWidgetItem(str(name))
                item_name.setFlags(item_name.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 0, item_name)

                date_str = safe_date_format(created_at, fmt="%d/%m/%Y", default="Unknown")
                item_date = QTableWidgetItem(date_str)
                item_date.setFlags(item_date.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 1, item_date)

                total_bought = safe_decimal(total_bought_raw)
                item_bought = QTableWidgetItem(f"{total_bought:,.2f}")
                item_bought.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_bought.setFlags(item_bought.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 2, item_bought)

                total_cost = safe_decimal(total_cost_raw)
                item_cost = QTableWidgetItem(f"{total_cost:,.2f} {CURRENCY_LABEL}")
                item_cost.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_cost.setFlags(item_cost.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 3, item_cost)

                current_stock = safe_decimal(current_stock_raw)
                item_stock = QTableWidgetItem(f"{current_stock:,.2f}")
                item_stock.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                item_stock.setFlags(item_stock.flags() ^ Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(row, 4, item_stock)

            except Exception:
                logger.exception("Failed to render product row: %s", product)
                # fallback placeholders
                self.table.setItem(row, 0, QTableWidgetItem("Error"))
                continue

    def _product_exists(self, name):
        """Check whether a product name already exists (case-insensitive)."""
        try:
            # Parameterized query - prevents SQL injection
            result = self.db.execute_query(
                "SELECT id FROM products WHERE LOWER(name) = LOWER(?) LIMIT 1", (name.strip(),)
            )
            return bool(result)
        except Exception:
            logger.exception("Failed checking product existence for name=%r", name)
            # Conservatively say it exists to avoid duplicate insert on DB uncertainty
            return True

    def add_product(self):
        """Add new product with validation, duplicate check and role enforcement."""
        role = self.current_user.get('role', 'viewer')
        if role not in ('admin', 'manager'):
            QMessageBox.warning(self, "Permission Denied", "You do not have permission to add products.")
            logger.warning("User %s attempted to add product without permission", self.current_user.get('username'))
            return

        name, ok = QInputDialog.getText(self, "Add Product", "Enter product name:")
        # Validate dialog response and input sanitization
        if not ok:
            logger.debug("Add product cancelled by user %s", self.current_user.get('username'))
            return

        if not name or not isinstance(name, str) or not name.strip():
            QMessageBox.warning(self, "Invalid Input", "Product name cannot be empty.")
            logger.info("User provided empty product name: %r", name)
            return

        # sanitize and limit length
        name_clean = name.strip()
        if len(name_clean) > MAX_INPUT_LENGTH:
            QMessageBox.warning(self, "Invalid Input", f"Product name too long (max {MAX_INPUT_LENGTH} chars).")
            logger.info("Product name too long (%d): %s", len(name_clean), name_clean[:50])
            return

        # Prevent duplicates (case-insensitive)
        if self._product_exists(name_clean):
            QMessageBox.warning(self, "Duplicate", "This product already exists.")
            logger.info("Duplicate product prevented: %s by user %s", name_clean, self.current_user.get('username'))
            return

        # Confirm insertion
        confirm = QMessageBox.question(
            self, "Confirm Add", f"Are you sure you want to add product: '{name_clean}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if confirm != QMessageBox.StandardButton.Yes:
            logger.debug("User cancelled adding product: %s", name_clean)
            return

        try:
            # Parameterized insert to prevent SQL injection
            self.db.execute_update('INSERT INTO products (name) VALUES (?)', (name_clean,))
            logger.info("Product added: %s by user %s", name_clean, self.current_user.get('username'))
            self.load_products()
            QMessageBox.information(self, "Success", "Product added successfully")
        except Exception as e:
            logger.exception("Failed to insert product %s: %s", name_clean, e)
            QMessageBox.warning(self, "Error", f"Failed to add product: operation failed.")
