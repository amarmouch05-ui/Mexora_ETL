"""
main.py — Pipeline ETL Mexora
Au lancement, un menu te demande où charger les données :
  1 → SQLite  (fichier mexora_dwh.db — aucune config requise)
  2 → PostgreSQL (DBeaver — nécessite la base mexora_dwh créée)
  3 → Les deux en même temps
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from datetime import datetime
from utils.logger import logger

from extract.extractor import (
    extract_commandes, extract_clients,
    extract_produits, extract_regions, extract_livreurs,
)
from transform.clean_commandes  import transform_commandes
from transform.clean_clients    import transform_clients, calculer_segments
from transform.clean_produits   import transform_produits
from transform.build_dimensions import (
    build_dim_temps, build_dim_produit, build_dim_client,
    build_dim_region, build_dim_livreur, build_fait_ventes,
)


# ── Menu ──────────────────────────────────────────────────────
def choisir_destination() -> str:
    print()
    print("=" * 55)
    print("   PIPELINE ETL MEXORA — Choix de destination")
    print("=" * 55)
    print()
    print("  1  →  SQLite       (fichier local mexora_dwh.db)")
    print("  2  →  PostgreSQL   (DBeaver)")
    print("  3  →  Les deux en même temps")
    print()
    while True:
        choix = input("  Ton choix [1/2/3] : ").strip()
        if choix in ("1", "2", "3"):
            return choix
        print("  Saisis 1, 2 ou 3.")


# ── Test connexion PostgreSQL ────────────────────────────────
def verifier_postgres(url: str) -> bool:
    try:
        import sqlalchemy
        engine = sqlalchemy.create_engine(url)
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        print("  [OK] Connexion PostgreSQL réussie\n")
        return True
    except Exception as e:
        print(f"  [ERREUR] Connexion PostgreSQL impossible :")
        print(f"           {e}")
        print()
        print("  Vérifie dans config/settings.py :")
        print("    PG_USER, PG_PASSWORD, PG_HOST, PG_PORT, PG_DBNAME")
        print("  Et que la base mexora_dwh existe dans DBeaver.")
        return False


# ── Phase Extract + Transform (commune aux deux cibles) ───────
def extraire_et_transformer():
    logger.info("--- PHASE EXTRACT ---")
    df_cmd_raw  = extract_commandes()
    df_cli_raw  = extract_clients()
    df_prod_raw = extract_produits()
    df_regions  = extract_regions()
    df_livreurs = extract_livreurs()

    logger.info("--- PHASE TRANSFORM ---")
    df_cmd      = transform_commandes(df_cmd_raw, df_regions)
    df_cli      = transform_clients(df_cli_raw, df_regions)
    df_prod     = transform_produits(df_prod_raw)
    df_segments = calculer_segments(df_cmd)

    logger.info("--- PHASE BUILD DIMENSIONS ---")
    dim_temps   = build_dim_temps("2020-01-01", "2025-12-31")
    dim_produit = build_dim_produit(df_prod)
    dim_client  = build_dim_client(df_cli, df_segments)
    dim_region  = build_dim_region(df_regions)
    dim_livreur = build_dim_livreur(df_livreurs)
    fait_ventes = build_fait_ventes(
        df_cmd, dim_temps, dim_client,
        dim_produit, dim_region, dim_livreur,
    )

    return dim_temps, dim_produit, dim_client, dim_region, dim_livreur, fait_ventes


# ── Phase Load vers une cible ────────────────────────────────
def charger_vers(db_url: str, label: str,
                 dim_temps, dim_produit, dim_client,
                 dim_region, dim_livreur, fait_ventes):
    """
    Charge les DataFrames déjà construits vers la cible choisie.
    db_url est injecté ici — pas de reload de module.
    """
    import sqlalchemy

    engine = sqlalchemy.create_engine(db_url)
    schema = "dwh_mexora" if engine.dialect.name == "postgresql" else None

    def _load(df, table_name):
        df.to_sql(
            name=table_name,
            schema=schema,
            con=engine,
            if_exists="replace",
            index=False,
            method="multi",
            chunksize=1000,
        )
        logger.info(f"[LOAD → {label}] {table_name:<20} : {len(df):>6} lignes")

    def _load_faits(df, table_name="fait_ventes"):
        total = 0
        for i in range(0, len(df), 5000):
            chunk = df.iloc[i:i + 5000]
            mode  = "replace" if i == 0 else "append"
            chunk.to_sql(
                name=table_name,
                schema=schema,
                con=engine,
                if_exists=mode,
                index=False,
                method="multi",
            )
            total += len(chunk)
        logger.info(f"[LOAD → {label}] {'fait_ventes':<20} : {total:>6} lignes")

    logger.info(f"--- PHASE LOAD → {label} ---")
    _load(dim_temps,   "dim_temps")
    _load(dim_produit, "dim_produit")
    _load(dim_client,  "dim_client")
    _load(dim_region,  "dim_region")
    _load(dim_livreur, "dim_livreur")
    _load_faits(fait_ventes)


# ── Résumé final ─────────────────────────────────────────────
def afficher_resume(label, dim_temps, dim_produit, dim_client,
                    dim_region, dim_livreur, fait_ventes, duree):
    logger.info("=" * 55)
    logger.info(f"  TERMINÉ EN {duree}s → {label}")
    logger.info(f"  dim_temps    : {len(dim_temps):>6} lignes")
    logger.info(f"  dim_produit  : {len(dim_produit):>6} lignes")
    logger.info(f"  dim_client   : {len(dim_client):>6} lignes")
    logger.info(f"  dim_region   : {len(dim_region):>6} lignes")
    logger.info(f"  dim_livreur  : {len(dim_livreur):>6} lignes")
    logger.info(f"  fait_ventes  : {len(fait_ventes):>6} lignes")
    logger.info("=" * 55)


# ── Point d'entrée ────────────────────────────────────────────
if __name__ == "__main__":
    import config.settings as settings

    choix = choisir_destination()
    start = datetime.now()

    # ── Extract + Transform (fait une seule fois même pour option 3)
    dims = extraire_et_transformer()
    dim_temps, dim_produit, dim_client, dim_region, dim_livreur, fait_ventes = dims

    duree = lambda: (datetime.now() - start).seconds

    if choix == "1":
        print(f"\n  Destination : SQLite → mexora_dwh.db\n")
        charger_vers(settings.SQLITE_URL, "SQLite", *dims)
        afficher_resume("SQLite", *dims, duree())

    elif choix == "2":
        print(f"\n  Destination : PostgreSQL ({settings.PG_HOST}/{settings.PG_DBNAME})\n")
        if verifier_postgres(settings.POSTGRES_URL):
            charger_vers(settings.POSTGRES_URL, "PostgreSQL", *dims)
            afficher_resume("PostgreSQL", *dims, duree())

    elif choix == "3":
        print(f"\n  Destination : SQLite + PostgreSQL\n")

        print("  ── Chargement SQLite ──────────────────────────")
        charger_vers(settings.SQLITE_URL, "SQLite", *dims)

        print()
        print("  ── Chargement PostgreSQL ──────────────────────")
        if verifier_postgres(settings.POSTGRES_URL):
            charger_vers(settings.POSTGRES_URL, "PostgreSQL", *dims)

        afficher_resume("SQLite + PostgreSQL", *dims, duree())

    print()
