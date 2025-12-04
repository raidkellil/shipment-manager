#!/usr/bin/env python3
"""
UI Widgets Module 1 - Shipments and Products
Handles shipments and products interface components
Created by: Maou Houssem Eddine
"""

from datetime import datetime
from decimal import Decimal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QDialog, QMessageBox, QHeaderView, QInputDialog
)
from PyQt6.QtCore import Qt


class ShipmentsWidget(QWidget):
    """Shipments management widget"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
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
            "ID", "Date", "Products", "Customers", "Total Paid (DA)"
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
            self.table.setItem(row, 0, QTableWidgetItem(str(shipment['id'])))
            
            date_obj = datetime.fromisoformat(shipment['created_at'])
            date_str = date_obj.strftime("%d/%m/%Y %H:%M")
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            
            self.table.setItem(row, 2, QTableWidgetItem(f"{shipment['product_count']} products"))
            self.table.setItem(row, 3, QTableWidgetItem(f"{shipment['farmer_count']} farmers"))
            
            total_paid = Decimal(str(shipment['total_paid'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 4, QTableWidgetItem(f"{total_paid:,.2f} DA"))
    
    def add_shipment(self):
        """Open dialog to add new shipment"""
        QMessageBox.information(self, "Add Shipment", "Shipment creation dialog would open here")


class ProductsWidget(QWidget):
    """Products management widget"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
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
            self.table.setItem(row, 0, QTableWidgetItem(product['name']))
            
            date_obj = datetime.fromisoformat(product['created_at'])
            date_str = date_obj.strftime("%d/%m/%Y")
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            
            total_bought = Decimal(str(product['total_bought'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 2, QTableWidgetItem(f"{total_bought:,.2f}"))
            
            total_cost = Decimal(str(product['total_cost'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 3, QTableWidgetItem(f"{total_cost:,.2f} DA"))
            
            current_stock = Decimal(str(product['current_stock'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 4, QTableWidgetItem(f"{current_stock:,.2f}"))
    
    def add_product(self):
        """Add new product"""
        name, ok = QInputDialog.getText(self, "Add Product", "Enter product name:")
        if ok and name:
            try:
                self.db.execute_update('INSERT INTO products (name) VALUES (?)', (name,))
                self.load_products()
                QMessageBox.information(self, "Success", "Product added successfully")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add product: {e}")
