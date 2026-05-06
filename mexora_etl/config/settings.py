import os

# ── Chemins des fichiers sources ──────────────────────────────
BASE_DIR  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR  = os.path.join(BASE_DIR, "data")
LOGS_DIR  = os.path.join(BASE_DIR, "logs")

COMMANDES_PATH = os.path.join(DATA_DIR, "commandes_mexora.csv")
CLIENTS_PATH   = os.path.join(DATA_DIR, "clients_mexora.csv")
PRODUITS_PATH  = os.path.join(DATA_DIR, "produits_mexora.json")
REGIONS_PATH   = os.path.join(DATA_DIR, "regions_maroc.csv")
LIVREURS_PATH  = os.path.join(DATA_DIR, "livreurs_mexora.csv")

# ── URLs de connexion ─────────────────────────────────────────
SQLITE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'mexora_dwh.db')}"

# Modifie uniquement ces 3 valeurs avec tes infos DBeaver
PG_USER     = "postgres"
PG_PASSWORD = "root"
PG_HOST     = "localhost"
PG_PORT     = "5432"
PG_DBNAME   = "mexora_dwh"

POSTGRES_URL = f"postgresql://{PG_USER}:{PG_PASSWORD}@{PG_HOST}:{PG_PORT}/{PG_DBNAME}"

# ── Schéma PostgreSQL ─────────────────────────────────────────
DWH_SCHEMA = "dwh_mexora"

# ── Règles métier ─────────────────────────────────────────────
SEGMENT_GOLD       = 15000
SEGMENT_SILVER     = 5000
AGE_MIN            = 16
AGE_MAX            = 100
SEUIL_RETARD_JOURS = 3

# ── DB_URL dynamique (défini par main.py au lancement) ────────
DB_URL = None
