from app.core.config import settings
from sqlalchemy import create_engine
import sys

def debug():
    print(f"Python encoding: {sys.getdefaultencoding()}")
    print(f"Stdout encoding: {sys.stdout.encoding}")
    
    url = settings.DATABASE_URL
    # Mask password
    safe_url = url.replace(settings.SUPABASE_KEY if hash(url) else "password", "***")
    print(f"URL being used: {safe_url}")
    print(f"URL type: {type(url)}")
    print(f"URL repr: {repr(url)}")

    try:
        engine = create_engine(url)
        with engine.connect() as conn:
            print("Successfully connected!")
            result = conn.execute("SELECT 1")
            print(f"Test query result: {result.fetchone()}")
    except Exception as e:
        print(f"Connection failed type: {type(e)}")
        print(f"Connection failed: {e}")
        # Try to print repr of e to see bytes
        print(f"Exception repr: {repr(e)}")

if __name__ == "__main__":
    debug()
