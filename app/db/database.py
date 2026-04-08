import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'saas.db')

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            api_key TEXT UNIQUE NOT NULL,
            monthly_quota INTEGER NOT NULL,
            used_quota INTEGER DEFAULT 0
        )
    ''')
    
    # Create the default demo client if not exists
    c.execute('SELECT COUNT(*) FROM clients WHERE api_key = "DEMO-SITE-KEY-12345"')
    if c.fetchone()[0] == 0:
        c.execute('''
            INSERT INTO clients (company_name, api_key, monthly_quota)
            VALUES ("ReviewLens Demo Site", "DEMO-SITE-KEY-12345", 99999)
        ''')
    
    conn.commit()
    conn.close()

def authenticate_and_charge(api_key: str, review_count: int) -> dict:
    """Verifies API key and deducts quota. Returns client dictionary if successful."""
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    c.execute('SELECT * FROM clients WHERE api_key = ?', (api_key,))
    client = c.fetchone()
    
    if not client:
        conn.close()
        return None
        
    client_dict = dict(client)
    remaining = client_dict['monthly_quota'] - client_dict['used_quota']
    
    if remaining < review_count:
        conn.close()
        raise ValueError(f"Quota Exceeded. Required: {review_count}, Remaining: {remaining}")
        
    # Deduct quota
    c.execute('UPDATE clients SET used_quota = used_quota + ? WHERE api_key = ?', (review_count, api_key))
    conn.commit()
    conn.close()
    
    return client_dict
