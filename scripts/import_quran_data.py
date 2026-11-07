#!/usr/bin/env python3
"""Télécharge le texte arabe du Coran et la traduction française de Hamidullah
depuis Tanzil (https://tanzil.net) et les charge dans les tables `ayahs` et
`fr_hamidullah` utilisées par le bot.

Ces textes ne sont pas fournis avec le dépôt : voir NOTICE pour leurs
conditions d'utilisation. Elles doivent être acceptées explicitement avec
--accept-tanzil-terms.

Exemples :
    python scripts/import_quran_data.py --accept-tanzil-terms --dry-run
    python scripts/import_quran_data.py --accept-tanzil-terms

La connexion utilise les mêmes variables que le bot (DB_HOST, DB_USER,
DB_PASSWORD, DB_NAME).
"""
import argparse
import os
import sys
import urllib.request

ARABIC_URL = "https://tanzil.net/pub/download/index.php?quranType=uthmani&outType=txt-2&agree=true"
FRENCH_URL = "https://tanzil.net/trans/?transID=fr.hamidullah&type=txt-2"
EXPECTED_VERSES = 6236

DDL = (
    """
    CREATE TABLE IF NOT EXISTS ayahs (
        surah_id        INT UNSIGNED NOT NULL,
        number_in_surah INT UNSIGNED NOT NULL,
        text            TEXT NOT NULL,
        PRIMARY KEY (surah_id, number_in_surah)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
    """
    CREATE TABLE IF NOT EXISTS fr_hamidullah (
        `index` INT NOT NULL,
        sura    INT NOT NULL DEFAULT 0,
        aya     INT NOT NULL DEFAULT 0,
        text    TEXT NOT NULL,
        KEY idx_sura_aya (sura, aya)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """,
)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "AlHudaBot-import/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read().decode("utf-8")


def parse(raw, label):
    """Lit les lignes `sourate|aya|texte` en ignorant les commentaires `#`."""
    rows = []
    for line in raw.splitlines():
        if not line.strip() or line.startswith("#"):
            continue
        sura, aya, text = line.split("|", 2)
        rows.append((int(sura), int(aya), text.strip()))
    if len(rows) != EXPECTED_VERSES:
        sys.exit(f"{label} : {len(rows)} versets reçus, {EXPECTED_VERSES} attendus")
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--accept-tanzil-terms", action="store_true",
                    help="confirme avoir lu et accepté les conditions de Tanzil (voir NOTICE)")
    ap.add_argument("--dry-run", action="store_true",
                    help="télécharge et vérifie les données sans toucher à la base")
    args = ap.parse_args()
    if not args.accept_tanzil_terms:
        sys.exit("Lis le fichier NOTICE puis relance avec --accept-tanzil-terms.")

    arabic = parse(fetch(ARABIC_URL), "texte arabe")
    french = parse(fetch(FRENCH_URL), "traduction française")
    print(f"{len(arabic)} versets arabes, {len(french)} versets français téléchargés")
    if args.dry_run:
        print("--dry-run : base inchangée")
        return

    import mysql.connector

    conn = mysql.connector.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        user=os.environ.get("DB_USER", "alhudauser"),
        password=os.environ["DB_PASSWORD"],
        database=os.environ.get("DB_NAME", "alhuda"),
        charset="utf8mb4",
    )
    try:
        cur = conn.cursor()
        for stmt in DDL:
            cur.execute(stmt)
        cur.execute("DELETE FROM ayahs")
        cur.execute("DELETE FROM fr_hamidullah")
        cur.executemany("INSERT INTO ayahs (surah_id, number_in_surah, text) VALUES (%s, %s, %s)", arabic)
        cur.executemany(
            "INSERT INTO fr_hamidullah (`index`, sura, aya, text) VALUES (%s, %s, %s, %s)",
            [(i, s, a, t) for i, (s, a, t) in enumerate(french, 1)],
        )
        conn.commit()
    finally:
        conn.close()
    print("Import terminé.")


if __name__ == "__main__":
    main()
