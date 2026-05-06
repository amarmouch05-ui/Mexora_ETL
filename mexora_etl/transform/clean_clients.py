import re
import pandas as pd
from datetime import date
from utils.logger import logger
from config.settings import SEGMENT_GOLD, SEGMENT_SILVER, AGE_MIN, AGE_MAX


_EMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')

_MAPPING_SEXE = {
    "m": "m", "f": "f",
    "1": "m", "0": "f",
    "homme": "m", "femme": "f",
    "male": "m", "female": "f",
    "h": "m",
}


def transform_clients(df: pd.DataFrame, df_regions: pd.DataFrame) -> pd.DataFrame:
    """
    Règles :
      R1 - Déduplication sur email normalisé (garder inscription la plus récente)
      R2 - Standardisation du sexe → 'm' / 'f' / 'inconnu'
      R3 - Validation des dates de naissance (âge entre 16 et 100 ans)
      R4 - Validation du format email (invalide → None)
      R5 - Harmonisation des villes via le référentiel regions_maroc
    """
    initial = len(df)
    logger.info(f"[TRANSFORM] clients      : début avec {initial} lignes")

    # ── R1 — Déduplication sur email ─────────────────────────
    df["email_norm"] = df["email"].str.lower().str.strip()
    df["date_inscription"] = pd.to_datetime(
        df["date_inscription"], errors="coerce"
    )
    avant = len(df)
    df = (df.sort_values("date_inscription")
            .drop_duplicates(subset=["email_norm"], keep="last"))
    logger.info(
        f"[TRANSFORM] R1 doublons  : {avant - len(df)} clients en doublon supprimés"
    )

    # ── R2 — Standardisation du sexe ─────────────────────────
    df["sexe"] = (
        df["sexe"].str.lower().str.strip()
        .map(_MAPPING_SEXE)
        .fillna("inconnu")
    )
    logger.info("[TRANSFORM] R2 sexe      : standardisé → m / f / inconnu")

    # ── R3 — Validation âge ───────────────────────────────────
    df["date_naissance"] = pd.to_datetime(df["date_naissance"], errors="coerce")
    today = pd.Timestamp(date.today())
    df["age"] = ((today - df["date_naissance"]).dt.days // 365).fillna(-1).astype(int)
    ages_invalides = ((df["age"] < AGE_MIN) | (df["age"] > AGE_MAX)).sum()
    df.loc[(df["age"] < AGE_MIN) | (df["age"] > AGE_MAX), "date_naissance"] = pd.NaT
    df.loc[(df["age"] < AGE_MIN) | (df["age"] > AGE_MAX), "age"] = -1
    logger.info(
        f"[TRANSFORM] R3 âge       : {ages_invalides} dates de naissance invalidées"
    )

    # Tranche d'âge — remplacer -1 par 0 (hors bins → NaN converti en 'inconnu')
    age_pour_cut = df["age"].replace(-1, 0).fillna(0).astype(float)
    df["tranche_age"] = pd.cut(
        age_pour_cut,
        bins=[0, 18, 25, 35, 45, 55, 65, 200],
        labels=["<18", "18-24", "25-34", "35-44", "45-54", "55-64", "65+"],
        include_lowest=False,
    ).astype(str).replace("nan", "inconnu")

    # ── R4 — Validation email ─────────────────────────────────
    masque_invalide = ~df["email"].str.match(_EMAIL_RE, na=False)
    nb_invalides = masque_invalide.sum()
    df.loc[masque_invalide, "email"] = None
    logger.info(
        f"[TRANSFORM] R4 emails    : {nb_invalides} emails invalides mis à None"
    )

    # ── R5 — Harmonisation des villes ────────────────────────
    mapping_villes = {
        str(row["code_ville"]).strip().lower(): str(row["nom_ville_standard"]).strip()
        for _, row in df_regions.iterrows()
    }
    df["ville"] = (
        df["ville"].str.strip().str.lower()
        .map(mapping_villes)
        .fillna(df["ville"].str.strip().str.title())
    )
    logger.info("[TRANSFORM] R5 villes    : harmonisées via référentiel")

    # ── Nom complet ───────────────────────────────────────────
    df["nom_complet"] = df["prenom"].str.strip() + " " + df["nom"].str.strip()

    logger.info(
        f"[TRANSFORM] clients      : {initial} → {len(df)} lignes "
        f"({initial - len(df)} supprimées au total)"
    )
    return df


def calculer_segments(df_commandes: pd.DataFrame) -> pd.DataFrame:
    """
    Calcule le segment Gold / Silver / Bronze par client
    basé sur le CA cumulé des 12 derniers mois (commandes livrées).

    Règles métier Mexora :
      Gold   : CA 12 mois >= 15 000 MAD
      Silver : CA 12 mois >=  5 000 MAD
      Bronze : CA 12 mois <   5 000 MAD
    """
    # Référence = date max du dataset (données historiques finissant fin 2024)
    date_ref    = df_commandes["date_commande"].max()
    date_limite = date_ref - pd.DateOffset(days=365)

    df_recents = df_commandes[
        (df_commandes["date_commande"] >= date_limite) &
        (df_commandes["statut"] == "livré")
    ].copy()

    df_recents["montant_ttc"] = (
        df_recents["quantite"].astype(float) *
        df_recents["prix_unitaire"].astype(float)
    )

    ca = (df_recents
          .groupby("id_client")["montant_ttc"]
          .sum()
          .reset_index()
          .rename(columns={"montant_ttc": "ca_12m"}))

    def _segment(ca_val):
        if ca_val >= SEGMENT_GOLD:   return "Gold"
        if ca_val >= SEGMENT_SILVER: return "Silver"
        return "Bronze"

    ca["segment_client"] = ca["ca_12m"].apply(_segment)
    logger.info(
        f"[TRANSFORM] segments     : {ca['segment_client'].value_counts().to_dict()}"
    )
    return ca[["id_client", "segment_client", "ca_12m"]]
