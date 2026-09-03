import hashlib
import random

import mysql.connector
from mysql.connector import Error

from config import DB_CONFIG


# =========================
# Coran
# =========================

def get_quran_ayah(sura: int, aya: int) -> dict | None:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()

        query = """
            SELECT
              a.text AS arabe,
              f.text AS francais
            FROM ayahs a
            JOIN fr_hamidullah f
              ON f.sura = a.surah_id
             AND f.aya  = a.number_in_surah
            WHERE a.surah_id        = %s
              AND a.number_in_surah = %s
            LIMIT 1
        """
        cursor.execute(query, (sura, aya))
        row = cursor.fetchone()
        if not row:
            return None

        arabe, francais = row
        return {"arabe": arabe, "francais": francais}
    except Error as e:
        print("Erreur MySQL (get_quran_ayah):", e)
        return None
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_quran_surah_verse_count(sura: int) -> int:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM ayahs
            WHERE surah_id = %s
            """,
            (sura,),
        )
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except Error as e:
        print("Erreur MySQL (get_quran_surah_verse_count):", e)
        return 0
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_random_quran_ayah() -> dict | None:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            SELECT a.surah_id, a.number_in_surah, a.text AS arabe, f.text AS francais
            FROM ayahs a
            JOIN fr_hamidullah f
              ON f.sura = a.surah_id
             AND f.aya  = a.number_in_surah
            ORDER BY RAND()
            LIMIT 1
            """
        )
        row = cursor.fetchone()
        if not row:
            return None
        sura_id, aya_num, arabe, francais = row
        return {
            "sura": sura_id,
            "aya": aya_num,
            "arabe": arabe,
            "francais": francais,
        }
    except Error as e:
        print("Erreur MySQL (random_quran_ayah):", e)
        return None
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def search_quran_by_text(query: str, hard_limit: int = 100) -> tuple[list[dict], int]:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()

        base_where = "LOWER(text) LIKE %s"
        params = [f"%{query.lower()}%"]

        count_sql = f"""
            SELECT COUNT(*)
            FROM fr_hamidullah
            WHERE {base_where}
        """
        cursor.execute(count_sql, tuple(params))
        row = cursor.fetchone()
        total = row[0] if row and row[0] is not None else 0

        data_sql = f"""
            SELECT sura, aya, text
            FROM fr_hamidullah
            WHERE {base_where}
            ORDER BY sura, aya
            LIMIT %s
        """
        data_params = params + [hard_limit]
        cursor.execute(data_sql, tuple(data_params))
        rows = cursor.fetchall()

        results = []
        for sura, aya, text in rows:
            results.append({
                "sura": sura,
                "aya": aya,
                "francais": text,
            })
        return results, total
    except Error as e:
        print("Erreur MySQL (search_quran_by_text):", e)
        return [], 0
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_quran_surah(sura: int) -> list[dict]:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()

        sql = """
            SELECT
              a.number_in_surah AS aya,
              a.text            AS arabe,
              f.text            AS francais
            FROM ayahs a
            JOIN fr_hamidullah f
              ON f.sura = a.surah_id
             AND f.aya  = a.number_in_surah
            WHERE a.surah_id = %s
            ORDER BY a.number_in_surah
        """
        cursor.execute(sql, (sura,))
        rows = cursor.fetchall()

        verses = []
        for aya, arabe, francais in rows:
            verses.append({
                "aya": aya,
                "arabe": arabe,
                "francais": francais,
            })
        return verses
    except Error as e:
        print("Erreur MySQL (get_quran_surah):", e)
        return []
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_total_quran_verses() -> int:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("SELECT COUNT(*) FROM ayahs")
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else 0
    except Error as e:
        print("Erreur MySQL (count quran ayahs):", e)
        return 0
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_daily_quran_ayah_for_date(date_str: str) -> dict | None:
    total_rows = get_total_quran_verses()
    if total_rows == 0:
        return None

    h = hashlib.sha256(date_str.encode("utf-8")).hexdigest()
    seed = int(h[:8], 16)
    rnd = random.Random(seed)
    offset = rnd.randint(0, total_rows - 1)

    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            SELECT a.surah_id, a.number_in_surah, a.text AS arabe, f.text AS francais
            FROM ayahs a
            JOIN fr_hamidullah f
              ON f.sura = a.surah_id
             AND f.aya  = a.number_in_surah
            LIMIT 1 OFFSET %s
            """,
            (offset,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        sura_id, aya_num, arabe, francais = row
        return {
            "sura": sura_id,
            "aya": aya_num,
            "arabe": arabe,
            "francais": francais,
        }
    except Error as e:
        print("Erreur MySQL (daily quran ayah for date):", e)
        return None
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_random_quran_surah() -> int | None:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("SELECT DISTINCT surah_id FROM ayahs")
        rows = cursor.fetchall()
        if not rows:
            return None
        surah_ids = [r[0] for r in rows]
        return random.choice(surah_ids)
    except Error as e:
        print("Erreur MySQL (random quran surah):", e)
        return None
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


# =========================
# Settings aya du jour
# =========================

def set_quran_daily_verse_settings(guild_id: int, channel_id: int, hour: int, minute: int, timezone: str):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            INSERT INTO quran_daily_verse_settings (guild_id, channel_id, hour, minute, timezone)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                channel_id = VALUES(channel_id),
                hour = VALUES(hour),
                minute = VALUES(minute),
                timezone = VALUES(timezone)
            """,
            (guild_id, channel_id, hour, minute, timezone)
        )
        cnx.commit()
    except Error as e:
        print("Erreur MySQL (set quran daily settings):", e)
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def delete_quran_daily_verse_settings(guild_id: int):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            "DELETE FROM quran_daily_verse_settings WHERE guild_id = %s",
            (guild_id,),
        )
        cnx.commit()
    except Error as e:
        print("Erreur MySQL (delete quran daily settings):", e)
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_all_quran_daily_verse_settings():
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("SELECT guild_id, channel_id, hour, minute, timezone FROM quran_daily_verse_settings")
        rows = cursor.fetchall()
        return rows
    except Error as e:
        print("Erreur MySQL (get quran daily settings):", e)
        return []
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


