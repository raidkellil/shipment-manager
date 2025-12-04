#!/usr/bin/env python3
"""
Main Application Entry Point
Shipment Management System
Created by: Benbouzid Khireddine
"""

import sys
import logging
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QFrame, QStyleFactory
)
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QDialog

from database import Database
from ui_widgets_1 import ShipmentsWidget, ProductsWidget
from ui_widgets_2 import FarmersWidget, LoginDialog


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.show_shipments()
    
    def init_ui(self):
        """Initialize main window UI"""
        self.setWindowTitle("Shipment Management System")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Sidebar
        sidebar = QFrame()
        sidebar.setFrameShape(QFrame.Shape.Box)
        sidebar.setMaximumWidth(200)
        sidebar_layout = QVBoxLayout()
        
        self.shipments_btn = QPushButton("Shipments")
        self.shipments_btn.clicked.connect(self.show_shipments)
        sidebar_layout.addWidget(self.shipments_btn)
        
        self.products_btn = QPushButton("Products")
        self.products_btn.clicked.connect(self.show_products)
        sidebar_layout.addWidget(self.products_btn)
        
        self.farmers_btn = QPushButton("Farmers")
        self.farmers_btn.clicked.connect(self.show_farmers)
        sidebar_layout.addWidget(self.farmers_btn)
        
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
    
    def clear_content(self):
        """Clear content area"""
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
    
    def logout(self):
        """Logout and return to login screen"""
        self.close()


def main():
    """Main application entry point"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('shipment_manager.log'),
            logging.StreamHandler()
        ]
    )
    
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create("Fusion"))
    
    db = Database()
    
    login = LoginDialog(db)
    if login.exec() == QDialog.DialogCode.Accepted:
        window = MainWindow(db)
        window.showMaximized()
        sys.exit(app.exec())
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
