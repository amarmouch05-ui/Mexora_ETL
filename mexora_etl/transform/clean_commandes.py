import pandas as pd
from utils.logger import logger


# ── Référentiel villes ────────────────────────────────────────
def _charger_mapping_villes(df_regions: pd.DataFrame) -> dict:
    """
    Construit un dict {alias_lowercase -> nom_standard}
    depuis le fichier regions_maroc.csv.
    Ex: {'tng': 'Tanger', 'tanja': 'Tanger', 'casa': 'Casablanca', ...}
    """
    mapping = {}
    for _, row in df_regions.iterrows():
        alias    = str(row["code_ville"]).strip().lower()
        standard = str(row["nom_ville_standard"]).strip()
        mapping[alias] = standard
    return mapping


# ── Transformation principale ─────────────────────────────────
def transform_commandes(df: pd.DataFrame, df_regions: pd.DataFrame) -> pd.DataFrame:
    """
    Applique les 7 règles de nettoyage sur les commandes Mexora.

    Règles :
      R1 - Suppression des doublons sur id_commande (garder la dernière occurrence)
      R2 - Standardisation des dates (format cible : YYYY-MM-DD)
      R3 - Harmonisation des villes via le référentiel regions_maroc
      R4 - Standardisation des statuts de commande
      R5 - Suppression des lignes avec quantite <= 0
      R6 - Suppression des lignes avec prix_unitaire = 0 (commandes test)
      R7 - Remplacement des id_livreur manquants par '-1' (livreur inconnu)
    """
    initial = len(df)
    logger.info(f"[TRANSFORM] commandes    : début avec {initial} lignes")

    # ── R1 — Doublons ────────────────────────────────────────
    avant = len(df)
    df = df.drop_duplicates(subset=["id_commande"], keep="last")
    suppr = avant - len(df)
    logger.info(f"[TRANSFORM] R1 doublons  : {suppr} lignes supprimées")

    # ── R2 — Standardisation des dates ───────────────────────
    # Les 3 formats présents : DD/MM/YYYY  |  YYYY-MM-DD  |  Mon DD YYYY
    df["date_commande"] = pd.to_datetime(
        df["date_commande"], format="mixed", dayfirst=True, errors="coerce"
    )
    df["date_livraison"] = pd.to_datetime(
        df["date_livraison"], format="mixed", dayfirst=True, errors="coerce"
    )
    dates_invalides = df["date_commande"].isna().sum()
    df = df.dropna(subset=["date_commande"])
    logger.info(f"[TRANSFORM] R2 dates     : {dates_invalides} dates invalides supprimées")

    # ── R3 — Harmonisation des villes ────────────────────────
    mapping_villes = _charger_mapping_villes(df_regions)
    avant_inconnus = (df["ville_livraison"].str.strip().str.lower()
                      .map(mapping_villes).isna().sum())
    df["ville_livraison"] = (
        df["ville_livraison"]
        .str.strip()
        .str.lower()
        .map(mapping_villes)
        .fillna("Non renseignée")
    )
    logger.info(
        f"[TRANSFORM] R3 villes    : {avant_inconnus} villes non reconnues → 'Non renseignée'"
    )

    # ── R4 — Standardisation des statuts ─────────────────────
    mapping_statuts = {
        # livré
        "livré": "livré", "livre": "livré", "LIVRE": "livré", "DONE": "livré",
        # annulé
        "annulé": "annulé", "annule": "annulé", "KO": "annulé",
        # en_cours
        "en_cours": "en_cours", "OK": "en_cours",
        # retourné
        "retourné": "retourné", "retourne": "retourné",
    }
    df["statut"] = df["statut"].map(mapping_statuts)
    inconnus = df["statut"].isna().sum()
    df["statut"] = df["statut"].fillna("inconnu")
    logger.info(
        f"[TRANSFORM] R4 statuts   : {inconnus} valeurs non reconnues → 'inconnu'"
    )

    # ── R5 — Quantités invalides ──────────────────────────────
    avant = len(df)
    df = df[df["quantite"].astype(float) > 0]
    logger.info(
        f"[TRANSFORM] R5 quantités : {avant - len(df)} lignes supprimées (quantite <= 0)"
    )

    # ── R6 — Prix nuls (commandes test) ──────────────────────
    avant = len(df)
    df = df[df["prix_unitaire"].astype(float) > 0]
    logger.info(
        f"[TRANSFORM] R6 prix nuls : {avant - len(df)} commandes test supprimées"
    )

    # ── R7 — Livreurs manquants ───────────────────────────────
    nb_manquants = df["id_livreur"].isna().sum()
    df["id_livreur"] = df["id_livreur"].fillna("-1")
    logger.info(
        f"[TRANSFORM] R7 livreurs  : {nb_manquants} valeurs manquantes → '-1'"
    )

    # ── Calcul montant TTC ────────────────────────────────────
    df["montant_ttc"] = df["quantite"].astype(float) * df["prix_unitaire"].astype(float)
    df["montant_ht"]  = (df["montant_ttc"] / 1.20).round(2)   # TVA 20% Maroc

    # ── Délai livraison en jours ──────────────────────────────
    df["delai_livraison_jours"] = (
        (df["date_livraison"] - df["date_commande"]).dt.days
    )

    logger.info(
        f"[TRANSFORM] commandes    : {initial} → {len(df)} lignes "
        f"({initial - len(df)} supprimées au total)"
    )
    return df