# =========================
# Settings hadith du jour
# =========================

def set_hadith_daily_settings(guild_id: int, channel_id: int, hour: int, minute: int, timezone: str):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            INSERT INTO hadith_daily_settings (guild_id, channel_id, hour, minute, timezone)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                channel_id = VALUES(channel_id),
                hour = VALUES(hour),
                minute = VALUES(minute),
                timezone = VALUES(timezone)
            """,
            (guild_id, channel_id, hour, minute, timezone)
        )
        cnx.commit()
    except Error as e:
        print("Erreur MySQL (set hadith daily settings):", e)
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def delete_hadith_daily_settings(guild_id: int):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            "DELETE FROM hadith_daily_settings WHERE guild_id = %s",
            (guild_id,),
        )
        cnx.commit()
    except Error as e:
        print("Erreur MySQL (delete hadith daily settings):", e)
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_all_hadith_daily_settings():
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute("SELECT guild_id, channel_id, hour, minute, timezone FROM hadith_daily_settings")
        rows = cursor.fetchall()
        return rows
    except Error as e:
        print("Erreur MySQL (get hadith daily settings):", e)
        return []
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def set_daily_hadith_for_date(date_str: str, hadeeth_id: int, label: str | None):
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            """
            INSERT INTO hadith_daily_cache (date_str, hadeeth_id, label)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
              hadeeth_id = VALUES(hadeeth_id),
              label      = VALUES(label)
            """,
            (date_str, hadeeth_id, label),
        )
        cnx.commit()
    except Error as e:
        print("Erreur MySQL (set_daily_hadith_for_date):", e)
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass


def get_daily_hadith_for_date(date_str: str) -> tuple[int | None, str | None]:
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            "SELECT hadeeth_id, label FROM hadith_daily_cache WHERE date_str = %s",
            (date_str,),
        )
        row = cursor.fetchone()
        if not row:
            return None, None
        return row[0], row[1]
    except Error as e:
        print("Erreur MySQL (get_daily_hadith_for_date):", e)
        return None, None
    finally:
        try:
            cursor.close()
            cnx.close()
        except Exception:
            pass
