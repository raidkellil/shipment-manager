#!/usr/bin/env python3
"""
Shipment Management System
A comprehensive wholesale/retail shipment management system with PyQt6 GUI
"""

import sys
import os
import sqlite3
import hashlib
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from decimal import Decimal, ROUND_HALF_UP

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLineEdit, QLabel,
    QDialog, QDialogButtonBox, QComboBox, QSpinBox, QDoubleSpinBox,
    QTextEdit, QSplitter, QFrame, QMessageBox, QHeaderView, QStyle,
    QStyleFactory, QMenuBar, QMenu, QStatusBar, QToolBar, QCheckBox,
    QGroupBox, QFormLayout, QScrollArea, QFileDialog,
    QTextBrowser, QTabWidget
)
from PyQt6.QtPrintSupport import QPrintDialog, QPrinter
from PyQt6.QtCore import Qt, QDateTime, pyqtSignal, QTimer
from PyQt6.QtGui import QAction, QIcon, QFont, QPalette, QColor, QKeySequence


class Database:
    """Database management class with SQLite"""
    
    def __init__(self, db_path: str = "shipments.db"):
        self.db_path = db_path
        self.init_database()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection with foreign keys enabled"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """Initialize database with all tables"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Create all tables
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS farmers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shipments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    notes TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shipment_products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shipment_id INTEGER REFERENCES shipments(id) ON DELETE CASCADE,
                    product_id INTEGER REFERENCES products(id),
                    unit_price REAL NOT NULL,
                    quantity INTEGER NOT NULL,
                    subtotal REAL
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS farmer_purchases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    shipment_id INTEGER REFERENCES shipments(id) ON DELETE CASCADE,
                    farmer_id INTEGER REFERENCES farmers(id),
                    product_id INTEGER REFERENCES products(id),
                    quantity REAL NOT NULL,
                    unit_price REAL NOT NULL,
                    total_paid REAL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS transfers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    from_farmer_id INTEGER REFERENCES farmers(id),
                    to_farmer_id INTEGER REFERENCES farmers(id),
                    product_id INTEGER REFERENCES products(id),
                    quantity REAL NOT NULL,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS returns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    farmer_id INTEGER REFERENCES farmers(id),
                    product_id INTEGER REFERENCES products(id),
                    quantity REAL NOT NULL,
                    refund_amount REAL,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL
                )
            ''')
            
            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shipment_products_shipment_id ON shipment_products(shipment_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_farmer_purchases_shipment_id ON farmer_purchases(shipment_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_farmer_purchases_farmer_id ON farmer_purchases(farmer_id)')
            
            # Insert default admin user if not exists
            password_hash = hashlib.sha256("password123".encode()).hexdigest()
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password_hash)
                VALUES (?, ?)
            ''', ('admin', password_hash))
            
            # Insert seed data if database is empty
            cursor.execute('SELECT COUNT(*) FROM products')
            if cursor.fetchone()[0] == 0:
                # Seed products
                products = ['Tomato', 'Potato', 'Onion']
                for product in products:
                    cursor.execute('INSERT INTO products (name) VALUES (?)', (product,))
                
                # Seed farmers
                farmers = ['Farmer A', 'Farmer B', 'Farmer C']
                for farmer in farmers:
                    cursor.execute('INSERT INTO farmers (name) VALUES (?)', (farmer,))
                
                # Create sample shipment
                cursor.execute('INSERT INTO shipments (notes) VALUES (?)', ('Sample shipment',))
                shipment_id = cursor.lastrowid
                
                # Add sample products to shipment
                cursor.execute('''
                    INSERT INTO shipment_products (shipment_id, product_id, unit_price, quantity, subtotal)
                    VALUES (?, 1, 50.00, 100, 5000.00)
                ''', (shipment_id,))
                
                # Add sample farmer purchase
                cursor.execute('''
                    INSERT INTO farmer_purchases (shipment_id, farmer_id, product_id, quantity, unit_price, total_paid)
                    VALUES (?, 1, 1, 50, 65.00, 3250.00)
                ''', (shipment_id,))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logging.error(f"Database initialization error: {e}")
            raise
    
    def execute_query(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        results = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return results
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE query and return last row ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        last_row_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return last_row_id


class LoginDialog(QDialog):
    """Login dialog for user authentication"""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize login UI"""
        self.setWindowTitle("Login - Shipment Management System")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        
        # Title
        title = QLabel("Shipment Management System")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        # Username
        username_layout = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        username_layout.addRow("Username:", self.username_input)
        layout.addLayout(username_layout)
        
        # Password
        password_layout = QFormLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password")
        password_layout.addRow("Password:", self.password_input)
        layout.addLayout(password_layout)
        
        layout.addSpacing(20)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
        # Set focus to username
        self.username_input.setFocus()
    
    def accept(self):
        """Validate login credentials"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return
        
        # Verify credentials
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        results = self.db.execute_query(
            'SELECT id FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        
        if results:
            super().accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid username or password")
            logging.warning(f"Failed login attempt for username: {username}")


class ShipmentsWidget(QWidget):
    """Shipments management widget"""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_shipments()
    
    def init_ui(self):
        """Initialize shipments UI"""
        layout = QVBoxLayout()
        
        # Header with add button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Shipments</h2>"))
        header_layout.addStretch()
        
        self.add_button = QPushButton("Add New Shipment")
        self.add_button.clicked.connect(self.add_shipment)
        header_layout.addWidget(self.add_button)
        
        layout.addLayout(header_layout)
        
        # Shipments table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "ID", "Date", "Products", "Customers", "Total Paid (DA)"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.view_shipment)
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def load_shipments(self):
        """Load shipments from database"""
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
        
        shipments = self.db.execute_query(query)
        
        self.table.setRowCount(len(shipments))
        for row, shipment in enumerate(shipments):
            # ID
            self.table.setItem(row, 0, QTableWidgetItem(str(shipment['id'])))
            
            # Date
            date_obj = datetime.fromisoformat(shipment['created_at'])
            date_str = date_obj.strftime("%d/%m/%Y %H:%M")
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            
            # Products
            self.table.setItem(row, 2, QTableWidgetItem(f"{shipment['product_count']} products"))
            
            # Customers
            self.table.setItem(row, 3, QTableWidgetItem(f"{shipment['farmer_count']} farmers"))
            
            # Total Paid
            total_paid = Decimal(str(shipment['total_paid'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 4, QTableWidgetItem(f"{total_paid:,.2f} DA"))
    
    def add_shipment(self):
        """Open dialog to add new shipment"""
        dialog = AddShipmentDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_shipments()
    
    def view_shipment(self):
        """View shipment details"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            shipment_id = int(self.table.item(current_row, 0).text())
            dialog = ShipmentDetailsDialog(self.db, shipment_id, self)
            dialog.exec()


class ProductsWidget(QWidget):
    """Products management widget"""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_products()
    
    def init_ui(self):
        """Initialize products UI"""
        layout = QVBoxLayout()
        
        # Header with add button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Products</h2>"))
        header_layout.addStretch()
        
        self.add_button = QPushButton("Add Product")
        self.add_button.clicked.connect(self.add_product)
        header_layout.addWidget(self.add_button)
        
        layout.addLayout(header_layout)
        
        # Products table
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            "Name", "Date Added", "Total Bought", "Total Cost", "Current Stock"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.view_product)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def load_products(self):
        """Load products from database with statistics"""
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
        
        products = self.db.execute_query(query)
        
        self.table.setRowCount(len(products))
        for row, product in enumerate(products):
            # Name
            self.table.setItem(row, 0, QTableWidgetItem(product['name']))
            
            # Date Added
            date_obj = datetime.fromisoformat(product['created_at'])
            date_str = date_obj.strftime("%d/%m/%Y")
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            
            # Total Bought
            total_bought = Decimal(str(product['total_bought'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 2, QTableWidgetItem(f"{total_bought:,.2f}"))
            
            # Total Cost
            total_cost = Decimal(str(product['total_cost'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 3, QTableWidgetItem(f"{total_cost:,.2f} DA"))
            
            # Current Stock
            current_stock = Decimal(str(product['current_stock'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 4, QTableWidgetItem(f"{current_stock:,.2f}"))
    
    def add_product(self):
        """Add new product"""
        name, ok = self.get_text_input("Add Product", "Enter product name:")
        if ok and name:
            try:
                self.db.execute_update('INSERT INTO products (name) VALUES (?)', (name,))
                self.load_products()
                QMessageBox.information(self, "Success", "Product added successfully")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add product: {e}")
    
    def view_product(self):
        """View product details"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            product_name = self.table.item(current_row, 0).text()
            QMessageBox.information(self, "Product Details", f"Details for: {product_name}")
    
    def get_text_input(self, title: str, label: str) -> tuple[str, bool]:
        """Utility method to get text input from user"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, title, label)
        return text, ok


class FarmersWidget(QWidget):
    """Farmers management widget"""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_farmers()
    
    def init_ui(self):
        """Initialize farmers UI"""
        layout = QVBoxLayout()
        
        # Header with add button
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Farmers</h2>"))
        header_layout.addStretch()
        
        # Add buttons for transfers and returns
        self.add_farmer_btn = QPushButton("Add Farmer")
        self.add_farmer_btn.clicked.connect(self.add_farmer)
        header_layout.addWidget(self.add_farmer_btn)
        
        self.transfer_btn = QPushButton("Transfer Products")
        self.transfer_btn.clicked.connect(self.transfer_products)
        header_layout.addWidget(self.transfer_btn)
        
        self.return_btn = QPushButton("Record Return")
        self.return_btn.clicked.connect(self.record_return)
        header_layout.addWidget(self.return_btn)
        
        layout.addLayout(header_layout)
        
        # Farmers table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Name", "Date Added", "Total Bought (DA)"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.doubleClicked.connect(self.view_farmer)
        
        layout.addWidget(self.table)
        self.setLayout(layout)
    
    def load_farmers(self):
        """Load farmers from database with statistics"""
        query = '''
            SELECT f.id, f.name, f.created_at,
                   COALESCE(SUM(fp.total_paid), 0) as total_bought
            FROM farmers f
            LEFT JOIN farmer_purchases fp ON f.id = fp.farmer_id
            GROUP BY f.id
            ORDER BY f.name
        '''
        
        farmers = self.db.execute_query(query)
        
        self.table.setRowCount(len(farmers))
        for row, farmer in enumerate(farmers):
            # Name
            self.table.setItem(row, 0, QTableWidgetItem(farmer['name']))
            
            # Date Added
            date_obj = datetime.fromisoformat(farmer['created_at'])
            date_str = date_obj.strftime("%d/%m/%Y")
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            
            # Total Bought
            total_bought = Decimal(str(farmer['total_bought'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 2, QTableWidgetItem(f"{total_bought:,.2f} DA"))
    
    def add_farmer(self):
        """Add new farmer"""
        name, ok = self.get_text_input("Add Farmer", "Enter farmer name:")
        if ok and name:
            try:
                self.db.execute_update('INSERT INTO farmers (name) VALUES (?)', (name,))
                self.load_farmers()
                QMessageBox.information(self, "Success", "Farmer added successfully")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add farmer: {e}")
    
    def transfer_products(self):
        """Transfer products between farmers"""
        dialog = TransferDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_farmers()
    
    def record_return(self):
        """Record product return from farmer"""
        dialog = ReturnDialog(self.db, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.load_farmers()
    
    def view_farmer(self):
        """View farmer details"""
        current_row = self.table.currentRow()
        if current_row >= 0:
            farmer_name = self.table.item(current_row, 0).text()
            QMessageBox.information(self, "Farmer Details", f"Details for: {farmer_name}")
    
    def get_text_input(self, title: str, label: str) -> tuple[str, bool]:
        """Utility method to get text input from user"""
        from PyQt6.QtWidgets import QInputDialog
        text, ok = QInputDialog.getText(self, title, label)
        return text, ok


class TransferDialog(QDialog):
    """Dialog to transfer products between farmers"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize transfer UI"""
        self.setWindowTitle("Transfer Products")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Transfer form
        form_layout = QFormLayout()
        
        # From farmer
        self.from_farmer_combo = QComboBox()
        farmers = self.db.execute_query('SELECT id, name FROM farmers ORDER BY name')
        for farmer in farmers:
            self.from_farmer_combo.addItem(farmer['name'], farmer['id'])
        form_layout.addRow("From Farmer:", self.from_farmer_combo)
        
        # To farmer
        self.to_farmer_combo = QComboBox()
        for farmer in farmers:
            self.to_farmer_combo.addItem(farmer['name'], farmer['id'])
        form_layout.addRow("To Farmer:", self.to_farmer_combo)
        
        # Product
        self.product_combo = QComboBox()
        products = self.db.execute_query('SELECT id, name FROM products ORDER BY name')
        for product in products:
            self.product_combo.addItem(product['name'], product['id'])
        form_layout.addRow("Product:", self.product_combo)
        
        # Quantity
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 10000)
        form_layout.addRow("Quantity:", self.quantity_spin)
        
        # Note
        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(60)
        form_layout.addRow("Note:", self.note_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.transfer_products)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def transfer_products(self):
        """Execute product transfer"""
        from_farmer_id = self.from_farmer_combo.currentData()
        to_farmer_id = self.to_farmer_combo.currentData()
        product_id = self.product_combo.currentData()
        quantity = self.quantity_spin.value()
        note = self.note_input.toPlainText()
        
        if from_farmer_id == to_farmer_id:
            QMessageBox.warning(self, "Error", "Cannot transfer to the same farmer")
            return
        
        try:
            # Record transfer
            self.db.execute_update('''
                INSERT INTO transfers (from_farmer_id, to_farmer_id, product_id, quantity, note)
                VALUES (?, ?, ?, ?, ?)
            ''', (from_farmer_id, to_farmer_id, product_id, quantity, note))
            
            QMessageBox.information(self, "Success", "Transfer completed successfully")
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to complete transfer: {e}")


class ReturnDialog(QDialog):
    """Dialog to record product returns"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize return UI"""
        self.setWindowTitle("Record Product Return")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout()
        
        # Return form
        form_layout = QFormLayout()
        
        # Farmer
        self.farmer_combo = QComboBox()
        farmers = self.db.execute_query('SELECT id, name FROM farmers ORDER BY name')
        for farmer in farmers:
            self.farmer_combo.addItem(farmer['name'], farmer['id'])
        form_layout.addRow("Farmer:", self.farmer_combo)
        
        # Product
        self.product_combo = QComboBox()
        products = self.db.execute_query('SELECT id, name FROM products ORDER BY name')
        for product in products:
            self.product_combo.addItem(product['name'], product['id'])
        form_layout.addRow("Product:", self.product_combo)
        
        # Quantity
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 10000)
        form_layout.addRow("Quantity:", self.quantity_spin)
        
        # Refund amount
        self.refund_spin = QDoubleSpinBox()
        self.refund_spin.setRange(0, 10000)
        self.refund_spin.setPrefix("DA ")
        form_layout.addRow("Refund Amount:", self.refund_spin)
        
        # Note
        self.note_input = QTextEdit()
        self.note_input.setMaximumHeight(60)
        form_layout.addRow("Note:", self.note_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.record_return)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def record_return(self):
        """Record product return"""
        farmer_id = self.farmer_combo.currentData()
        product_id = self.product_combo.currentData()
        quantity = self.quantity_spin.value()
        refund_amount = self.refund_spin.value()
        note = self.note_input.toPlainText()
        
        try:
            # Record return
            self.db.execute_update('''
                INSERT INTO returns (farmer_id, product_id, quantity, refund_amount, note)
                VALUES (?, ?, ?, ?, ?)
            ''', (farmer_id, product_id, quantity, refund_amount, note))
            
            QMessageBox.information(self, "Success", "Return recorded successfully")
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to record return: {e}")


class ReceiptsWidget(QWidget):
    """Receipts management widget"""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize receipts UI"""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Receipts</h2>"))
        
        # Receipt types
        receipt_group = QGroupBox("Generate Receipts")
        receipt_layout = QVBoxLayout()
        
        self.factory_receipt_btn = QPushButton("Factory Purchase Receipt")
        self.factory_receipt_btn.clicked.connect(self.generate_factory_receipt)
        receipt_layout.addWidget(self.factory_receipt_btn)
        
        self.farmer_receipt_btn = QPushButton("Farmer Sale Receipt")
        self.farmer_receipt_btn.clicked.connect(self.generate_farmer_receipt)
        receipt_layout.addWidget(self.farmer_receipt_btn)
        
        self.shipment_receipt_btn = QPushButton("Shipment Receipt")
        self.shipment_receipt_btn.clicked.connect(self.generate_shipment_receipt)
        receipt_layout.addWidget(self.shipment_receipt_btn)
        
        receipt_group.setLayout(receipt_layout)
        layout.addWidget(receipt_group)
        
        # Receipt preview
        self.receipt_preview = QTextBrowser()
        layout.addWidget(self.receipt_preview)
        
        self.setLayout(layout)
    
    def generate_factory_receipt(self):
        """Generate factory purchase receipt"""
        html = self.create_receipt_html("FACTORY PURCHASE RECEIPT", "blue")
        self.receipt_preview.setHtml(html)
    
    def generate_farmer_receipt(self):
        """Generate farmer sale receipt"""
        html = self.create_receipt_html("FARMER SALE RECEIPT", "green")
        self.receipt_preview.setHtml(html)
    
    def generate_shipment_receipt(self):
        """Generate shipment receipt"""
        html = self.create_receipt_html("SHIPMENT RECEIPT", "orange")
        self.receipt_preview.setHtml(html)
    
    def create_receipt_html(self, title: str, color: str) -> str:
        """Create HTML receipt template"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .title {{ font-size: 24px; font-weight: bold; color: {color}; }}
                .date {{ font-size: 12px; color: #666; }}
                .items {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .items th, .items td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .items th {{ background-color: #f2f2f2; }}
                .total {{ font-weight: bold; font-size: 16px; text-align: right; margin-top: 20px; }}
                .footer {{ margin-top: 40px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">{title}</div>
                <div class="date">Generated: {current_time}</div>
            </div>
            
            <table class="items">
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Subtotal</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td>Sample Product</td>
                        <td>100</td>
                        <td>DA 50.00</td>
                        <td>DA 5,000.00</td>
                    </tr>
                </tbody>
            </table>
            
            <div class="total">
                Total: DA 5,000.00
            </div>
            
            <div class="footer">
                Thank you for your business!<br>
                Shipment Management System
            </div>
        </body>
        </html>
        """
        return html


class ManageWidget(QWidget):
    """Stock management widget"""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_stock()
    
    def init_ui(self):
        """Initialize manage UI"""
        layout = QVBoxLayout()
        layout.addWidget(QLabel("<h2>Stock Management</h2>"))
        
        # Stock table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels([
            "Product", "Total Bought", "Total Sold", "Current Stock"
        ])
        
        layout.addWidget(self.table)
        
        # Direct sale section
        sale_group = QGroupBox("Direct Warehouse Sale")
        sale_layout = QFormLayout()
        
        self.farmer_combo = QComboBox()
        self.product_combo = QComboBox()
        self.quantity_spin = QDoubleSpinBox()
        self.quantity_spin.setRange(0.01, 10000)
        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0.01, 10000)
        
        sale_layout.addRow("Farmer:", self.farmer_combo)
        sale_layout.addRow("Product:", self.product_combo)
        sale_layout.addRow("Quantity:", self.quantity_spin)
        sale_layout.addRow("Unit Price:", self.price_spin)
        
        self.sell_button = QPushButton("Sell")
        self.sell_button.clicked.connect(self.direct_sell)
        sale_layout.addRow(self.sell_button)
        
        sale_group.setLayout(sale_layout)
        layout.addWidget(sale_group)
        
        self.setLayout(layout)
        
        # Load combo boxes
        self.load_combos()
    
    def load_combos(self):
        """Load farmers and products into combo boxes"""
        # Load farmers
        farmers = self.db.execute_query('SELECT id, name FROM farmers ORDER BY name')
        self.farmer_combo.clear()
        for farmer in farmers:
            self.farmer_combo.addItem(farmer['name'], farmer['id'])
        
        # Load products
        products = self.db.execute_query('SELECT id, name FROM products ORDER BY name')
        self.product_combo.clear()
        for product in products:
            self.product_combo.addItem(product['name'], product['id'])
    
    def load_stock(self):
        """Load current stock for all products"""
        query = '''
            SELECT p.name,
                   COALESCE(SUM(sp.quantity), 0) as total_bought,
                   COALESCE(SUM(fp.quantity), 0) as total_sold,
                   COALESCE(SUM(sp.quantity), 0) - 
                   COALESCE(SUM(fp.quantity), 0) - 
                   COALESCE(SUM(r.quantity), 0) as current_stock
            FROM products p
            LEFT JOIN shipment_products sp ON p.id = sp.product_id
            LEFT JOIN farmer_purchases fp ON p.id = fp.product_id AND fp.shipment_id IS NOT NULL
            LEFT JOIN returns r ON p.id = r.product_id
            GROUP BY p.id
            ORDER BY p.name
        '''
        
        stock_data = self.db.execute_query(query)
        
        self.table.setRowCount(len(stock_data))
        for row, item in enumerate(stock_data):
            self.table.setItem(row, 0, QTableWidgetItem(item['name']))
            
            total_bought = Decimal(str(item['total_bought'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 1, QTableWidgetItem(f"{total_bought:,.2f}"))
            
            total_sold = Decimal(str(item['total_sold'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 2, QTableWidgetItem(f"{total_sold:,.2f}"))
            
            current_stock = Decimal(str(item['current_stock'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 3, QTableWidgetItem(f"{current_stock:,.2f}"))
    
    def direct_sell(self):
        """Perform direct warehouse sale"""
        farmer_id = self.farmer_combo.currentData()
        product_id = self.product_combo.currentData()
        quantity = self.quantity_spin.value()
        unit_price = self.price_spin.value()
        total_paid = quantity * unit_price
        
        if not farmer_id or not product_id:
            QMessageBox.warning(self, "Error", "Please select farmer and product")
            return
        
        try:
            # Create direct purchase (shipment_id = NULL)
            self.db.execute_update('''
                INSERT INTO farmer_purchases (farmer_id, product_id, quantity, unit_price, total_paid)
                VALUES (?, ?, ?, ?, ?)
            ''', (farmer_id, product_id, quantity, unit_price, total_paid))
            
            QMessageBox.information(self, "Success", "Direct sale completed successfully")
            self.load_stock()
            
            # Reset form
            self.quantity_spin.setValue(0)
            self.price_spin.setValue(0)
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to complete sale: {e}")


class AddShipmentDialog(QDialog):
    """Dialog to add new shipment with farmer distribution"""
    
    def __init__(self, db: Database, parent=None):
        super().__init__(parent)
        self.db = db
        self.products = []
        self.farmer_purchases = []
        self.current_product_idx = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize add shipment UI with farmer distribution"""
        self.setWindowTitle("Add New Shipment")
        self.setModal(True)
        self.resize(1000, 800)
        
        layout = QVBoxLayout()
        
        # Shipment notes
        notes_layout = QFormLayout()
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        notes_layout.addRow("Notes:", self.notes_input)
        layout.addLayout(notes_layout)
        
        # Products section
        layout.addWidget(QLabel("<h3>Add Products to Shipment</h3>"))
        
        # Add product form
        product_form = QHBoxLayout()
        
        self.product_combo = QComboBox()
        products = self.db.execute_query('SELECT id, name FROM products ORDER BY name')
        for product in products:
            self.product_combo.addItem(product['name'], product['id'])
        
        self.unit_price_spin = QDoubleSpinBox()
        self.unit_price_spin.setRange(0.01, 10000)
        self.unit_price_spin.setPrefix("DA ")
        
        self.quantity_spin = QSpinBox()
        self.quantity_spin.setRange(1, 10000)
        
        self.add_product_btn = QPushButton("Add Product")
        self.add_product_btn.clicked.connect(self.add_product_to_shipment)
        
        product_form.addWidget(QLabel("Product:"))
        product_form.addWidget(self.product_combo)
        product_form.addWidget(QLabel("Unit Price:"))
        product_form.addWidget(self.unit_price_spin)
        product_form.addWidget(QLabel("Quantity:"))
        product_form.addWidget(self.quantity_spin)
        product_form.addWidget(self.add_product_btn)
        
        layout.addLayout(product_form)
        
        # Products table
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels([
            "Product", "Unit Price", "Quantity", "Subtotal", "Farmers Assigned"
        ])
        self.products_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.products_table.clicked.connect(self.select_product_for_farmers)
        layout.addWidget(self.products_table)
        
        # Farmer distribution section
        layout.addWidget(QLabel("<h3>Distribute to Farmers</h3>"))
        
        # Farmer distribution form
        farmer_form = QHBoxLayout()
        
        self.farmer_combo = QComboBox()
        farmers = self.db.execute_query('SELECT id, name FROM farmers ORDER BY name')
        for farmer in farmers:
            self.farmer_combo.addItem(farmer['name'], farmer['id'])
        
        self.farmer_quantity_spin = QDoubleSpinBox()
        self.farmer_quantity_spin.setRange(0.01, 10000)
        
        self.selling_price_spin = QDoubleSpinBox()
        self.selling_price_spin.setRange(0.01, 10000)
        self.selling_price_spin.setPrefix("DA ")
        
        self.add_farmer_btn = QPushButton("Assign to Farmer")
        self.add_farmer_btn.clicked.connect(self.assign_to_farmer)
        
        farmer_form.addWidget(QLabel("Farmer:"))
        farmer_form.addWidget(self.farmer_combo)
        farmer_form.addWidget(QLabel("Quantity:"))
        farmer_form.addWidget(self.farmer_quantity_spin)
        farmer_form.addWidget(QLabel("Selling Price:"))
        farmer_form.addWidget(self.selling_price_spin)
        farmer_form.addWidget(self.add_farmer_btn)
        
        layout.addLayout(farmer_form)
        
        # Farmer assignments table
        self.farmers_table = QTableWidget()
        self.farmers_table.setColumnCount(5)
        self.farmers_table.setHorizontalHeaderLabels([
            "Product", "Farmer", "Quantity", "Unit Price", "Total Paid"
        ])
        layout.addWidget(self.farmers_table)
        
        # Totals
        totals_layout = QHBoxLayout()
        
        self.purchase_total_label = QLabel("Purchase Total: DA 0.00")
        self.purchase_total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.purchase_total_label.setFont(font)
        totals_layout.addWidget(self.purchase_total_label)
        
        self.sales_total_label = QLabel("Sales Total: DA 0.00")
        self.sales_total_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        self.sales_total_label.setFont(font)
        totals_layout.addWidget(self.sales_total_label)
        
        layout.addLayout(totals_layout)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.save_shipment)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def add_product_to_shipment(self):
        """Add product to shipment"""
        product_id = self.product_combo.currentData()
        product_name = self.product_combo.currentText()
        unit_price = self.unit_price_spin.value()
        quantity = self.quantity_spin.value()
        subtotal = unit_price * quantity
        
        # Check if product already added
        for product in self.products:
            if product['product_id'] == product_id:
                QMessageBox.warning(self, "Error", "Product already added to shipment")
                return
        
        # Add to products list
        self.products.append({
            'product_id': product_id,
            'name': product_name,
            'unit_price': unit_price,
            'quantity': quantity,
            'subtotal': subtotal,
            'farmers': []
        })
        
        # Update table
        self.update_products_table()
        
        # Reset form
        self.unit_price_spin.setValue(0)
        self.quantity_spin.setValue(1)
    
    def update_products_table(self):
        """Update products table display"""
        self.products_table.setRowCount(len(self.products))
        purchase_total = 0
        
        for row, product in enumerate(self.products):
            self.products_table.setItem(row, 0, QTableWidgetItem(product['name']))
            self.products_table.setItem(row, 1, QTableWidgetItem(f"DA {product['unit_price']:.2f}"))
            self.products_table.setItem(row, 2, QTableWidgetItem(str(product['quantity'])))
            self.products_table.setItem(row, 3, QTableWidgetItem(f"DA {product['subtotal']:.2f}"))
            
            # Show farmers assigned
            farmers_text = f"{len(product['farmers'])} farmers"
            self.products_table.setItem(row, 4, QTableWidgetItem(farmers_text))
            
            purchase_total += product['subtotal']
        
        self.purchase_total_label.setText(f"Purchase Total: DA {purchase_total:.2f}")
    
    def select_product_for_farmers(self):
        """Select product for farmer assignment"""
        current_row = self.products_table.currentRow()
        if current_row >= 0 and current_row < len(self.products):
            self.current_product_idx = current_row
            self.update_farmers_table()
    
    def assign_to_farmer(self):
        """Assign product to farmer"""
        if self.current_product_idx is None:
            QMessageBox.warning(self, "Error", "Please select a product first")
            return
        
        farmer_id = self.farmer_combo.currentData()
        farmer_name = self.farmer_combo.currentText()
        quantity = self.farmer_quantity_spin.value()
        selling_price = self.selling_price_spin.value()
        
        product = self.products[self.current_product_idx]
        
        # Check if farmer already assigned to this product
        for farmer in product['farmers']:
            if farmer['farmer_id'] == farmer_id:
                QMessageBox.warning(self, "Error", "Farmer already assigned to this product")
                return
        
        # Check if total quantity exceeds available
        total_assigned = sum(f['quantity'] for f in product['farmers'])
        if total_assigned + quantity > product['quantity']:
            remaining = product['quantity'] - total_assigned
            QMessageBox.warning(self, "Error", f"Only {remaining:.2f} units remaining for this product")
            return
        
        # Add farmer assignment
        total_paid = quantity * selling_price
        product['farmers'].append({
            'farmer_id': farmer_id,
            'farmer_name': farmer_name,
            'quantity': quantity,
            'unit_price': selling_price,
            'total_paid': total_paid
        })
        
        # Update tables
        self.update_farmers_table()
        self.update_products_table()
        self.update_sales_total()
        
        # Reset form
        self.farmer_quantity_spin.setValue(0)
        self.selling_price_spin.setValue(0)
    
    def update_farmers_table(self):
        """Update farmers assignment table"""
        self.farmers_table.setRowCount(0)
        
        if self.current_product_idx is None:
            return
        
        product = self.products[self.current_product_idx]
        
        for farmer in product['farmers']:
            row = self.farmers_table.rowCount()
            self.farmers_table.insertRow(row)
            
            self.farmers_table.setItem(row, 0, QTableWidgetItem(product['name']))
            self.farmers_table.setItem(row, 1, QTableWidgetItem(farmer['farmer_name']))
            self.farmers_table.setItem(row, 2, QTableWidgetItem(str(farmer['quantity'])))
            self.farmers_table.setItem(row, 3, QTableWidgetItem(f"DA {farmer['unit_price']:.2f}"))
            self.farmers_table.setItem(row, 4, QTableWidgetItem(f"DA {farmer['total_paid']:.2f}"))
    
    def update_sales_total(self):
        """Update sales total"""
        sales_total = 0
        for product in self.products:
            for farmer in product['farmers']:
                sales_total += farmer['total_paid']
        
        self.sales_total_label.setText(f"Sales Total: DA {sales_total:.2f}")
    
    def save_shipment(self):
        """Save shipment to database"""
        if not self.products:
            QMessageBox.warning(self, "Error", "Please add at least one product")
            return
        
        # Check if all products have farmer assignments
        for product in self.products:
            total_assigned = sum(f['quantity'] for f in product['farmers'])
            if total_assigned != product['quantity']:
                QMessageBox.warning(self, "Error", f"Product '{product['name']}' has {product['quantity'] - total_assigned:.2f} units not assigned to farmers")
                return
        
        try:
            # Create shipment
            notes = self.notes_input.toPlainText()
            shipment_id = self.db.execute_update(
                'INSERT INTO shipments (notes) VALUES (?)',
                (notes,)
            )
            
            # Add products to shipment
            for product in self.products:
                self.db.execute_update('''
                    INSERT INTO shipment_products (shipment_id, product_id, unit_price, quantity, subtotal)
                    VALUES (?, ?, ?, ?, ?)
                ''', (shipment_id, product['product_id'], product['unit_price'], 
                      product['quantity'], product['subtotal']))
                
                # Add farmer purchases
                for farmer in product['farmers']:
                    self.db.execute_update('''
                        INSERT INTO farmer_purchases (shipment_id, farmer_id, product_id, quantity, unit_price, total_paid)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (shipment_id, farmer['farmer_id'], product['product_id'],
                          farmer['quantity'], farmer['unit_price'], farmer['total_paid']))
            
            QMessageBox.information(self, "Success", f"Shipment #{shipment_id} saved successfully with farmer assignments")
            self.accept()
            
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save shipment: {e}")


class ShipmentDetailsDialog(QDialog):
    """Dialog to view shipment details"""
    
    def __init__(self, db: Database, shipment_id: int, parent=None):
        super().__init__(parent)
        self.db = db
        self.shipment_id = shipment_id
        self.init_ui()
        self.load_shipment_details()
    
    def init_ui(self):
        """Initialize shipment details UI"""
        self.setWindowTitle(f"Shipment #{self.shipment_id} Details")
        self.setModal(True)
        self.resize(800, 600)
        
        layout = QVBoxLayout()
        
        # Shipment info
        self.info_label = QLabel()
        layout.addWidget(self.info_label)
        
        # Products table
        layout.addWidget(QLabel("<h3>Products</h3>"))
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(4)
        self.products_table.setHorizontalHeaderLabels([
            "Product", "Unit Price", "Quantity", "Subtotal"
        ])
        layout.addWidget(self.products_table)
        
        # Receipt buttons
        receipt_layout = QHBoxLayout()
        
        self.factory_receipt_btn = QPushButton("Generate Factory Receipt")
        self.factory_receipt_btn.clicked.connect(self.generate_factory_receipt)
        receipt_layout.addWidget(self.factory_receipt_btn)
        
        self.farmer_receipts_btn = QPushButton("Generate Farmer Receipts")
        self.farmer_receipts_btn.clicked.connect(self.generate_farmer_receipts)
        receipt_layout.addWidget(self.farmer_receipts_btn)
        
        receipt_layout.addStretch()
        layout.addLayout(receipt_layout)
        
        # Close button
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def load_shipment_details(self):
        """Load shipment details from database"""
        # Get shipment info
        shipment = self.db.execute_query(
            'SELECT * FROM shipments WHERE id = ?',
            (self.shipment_id,)
        )[0]
        
        date_obj = datetime.fromisoformat(shipment['created_at'])
        date_str = date_obj.strftime("%d/%m/%Y %H:%M")
        
        self.info_label.setText(f"""
        <h3>Shipment #{shipment['id']}</h3>
        <p><strong>Date:</strong> {date_str}</p>
        <p><strong>Notes:</strong> {shipment['notes'] or 'None'}</p>
        """)
        
        # Get products
        products = self.db.execute_query('''
            SELECT p.name, sp.unit_price, sp.quantity, sp.subtotal
            FROM shipment_products sp
            JOIN products p ON sp.product_id = p.id
            WHERE sp.shipment_id = ?
        ''', (self.shipment_id,))
        
        self.products_table.setRowCount(len(products))
        for row, product in enumerate(products):
            self.products_table.setItem(row, 0, QTableWidgetItem(product['name']))
            self.products_table.setItem(row, 1, QTableWidgetItem(f"DA {product['unit_price']:.2f}"))
            self.products_table.setItem(row, 2, QTableWidgetItem(str(product['quantity'])))
            self.products_table.setItem(row, 3, QTableWidgetItem(f"DA {product['subtotal']:.2f}"))
    
    def generate_factory_receipt(self):
        """Generate factory receipt"""
        html = self.create_receipt_html("FACTORY PURCHASE RECEIPT", "blue")
        self.show_receipt_dialog(html)
    
    def generate_farmer_receipts(self):
        """Generate farmer receipts"""
        html = self.create_receipt_html("FARMER SALE RECEIPT", "green")
        self.show_receipt_dialog(html)
    
    def create_receipt_html(self, title: str, color: str) -> str:
        """Create HTML receipt"""
        current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        
        # Get shipment details
        shipment = self.db.execute_query(
            'SELECT * FROM shipments WHERE id = ?',
            (self.shipment_id,)
        )[0]
        
        date_obj = datetime.fromisoformat(shipment['created_at'])
        shipment_date = date_obj.strftime("%d/%m/%Y %H:%M")
        
        # Get products
        products = self.db.execute_query('''
            SELECT p.name, sp.unit_price, sp.quantity, sp.subtotal
            FROM shipment_products sp
            JOIN products p ON sp.product_id = p.id
            WHERE sp.shipment_id = ?
        ''', (self.shipment_id,))
        
        total = sum(p['subtotal'] for p in products)
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ text-align: center; margin-bottom: 30px; }}
                .title {{ font-size: 24px; font-weight: bold; color: {color}; }}
                .date {{ font-size: 12px; color: #666; }}
                .info {{ margin: 20px 0; }}
                .items {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                .items th, .items td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .items th {{ background-color: #f2f2f2; }}
                .total {{ font-weight: bold; font-size: 16px; text-align: right; margin-top: 20px; }}
                .footer {{ margin-top: 40px; font-size: 12px; color: #666; text-align: center; }}
            </style>
        </head>
        <body>
            <div class="header">
                <div class="title">{title}</div>
                <div class="date">Receipt #{self.shipment_id} - {current_time}</div>
            </div>
            
            <div class="info">
                <strong>Shipment Date:</strong> {shipment_date}<br>
                <strong>Notes:</strong> {shipment['notes'] or 'None'}
            </div>
            
            <table class="items">
                <thead>
                    <tr>
                        <th>Item</th>
                        <th>Quantity</th>
                        <th>Unit Price</th>
                        <th>Subtotal</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for product in products:
            html += f"""
                    <tr>
                        <td>{product['name']}</td>
                        <td>{product['quantity']}</td>
                        <td>DA {product['unit_price']:.2f}</td>
                        <td>DA {product['subtotal']:.2f}</td>
                    </tr>
            """
        
        html += f"""
                </tbody>
            </table>
            
            <div class="total">
                Total: DA {total:.2f}
            </div>
            
            <div class="footer">
                Thank you for your business!<br>
                Shipment Management System
            </div>
        </body>
        </html>
        """
        return html
    
    def show_receipt_dialog(self, html: str):
        """Show receipt in a dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Receipt")
        dialog.resize(600, 800)
        
        layout = QVBoxLayout()
        
        browser = QTextBrowser()
        browser.setHtml(html)
        layout.addWidget(browser)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        dialog.setLayout(layout)
        dialog.exec()


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, db: Database):
        super().__init__()
        self.db = db
        self.init_ui()
        self.show_shipments()
    
    def init_ui(self):
        """Initialize main window UI"""
        self.setWindowTitle("Shipment Management System")
        self.setGeometry(100, 100, 1200, 800)
        
        # Central widget with sidebar
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.Shape.Box)
        sidebar.setMaximumWidth(200)
        sidebar_layout = QVBoxLayout()
        
        # Sidebar buttons
        self.shipments_btn = QPushButton("Shipments")
        self.shipments_btn.clicked.connect(self.show_shipments)
        sidebar_layout.addWidget(self.shipments_btn)
        
        self.products_btn = QPushButton("Products")
        self.products_btn.clicked.connect(self.show_products)
        sidebar_layout.addWidget(self.products_btn)
        
        self.farmers_btn = QPushButton("Farmers")
        self.farmers_btn.clicked.connect(self.show_farmers)
        sidebar_layout.addWidget(self.farmers_btn)
        
        self.receipts_btn = QPushButton("Receipts")
        self.receipts_btn.clicked.connect(self.show_receipts)
        sidebar_layout.addWidget(self.receipts_btn)
        
        self.manage_btn = QPushButton("Manage")
        self.manage_btn.clicked.connect(self.show_manage)
        sidebar_layout.addWidget(self.manage_btn)
        
        sidebar_layout.addStretch()
        
        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self.logout)
        sidebar_layout.addWidget(self.logout_btn)
        
        sidebar.setLayout(sidebar_layout)
        main_layout.addWidget(sidebar)
        
        # Main content area
        self.content_area = QFrame()
        self.content_area.setFrameShape(QFrame.Shape.Box)
        self.content_layout = QVBoxLayout()
        self.content_area.setLayout(self.content_layout)
        
        main_layout.addWidget(self.content_area)
        
        # Menu bar
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("File")
        
        logout_action = QAction("Logout", self)
        logout_action.setShortcut(QKeySequence("Ctrl+L"))
        logout_action.triggered.connect(self.logout)
        file_menu.addAction(logout_action)
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu("Tools")
        
        new_shipment_action = QAction("New Shipment", self)
        new_shipment_action.setShortcut(QKeySequence("Ctrl+N"))
        new_shipment_action.triggered.connect(self.new_shipment)
        tools_menu.addAction(new_shipment_action)
        
        print_action = QAction("Print", self)
        print_action.setShortcut(QKeySequence("Ctrl+P"))
        print_action.triggered.connect(self.print_current)
        tools_menu.addAction(print_action)
        
        # Status bar
        self.statusBar().showMessage("Ready")
    
    def show_shipments(self):
        """Show shipments widget"""
        self.clear_content()
        self.shipments_widget = ShipmentsWidget(self.db)
        self.content_layout.addWidget(self.shipments_widget)
        self.statusBar().showMessage("Shipments")
    
    def show_products(self):
        """Show products widget"""
        self.clear_content()
        self.products_widget = ProductsWidget(self.db)
        self.content_layout.addWidget(self.products_widget)
        self.statusBar().showMessage("Products")
    
    def show_farmers(self):
        """Show farmers widget"""
        self.clear_content()
        self.farmers_widget = FarmersWidget(self.db)
        self.content_layout.addWidget(self.farmers_widget)
        self.statusBar().showMessage("Farmers")
    
    def show_receipts(self):
        """Show receipts widget"""
        self.clear_content()
        self.receipts_widget = ReceiptsWidget(self.db)
        self.content_layout.addWidget(self.receipts_widget)
        self.statusBar().showMessage("Receipts")
    
    def show_manage(self):
        """Show manage widget"""
        self.clear_content()
        self.manage_widget = ManageWidget(self.db)
        self.content_layout.addWidget(self.manage_widget)
        self.statusBar().showMessage("Stock Management")
    
    def clear_content(self):
        """Clear content area"""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def new_shipment(self):
        """Create new shipment"""
        if hasattr(self, 'shipments_widget'):
            self.shipments_widget.add_shipment()
    
    def print_current(self):
        """Print current view"""
        QMessageBox.information(self, "Print", "Print functionality would be implemented here")
    
    def logout(self):
        """Logout and return to login screen"""
        self.close()


def main():
    """Main application entry point"""
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('shipment_manager.log'),
            logging.StreamHandler()
        ]
    )
    
    # Create application
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    
    # Create database
    db = Database()
    
    # Show login dialog
    login = LoginDialog(db)
    if login.exec() == QDialog.DialogCode.Accepted:
        # Show main window
        window = MainWindow(db)
        window.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()