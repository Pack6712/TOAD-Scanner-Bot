import sqlite3


DB_FILE = "scam.db"


def get_columns(cursor, table_name):
    cursor.execute(f"PRAGMA table_info({table_name})")
    return [row[1] for row in cursor.fetchall()]


con = sqlite3.connect(DB_FILE)
cur = con.cursor()

try:
    print("🐸 TOAD Scanner 2.0 — миграция базы\n")

    # 1. Таблица досье
    cur.execute("""
        CREATE TABLE IF NOT EXISTS scam_entities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            primary_username VARCHAR(100),
            display_name VARCHAR(255),
            status VARCHAR(30) DEFAULT 'active',
            risk_score INTEGER DEFAULT 0,
            created_at DATETIME,
            updated_at DATETIME
        )
    """)

    print("✅ Таблица scam_entities готова")

    # 2. Таблица идентификаторов
    cur.execute("""
        CREATE TABLE IF NOT EXISTS entity_identifiers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id INTEGER NOT NULL,
            identifier_type VARCHAR(50) NOT NULL,
            value_masked VARCHAR(255) NOT NULL,
            value_hash VARCHAR(64) NOT NULL,
            label VARCHAR(100),
            created_at DATETIME,

            FOREIGN KEY(entity_id)
                REFERENCES scam_entities(id)
        )
    """)

    print("✅ Таблица entity_identifiers готова")

    # 3. Индексы
    cur.execute("""
        CREATE INDEX IF NOT EXISTS
        ix_entity_identifiers_entity_id
        ON entity_identifiers(entity_id)
    """)

    cur.execute("""
        CREATE INDEX IF NOT EXISTS
        ix_entity_identifiers_value_hash
        ON entity_identifiers(value_hash)
    """)

    print("✅ Индексы идентификаторов готовы")

    # 4. Добавляем entity_id в scam_reports
    report_columns = get_columns(
        cur,
        "scam_reports"
    )

    if "entity_id" not in report_columns:
        cur.execute("""
            ALTER TABLE scam_reports
            ADD COLUMN entity_id INTEGER
            REFERENCES scam_entities(id)
        """)

        print("✅ Колонка entity_id добавлена в scam_reports")

    else:
        print("ℹ️ Колонка entity_id уже существует")

    # 5. Индекс для entity_id
    cur.execute("""
        CREATE INDEX IF NOT EXISTS
        ix_scam_reports_entity_id
        ON scam_reports(entity_id)
    """)

    con.commit()

    print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print("✅ МИГРАЦИЯ TOAD SCANNER 2.0 ЗАВЕРШЕНА")
    print("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

    print("\nТаблицы:")

    cur.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table'
        ORDER BY name
    """)

    for row in cur.fetchall():
        print(" •", row[0])

    print("\nКолонки scam_reports:")

    for column in get_columns(
        cur,
        "scam_reports"
    ):
        print(" •", column)

except Exception as error:
    con.rollback()

    print("\n❌ ОШИБКА МИГРАЦИИ:")
    print(repr(error))

finally:
    con.close()