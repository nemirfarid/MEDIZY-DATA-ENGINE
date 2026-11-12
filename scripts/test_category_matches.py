import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

queries = [
    'généraliste', 'dentiste', 'pédiatre', 'pharmacie', 'clinique',
    'laboratoire', 'cardiologue', 'imagerie', 'ophtalmologue',
    'gynécologue', 'dermatologue', 'chirurgie orthopédique',
    'gastro-entérologie', 'pneumologie', 'clinique orl',
    'psychiatrie', 'urgences', 'kinésithérapie'
]

# Check how many results each query yields with current appendCategoryClause logic
for q in queries:
    c.execute(f"SELECT count(1) FROM facilities WHERE lower(categorie) LIKE '%{q}%' OR lower(nom) LIKE '%{q}%'")
    res = c.fetchone()[0]
    print(f"Slug: '{q}' -> matches: {res}")

conn.close()

