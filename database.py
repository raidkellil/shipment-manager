#!/usr/bin/env python3
"""
Database module for Shipment Management System
Handles all SQLite database operations
Created by: [Person 1 Name]
"""

import sqlite3
import hashlib
import logging
from typing import List, Dict, Any


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
            
            # Create indexes
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_shipment_products_shipment_id ON shipment_products(shipment_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_farmer_purchases_shipment_id ON farmer_purchases(shipment_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_farmer_purchases_farmer_id ON farmer_purchases(farmer_id)')
            
            # Insert default admin user
            password_hash = hashlib.sha256("password123".encode()).hexdigest()
            cursor.execute('''
                INSERT OR IGNORE INTO users (username, password_hash)
                VALUES (?, ?)
            ''', ('admin', password_hash))
            
            # Insert seed data
            cursor.execute('SELECT COUNT(*) FROM products')
            if cursor.fetchone()[0] == 0:
                products = ['Tomato', 'Potato', 'Onion']
                for product in products:
                    cursor.execute('INSERT INTO products (name) VALUES (?)', (product,))
                
                farmers = ['Farmer A', 'Farmer B', 'Farmer C']
                for farmer in farmers:
                    cursor.execute('INSERT INTO farmers (name) VALUES (?)', (farmer,))
            
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
