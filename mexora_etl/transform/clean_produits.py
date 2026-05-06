import pandas as pd
from datetime import date
from utils.logger import logger


def transform_produits(df: pd.DataFrame) -> pd.DataFrame:
    """
    Règles :
      R1 - Normalisation de la casse des catégories
      R2 - Remplacement des prix_catalogue null par la médiane de la catégorie
      R3 - Ajout colonnes SCD Type 2 (date_debut, date_fin, est_actif)
    """
    initial = len(df)
    logger.info(f"[TRANSFORM] produits     : début avec {initial} lignes")

    # ── R1 — Normalisation catégories ────────────────────────
    # Problème détecté : 'electronique', 'Electronique', 'ELECTRONIQUE'
    df["categorie"]     = df["categorie"].str.strip().str.title()
    df["sous_categorie"] = df["sous_categorie"].str.strip().str.title()
    logger.info("[TRANSFORM] R1 catégories: normalisées en Title Case")

    # ── R2 — Prix catalogue null ──────────────────────────────
    df["prix_catalogue"] = pd.to_numeric(df["prix_catalogue"], errors="coerce")
    nb_null = df["prix_catalogue"].isna().sum()
    if nb_null > 0:
        mediane = df.groupby("categorie")["prix_catalogue"].transform("median")
        df["prix_catalogue"] = df["prix_catalogue"].fillna(mediane)
        logger.info(
            f"[TRANSFORM] R2 prix null : {nb_null} prix remplacés par la médiane de catégorie"
        )

    # ── R3 — Colonnes SCD Type 2 ─────────────────────────────
    # Produits inactifs (actif=False) gardés mais marqués avec date_fin
    # → les commandes historiques restent liées à l'état du produit à l'époque
    today = str(date.today())
    df["date_debut"] = df["date_creation"].fillna(today)
    df["date_fin"]   = "9999-12-31"
    df["est_actif"]  = df["actif"].astype(bool)

    nb_inactifs = (~df["est_actif"]).sum()
    df.loc[~df["est_actif"], "date_fin"] = today
    logger.info(
        f"[TRANSFORM] R3 SCD Type2 : {nb_inactifs} produits inactifs marqués avec date_fin"
    )

    logger.info(f"[TRANSFORM] produits     : {initial} → {len(df)} lignes (aucune suppression)")
    return df
