from .connection import MongoConn
from datetime import date

async def ensure_connected(conn: MongoConn):
    """
    Checks if the connection is alive and tries to reconnect if it isn't
    
    Args:
        conn (MongoConn): Active connection to the mongo database
        
    Raises:
        Exception: If re-connection failed
    """
    if not await conn.is_connection_alive():
        print("[DB] Connection lost, attempting to reconnect...")
        await conn.connect()

def check_valid_date_range(start_date, end_date):
    """
    Checks if the given dates are valid and build a valid time range
    
    Args:
        conn (MongoConn): Active connection to the mongo database
        
    Raises:
        TypeError: If input isn't proper datetime.date
        ValueError: If end_date isn't after start_date
    """

    # Check that both are instances of datetime.date
    if not isinstance(start_date, date) or not isinstance(end_date, date):
        raise TypeError("start_date and end_date must be datetime.date instances")

    # Ensure start_date is not after end_date
    if start_date > end_date:
        raise ValueError("start_date cannot be after end_date")

    return True