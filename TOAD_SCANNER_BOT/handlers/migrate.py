import sqlite3


DB_FILE = "scam.db"

con = sqlite3.connect(DB_FILE)
cur = con.cursor()

cur.execute("PRAGMA table_info(scam_reports)")
columns = [row[1] for row in cur.fetchall()]

print("Колонки до миграции:")
print(columns)

if "reject_reason" not in columns:
    cur.execute(
        "ALTER TABLE scam_reports "
        "ADD COLUMN reject_reason TEXT"
    )

    con.commit()

    print("\n✅ Колонка reject_reason добавлена.")
else:
    print("\nℹ️ Колонка reject_reason уже существует.")

cur.execute("PRAGMA table_info(scam_reports)")
columns = [row[1] for row in cur.fetchall()]

print("\nКолонки после миграции:")
print(columns)

con.close()