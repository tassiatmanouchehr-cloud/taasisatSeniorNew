import psycopg

conn = psycopg.connect("postgresql://postgres:123456@localhost:5432/postgres")
conn.autocommit = True
cur = conn.cursor()

try:
    cur.execute("CREATE USER marketplace WITH PASSWORD 'marketplace'")
    print("Created user marketplace")
except Exception as e:
    print(f"User creation: {e}")

try:
    cur.execute("CREATE DATABASE marketplace OWNER marketplace")
    print("Created database marketplace")
except Exception as e:
    print(f"Database creation: {e}")

try:
    cur.execute("GRANT ALL PRIVILEGES ON DATABASE marketplace TO marketplace")
    print("Granted privileges")
except Exception as e:
    print(f"Grant: {e}")

conn.close()
print("Done")
