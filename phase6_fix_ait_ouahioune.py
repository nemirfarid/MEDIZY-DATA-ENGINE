"""Set approximate GPS for Ait Ouahioune."""
import sqlite3, sys
sys.stdout.reconfigure(encoding='utf-8')

conn = sqlite3.connect(r'C:\SANTE_DZ_SCRAPER\medizy_scraper.db')
c = conn.cursor()

# Ait Ouahioune is in Tizi Ouzou wilaya - use approximate coordinates near Tizi Ouzou
c.execute(
    'UPDATE places SET latitude = 36.6816, longitude = 4.2372, commune = ?, commune_source = ?, commune_confidence = ?, commune_updated_at = ? WHERE id = 77898',
    ('Ait Ouahioune', 'MIPH_2025_approximation', 0.3, '2026-10-10 20:33:00'))
conn.commit()

c.execute('SELECT COUNT(*), COUNT(CASE WHEN latitude IS NOT NULL THEN 1 END) FROM places')
total, with_gps = c.fetchone()
print(f'Final: Total={total}, With GPS={with_gps}')

c.execute('SELECT id, nom, latitude, longitude FROM places WHERE latitude IS NULL OR longitude IS NULL')
remaining = c.fetchall()
print(f'Still missing GPS: {len(remaining)}')
for r in remaining:
    print(f'  {r}')

# Also check MIPH_2025 entries
c.execute('SELECT COUNT(*) FROM places WHERE source = ?', ('MIPH_2025',))
print(f'MIPH_2025 entries: {c.fetchone()[0]}')

conn.close()
