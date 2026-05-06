import pandas as pd
from datetime import date
from utils.logger import logger


# ── DIM_TEMPS ─────────────────────────────────────────────────
_FERIES_MAROC = {
    "2022-01-01","2022-01-11","2022-05-01","2022-07-30",
    "2022-08-14","2022-08-20","2022-11-06","2022-11-18",
    "2023-01-01","2023-01-11","2023-05-01","2023-07-30",
    "2023-08-14","2023-08-20","2023-11-06","2023-11-18",
    "2024-01-01","2024-01-11","2024-05-01","2024-07-30",
    "2024-08-14","2024-08-20","2024-11-06","2024-11-18",
    "2025-01-01","2025-01-11","2025-05-01","2025-07-30",
    "2025-08-14","2025-08-20","2025-11-06","2025-11-18",
}

_RAMADAN = [
    ("2022-04-02", "2022-05-01"),
    ("2023-03-22", "2023-04-20"),
    ("2024-03-10", "2024-04-09"),
    ("2025-03-01", "2025-03-30"),
]


def build_dim_temps(date_debut: str = "2020-01-01",
                    date_fin: str   = "2025-12-31") -> pd.DataFrame:
    dates = pd.date_range(start=date_debut, end=date_fin, freq="D")

    df = pd.DataFrame({
        "id_date":        dates.strftime("%Y%m%d").astype(int),
        "date_complete":  dates.date,
        "jour":           dates.day,
        "mois":           dates.month,
        "trimestre":      dates.quarter,
        "annee":          dates.year,
        "semaine":        dates.isocalendar().week.astype(int),
        "libelle_jour":   dates.strftime("%A"),
        "libelle_mois":   dates.strftime("%B"),
        "est_weekend":    dates.dayofweek >= 5,
        "est_ferie_maroc": dates.strftime("%Y-%m-%d").isin(_FERIES_MAROC),
        "periode_ramadan": False,
    })

    for debut, fin in _RAMADAN:
        masque = (df["date_complete"] >= pd.Timestamp(debut).date()) & \
                 (df["date_complete"] <= pd.Timestamp(fin).date())
        df.loc[masque, "periode_ramadan"] = True

    logger.info(f"[BUILD] dim_temps        : {len(df)} lignes ({date_debut} → {date_fin})")
    return df.drop(columns=["date_complete"])


# ── DIM_PRODUIT ───────────────────────────────────────────────
def build_dim_produit(df_produits: pd.DataFrame) -> pd.DataFrame:
    df = df_produits.rename(columns={
        "id_produit":     "id_produit_nk",
        "nom":            "nom_produit",
        "prix_catalogue": "prix_standard",
        "origine_pays":   "origine_pays",
    })[[
        "id_produit_nk","nom_produit","categorie","sous_categorie",
        "marque","fournisseur","prix_standard","origine_pays",
        "date_debut","date_fin","est_actif",
    ]].copy()
    df.insert(0, "id_produit_sk", range(1, len(df) + 1))
    logger.info(f"[BUILD] dim_produit      : {len(df)} lignes")
    return df


# ── DIM_CLIENT ────────────────────────────────────────────────
def build_dim_client(df_clients: pd.DataFrame,
                     df_segments: pd.DataFrame) -> pd.DataFrame:
    df = df_clients.merge(df_segments, on="id_client", how="left")
    df["segment_client"] = df["segment_client"].fillna("Bronze")

    df = df.rename(columns={"id_client": "id_client_nk"})[[
        "id_client_nk","nom_complet","tranche_age","sexe",
        "ville","segment_client","canal_acquisition",
    ]].copy()
    df.insert(0, "id_client_sk", range(1, len(df) + 1))
    logger.info(f"[BUILD] dim_client       : {len(df)} lignes")
    return df


# ── DIM_REGION ────────────────────────────────────────────────
def build_dim_region(df_regions: pd.DataFrame) -> pd.DataFrame:
    # Une ligne par ville standard (déduplication)
    df = (df_regions
          .rename(columns={"nom_ville_standard": "ville"})
          [["ville","province","region_admin","zone_geo"]]
          .drop_duplicates(subset=["ville"])
          .copy())
    df.insert(0, "id_region", range(1, len(df) + 1))
    logger.info(f"[BUILD] dim_region       : {len(df)} lignes")
    return df


# ── DIM_LIVREUR ───────────────────────────────────────────────
def build_dim_livreur(df_livreurs: pd.DataFrame) -> pd.DataFrame:
    df = df_livreurs.rename(columns={"id_livreur": "id_livreur_nk"}).copy()
    # Ajouter le livreur inconnu (pour les id_livreur = '-1')
    inconnu = pd.DataFrame([{
        "id_livreur_nk": "-1",
        "nom_livreur":   "Livreur inconnu",
        "type_transport":"Inconnu",
        "zone_couverture":"Inconnue",
    }])
    df = pd.concat([df, inconnu], ignore_index=True)
    df.insert(0, "id_livreur_sk", range(1, len(df) + 1))
    logger.info(f"[BUILD] dim_livreur      : {len(df)} lignes (+ 1 livreur inconnu)")
    return df


# ── FAIT_VENTES ───────────────────────────────────────────────
def build_fait_ventes(df_cmd: pd.DataFrame,
                      dim_temps:   pd.DataFrame,
                      dim_client:  pd.DataFrame,
                      dim_produit: pd.DataFrame,
                      dim_region:  pd.DataFrame,
                      dim_livreur: pd.DataFrame) -> pd.DataFrame:
    """
    Construit la table de faits en joignant les clés de substitution
    (surrogate keys) des dimensions sur les clés naturelles.

    Granularité : 1 ligne = 1 commande (id_commande unique).
    """
    df = df_cmd.copy()

    # Clé temporelle
    df["id_date"] = df["date_commande"].dt.strftime("%Y%m%d").astype(int)

    # Clé produit (natural key → surrogate key)
    map_prod = dim_produit.set_index("id_produit_nk")["id_produit_sk"]
    df["id_produit"] = df["id_produit"].map(map_prod)

    # Clé client
    map_cli = dim_client.set_index("id_client_nk")["id_client_sk"]
    df["id_client"] = df["id_client"].map(map_cli)

    # Clé région (ville_livraison harmonisée → id_region)
    map_reg = dim_region.set_index("ville")["id_region"]
    df["id_region"] = df["ville_livraison"].map(map_reg)

    # Clé livreur
    map_liv = dim_livreur.set_index("id_livreur_nk")["id_livreur_sk"]
    df["id_livreur"] = df["id_livreur"].map(map_liv)

    # Sélection colonnes finales
    fait = df[[
        "id_date","id_produit","id_client","id_region","id_livreur",
        "quantite","montant_ht","montant_ttc",
        "delai_livraison_jours","statut",
    ]].rename(columns={
        "quantite": "quantite_vendue",
        "statut":   "statut_commande",
    }).copy()

    # Surrogate key
    fait.insert(0, "id_vente", range(1, len(fait) + 1))

    # Supprimer les lignes sans correspondance dans les dimensions
    avant = len(fait)
    fait = fait.dropna(subset=["id_produit","id_client","id_region"])
    logger.info(
        f"[BUILD] fait_ventes      : {avant} → {len(fait)} lignes "
        f"({avant - len(fait)} sans correspondance dimension)"
    )
    return fait
