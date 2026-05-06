# Mexora ETL — Pipeline Data Warehouse

## Structure du projet

```
mexora_etl/
├── config/
│   └── settings.py          # chemins et paramètres métier
├── extract/
│   └── extractor.py         # extraction brute par source
├── transform/
│   ├── clean_commandes.py   # règles R1–R7 commandes
│   ├── clean_clients.py     # règles R1–R5 clients + segmentation
│   ├── clean_produits.py    # normalisation produits + SCD
│   └── build_dimensions.py  # construction des 5 dimensions + faits
├── load/
│   └── loader.py            # chargement SQLite / PostgreSQL
├── utils/
│   └── logger.py            # logging ETL horodaté
├── logs/                    # logs générés automatiquement
├── data/                    # fichiers sources CSV/JSON
├── main.py                  # orchestration du pipeline
├── create_dwh.sql           # DDL PostgreSQL (Étape 3)
├── check_integrity.sql      # vérification intégrité référentielle
├── rapport_transformations.md
└── requirements.txt
```

## Prérequis

```bash
pip install pandas sqlalchemy
# Pour PostgreSQL (production) :
pip install psycopg2-binary
```

## Lancer le pipeline (SQLite — développement)

```bash
cd mexora_etl
python main.py
```

La base `mexora_dwh.db` est créée dans le dossier courant.  
Les logs sont générés dans `logs/etl_YYYYMMDD_HHMMSS.log`.

## Passer en PostgreSQL (production)

Dans `config/settings.py`, remplacer :
```python
DB_URL = "sqlite:///mexora_dwh.db"
```
par :
```python
DB_URL = "postgresql://user:password@localhost:5432/mexora_dwh"
```

Puis créer le schéma au préalable :
```bash
psql -U user -d mexora_dwh -f create_dwh.sql
```

## Résultats attendus après exécution

| Table | Lignes |
|---|---|
| dim_temps | 2 192 |
| dim_produit | 50 |
| dim_client | 4 891 |
| dim_region | 15 |
| dim_livreur | 16 |
| **fait_ventes** | **43 342** |

## Anomalies corrigées (résumé)

| Règle | Fichier | Lignes affectées |
|---|---|---|
| Doublons id_commande | commandes | 1 424 |
| Quantités <= 0 | commandes | 2 890 |
| Prix = 0 (tests) | commandes | 884 |
| Livreurs manquants | commandes | 3 127 |
| Doublons email | clients | 209 |
| Âges invalides | clients | 103 |
| Emails invalides | clients | 4 |
| Catégories normalisées | produits | 50 |
| Prix null → médiane | produits | 2 |
| SCD Type 2 inactifs | produits | 3 |
