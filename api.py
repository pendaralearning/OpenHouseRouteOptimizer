from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List
import sqlite3
from fastapi.middleware.cors import CORSMiddleware
import os

app = FastAPI()

# Allow CORS so the Chrome Extension can make requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production, fine for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "redfin_favorites.db"

class AddressList(BaseModel):
    addresses: List[str] = Field(..., description="List of scraped addresses")

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS addresses
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, address TEXT UNIQUE)''')
    conn.commit()
    conn.close()

init_db()

@app.post("/add_addresses")
async def add_addresses(data: AddressList):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    added_count = 0
    for addr in data.addresses:
        try:
            c.execute("INSERT OR IGNORE INTO addresses (address) VALUES (?)", (addr,))
            if c.rowcount > 0:
                added_count += 1
        except Exception as e:
            print(f"Error inserting {addr}: {e}")
    conn.commit()
    conn.close()
    return {"status": "success", "message": f"Added {added_count} addresses"}

@app.get("/get_addresses")
async def get_addresses():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT address FROM addresses")
    addresses = [row[0] for row in c.fetchall()]
    conn.close()
    return {"addresses": addresses}

@app.post("/clear_addresses")
async def clear_addresses():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM addresses")
    conn.commit()
    conn.close()
    return {"status": "success", "message": "All addresses cleared"}
