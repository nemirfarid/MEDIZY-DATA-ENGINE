import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

# We check for corruption patterns like @, aayd@, mSH@, etc.
c.execute("SELECT id, nom FROM facilities WHERE nom LIKE '%@%' OR nom LIKE '%?%' OR nom LIKE '%Ã%' OR nom LIKE '%©%' OR nom LIKE '%â%'")
corrupt = c.fetchall()
print(f"Names with encoding or transliteration artifacts: {len(corrupt)}")
for row in corrupt[:15]:
    print("  ", row)

conn.close()

