import sqlite3

conn = sqlite3.connect('assets/data/sante_dz_bundled.db')
c = conn.cursor()

def test_cat(name, condition):
    c.execute(f"SELECT count(1) FROM facilities WHERE {condition}")
    print(f"Category [{name}]: {c.fetchone()[0]} facilities")

test_cat("Généraliste", "lower(categorie) LIKE '%generalist%' OR lower(categorie) LIKE '%généralist%' OR lower(categorie) = 'medecin' OR lower(categorie) LIKE '%cabinet medical%' OR lower(categorie) LIKE '%médecin%' OR lower(nom) LIKE '%généraliste%'")
test_cat("Dentiste", "lower(categorie) LIKE '%dentist%' OR lower(categorie) LIKE '%dentaire%' OR lower(nom) LIKE '%dentist%' OR lower(nom) LIKE '%dentaire%'")
test_cat("Pédiatre", "lower(categorie) LIKE '%pediatr%' OR lower(categorie) LIKE '%pédiatr%' OR lower(nom) LIKE '%pediatr%' OR lower(nom) LIKE '%pédiatr%' OR lower(nom) LIKE '%enfants%'")
test_cat("Pharmacie", "lower(categorie) LIKE '%pharmac%' OR lower(nom) LIKE '%pharmac%' OR lower(categorie) LIKE '%officine%'")
test_cat("Clinique / Hôpital", "lower(categorie) LIKE '%clinique%' OR lower(categorie) LIKE '%hopital%' OR lower(categorie) LIKE '%hôpital%' OR lower(categorie) LIKE '%chu%' OR lower(categorie) LIKE '%eph%' OR lower(nom) LIKE '%clinique%' OR lower(nom) LIKE '%hopital%' OR lower(nom) LIKE '%hôpital%'")
test_cat("Laboratoire", "lower(categorie) LIKE '%laboratoire%' OR lower(categorie) LIKE '%analyse%' OR lower(nom) LIKE '%laboratoire%' OR lower(nom) LIKE '%analyse%'")
test_cat("Cardiologue", "lower(categorie) LIKE '%cardio%' OR lower(nom) LIKE '%cardio%'")
test_cat("Imagerie / Radio", "lower(categorie) LIKE '%imagerie%' OR lower(categorie) LIKE '%radio%' OR lower(categorie) LIKE '%scanner%' OR lower(categorie) LIKE '%irm%' OR lower(nom) LIKE '%imagerie%' OR lower(nom) LIKE '%radio%'")
test_cat("Ophtalmologue", "lower(categorie) LIKE '%ophtalm%' OR lower(nom) LIKE '%ophtalm%' OR lower(categorie) LIKE '%opticien%'")
test_cat("Gynécologue", "lower(categorie) LIKE '%gyneco%' OR lower(categorie) LIKE '%gynéco%' OR lower(categorie) LIKE '%maternite%' OR lower(categorie) LIKE '%maternité%' OR lower(nom) LIKE '%gyneco%' OR lower(nom) LIKE '%gynéco%'")
test_cat("Dermatologue", "lower(categorie) LIKE '%dermat%' OR lower(nom) LIKE '%dermat%'")
test_cat("Orthopédiste", "lower(categorie) LIKE '%orthoped%' OR lower(categorie) LIKE '%orthopéd%' OR lower(nom) LIKE '%orthoped%' OR lower(nom) LIKE '%orthopéd%'")
test_cat("Gastro-entérologue", "lower(categorie) LIKE '%gastro%' OR lower(nom) LIKE '%gastro%'")
test_cat("Pneumologue", "lower(categorie) LIKE '%pneumo%' OR lower(nom) LIKE '%pneumo%'")
test_cat("ORL", "lower(categorie) LIKE '%orl%' OR lower(categorie) LIKE '%rhino%' OR lower(nom) LIKE '%orl%' OR lower(nom) LIKE '%oto-rhino%'")
test_cat("Psychiatrie / Psychologue", "lower(categorie) LIKE '%psych%' OR lower(nom) LIKE '%psych%'")
test_cat("Paramédical / Kiné", "lower(categorie) LIKE '%kine%' OR lower(categorie) LIKE '%kiné%' OR lower(categorie) LIKE '%paramed%' OR lower(categorie) LIKE '%paraméd%' OR lower(categorie) LIKE '%physio%' OR lower(categorie) LIKE '%orthophon%' OR lower(nom) LIKE '%kine%' OR lower(nom) LIKE '%kiné%'")
test_cat("Urgences 24/7", "lower(categorie) LIKE '%urgence%' OR lower(nom) LIKE '%urgence%' OR lower(nom) LIKE '%garde%' OR lower(nom) LIKE '%24/24%' OR lower(categorie) LIKE '%chu%' OR lower(categorie) LIKE '%eph%'")

conn.close()

