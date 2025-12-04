#!/usr/bin/env python3
"""
UI Widgets Module 2 - Farmers and Dialogs
Handles farmers interface and dialog components
Created by: Beddiar Rajab
"""

from datetime import datetime
from decimal import Decimal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QLabel, QDialog, QMessageBox, QInputDialog
)


class FarmersWidget(QWidget):
    """Farmers management widget"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_farmers()
    
    def init_ui(self):
        """Initialize farmers UI"""
        layout = QVBoxLayout()
        
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("<h2>Farmers</h2>"))
        header_layout.addStretch()
        
        self.add_farmer_btn = QPushButton("Add Farmer")
        self.add_farmer_btn.clicked.connect(self.add_farmer)
        header_layout.addWidget(self.add_farmer_btn)
        
        layout.addLayout(header_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels([
            "Name", "Date Added", "Total Bought (DA)"
        ])
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
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
            self.table.setItem(row, 0, QTableWidgetItem(farmer['name']))
            
            date_obj = datetime.fromisoformat(farmer['created_at'])
            date_str = date_obj.strftime("%d/%m/%Y")
            self.table.setItem(row, 1, QTableWidgetItem(date_str))
            
            total_bought = Decimal(str(farmer['total_bought'])).quantize(Decimal('0.01'))
            self.table.setItem(row, 2, QTableWidgetItem(f"{total_bought:,.2f} DA"))
    
    def add_farmer(self):
        """Add new farmer"""
        name, ok = QInputDialog.getText(self, "Add Farmer", "Enter farmer name:")
        if ok and name:
            try:
                self.db.execute_update('INSERT INTO farmers (name) VALUES (?)', (name,))
                self.load_farmers()
                QMessageBox.information(self, "Success", "Farmer added successfully")
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Failed to add farmer: {e}")


class LoginDialog(QDialog):
    """Login dialog for user authentication"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
    
    def init_ui(self):
        """Initialize login UI"""
        from PyQt6.QtWidgets import QLineEdit, QFormLayout, QDialogButtonBox
        from PyQt6.QtGui import QFont
        from PyQt6.QtCore import Qt
        import hashlib
        
        self.setWindowTitle("Login - Shipment Management System")
        self.setFixedSize(400, 300)
        
        layout = QVBoxLayout()
        
        title = QLabel("Shipment Management System")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        layout.addSpacing(20)
        
        username_layout = QFormLayout()
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("Enter username")
        username_layout.addRow("Username:", self.username_input)
        layout.addLayout(username_layout)
        
        password_layout = QFormLayout()
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText("Enter password")
        password_layout.addRow("Password:", self.password_input)
        layout.addLayout(password_layout)
        
        layout.addSpacing(20)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.validate_login)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.username_input.setFocus()
    
    def validate_login(self):
        """Validate login credentials"""
        import hashlib
        
        username = self.username_input.text().strip()
        password = self.password_input.text()
        
        if not username or not password:
            QMessageBox.warning(self, "Error", "Please enter both username and password")
            return
        
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        results = self.db.execute_query(
            'SELECT id FROM users WHERE username = ? AND password_hash = ?',
            (username, password_hash)
        )
        
        if results:
            self.accept()
        else:
            QMessageBox.warning(self, "Error", "Invalid username or password")
