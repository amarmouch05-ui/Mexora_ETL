import pandas as pd
import json
from utils.logger import logger
from config.settings import (
    COMMANDES_PATH, CLIENTS_PATH, PRODUITS_PATH,
    REGIONS_PATH, LIVREURS_PATH
)


def extract_commandes() -> pd.DataFrame:
    """Extrait les commandes depuis le CSV source — aucune modification."""
    df = pd.read_csv(COMMANDES_PATH, encoding="utf-8", dtype=str)
    logger.info(f"[EXTRACT] commandes      : {len(df):>6} lignes extraites")
    return df


def extract_clients() -> pd.DataFrame:
    """Extrait les clients depuis le CSV source — aucune modification."""
    df = pd.read_csv(CLIENTS_PATH, encoding="utf-8", dtype=str)
    logger.info(f"[EXTRACT] clients        : {len(df):>6} lignes extraites")
    return df


def extract_produits() -> pd.DataFrame:
    """Extrait les produits depuis le JSON source — aucune modification."""
    with open(PRODUITS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    df = pd.DataFrame(data["produits"])
    logger.info(f"[EXTRACT] produits       : {len(df):>6} lignes extraites")
    return df


def extract_regions() -> pd.DataFrame:
    """Extrait le référentiel géographique (déjà propre)."""
    df = pd.read_csv(REGIONS_PATH, encoding="utf-8", dtype=str)
    logger.info(f"[EXTRACT] regions        : {len(df):>6} lignes extraites")
    return df


def extract_livreurs() -> pd.DataFrame:
    """Extrait les livreurs (déjà propre)."""
    df = pd.read_csv(LIVREURS_PATH, encoding="utf-8", dtype=str)
    logger.info(f"[EXTRACT] livreurs       : {len(df):>6} lignes extraites")
    return df
