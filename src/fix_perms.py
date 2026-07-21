import psycopg

conn = psycopg.connect("postgresql://postgres:123456@localhost:5432/postgres")
conn.autocommit = True
cur = conn.cursor()

cur.execute("ALTER USER marketplace CREATEDB")
print("Granted CREATEDB to marketplace")

conn.close()
