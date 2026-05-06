import pandas as pd
import sqlalchemy
from utils.logger import logger
import config.settings as settings


def _get_engine():
    return sqlalchemy.create_engine(settings.DB_URL)


def _detect_schema(engine) -> str:
    """Retourne dwh_mexora pour PostgreSQL, None pour SQLite."""
    return settings.DWH_SCHEMA if engine.dialect.name == "postgresql" else None


def _creer_schema_si_besoin(engine) -> None:
    """
    Crée le schéma dwh_mexora dans PostgreSQL s'il n'existe pas.
    Sans ça, pandas lève 'schema does not exist' avant même de créer la table.
    Ignoré silencieusement pour SQLite.
    """
    if engine.dialect.name != "postgresql":
        return
    with engine.connect() as conn:
        conn.execute(
            sqlalchemy.text(
                f"CREATE SCHEMA IF NOT EXISTS {settings.DWH_SCHEMA}"
            )
        )
        conn.commit()
    logger.info(f"[LOAD] Schéma '{settings.DWH_SCHEMA}' vérifié / créé")


def _chunk_size(engine) -> int:
    """
    SQLite : limite de 999 paramètres par requête.
    Avec 11 colonnes (fait_ventes) → max 999 // 11 = 90 lignes par chunk.
    On prend 50 pour avoir une marge.
    PostgreSQL : pas de limite stricte, on peut utiliser 1000.
    """
    return 1000 if engine.dialect.name == "postgresql" else 50


def charger_dimension(df: pd.DataFrame, table_name: str) -> None:
    """
    Charge une dimension en mode REPLACE.
    Compatible SQLite (chunksize réduit) et PostgreSQL (schéma auto-créé).
    """
    engine = _get_engine()
    _creer_schema_si_besoin(engine)
    schema = _detect_schema(engine)
    chunk  = _chunk_size(engine)

    df.to_sql(
        name=table_name,
        schema=schema,
        con=engine,
        if_exists="replace",
        index=False,
        method="multi",
        chunksize=chunk,
    )
    logger.info(f"[LOAD] {table_name:<20} : {len(df):>6} lignes chargées")


def charger_faits(df: pd.DataFrame, table_name: str = "fait_ventes") -> None:
    """
    Charge la table de faits par chunks.
    Compatible SQLite (chunksize réduit) et PostgreSQL (schéma auto-créé).
    """
    engine = _get_engine()
    _creer_schema_si_besoin(engine)
    schema    = _detect_schema(engine)
    chunk     = _chunk_size(engine)
    total     = 0

    for i in range(0, len(df), chunk):
        batch = df.iloc[i:i + chunk]
        mode  = "replace" if i == 0 else "append"
        batch.to_sql(
            name=table_name,
            schema=schema,
            con=engine,
            if_exists=mode,
            index=False,
            method="multi",
        )
        total += len(batch)

    logger.info(f"[LOAD] {table_name:<20} : {total:>6} lignes chargées")
