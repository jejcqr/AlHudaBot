import random
import time

import requests

from config import HADEETHENC_BASE, HADEETHENC_LANG

_categories_cache: list[dict] = []
_categories_loaded_at: float | None = None


def load_categories(force: bool = False) -> list[dict]:
    """
    Charge toutes les catégories HadeethEnc (langue FR) avec cache en mémoire.
    """
    global _categories_cache, _categories_loaded_at

    if (
        not force
        and _categories_cache
        and _categories_loaded_at
        and (time.time() - _categories_loaded_at) < 3600
    ):
        return _categories_cache

    try:
        resp = requests.get(
            f"{HADEETHENC_BASE}/categories/list",
            params={"language": HADEETHENC_LANG},
            timeout=10,
        )
    except Exception as e:
        print("Exception HadeethEnc (categories load):", e)
        return _categories_cache

    if resp.status_code != 200:
        print("Erreur HadeethEnc (categories):", resp.status_code, resp.text)
        return _categories_cache

    data = resp.json()
    if isinstance(data, list):
        categories = data
    else:
        categories = data.get("data", []) if isinstance(data, dict) else []

    _categories_cache = categories
    _categories_loaded_at = time.time()
    print(f"HadeethEnc: {len(categories)} catégories chargées.")
    return categories


def get_random_from_category(category_id: int) -> dict | None:
    """
    Hadith aléatoire depuis HadeethEnc dans une catégorie donnée (langue française).
    On pioche d'abord une page aléatoire, puis un hadith dans cette page.
    """
    try:
        resp = requests.get(
            f"{HADEETHENC_BASE}/hadeeths/list",
            params={
                "language": HADEETHENC_LANG,
                "category_id": category_id,
                "page": 1,
                "per_page": 10,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            print("Erreur HadeethEnc (list page 1):", resp.status_code, resp.text)
            return None

        data = resp.json()
        meta = data.get("meta", {})
        per_page = int(meta.get("per_page", 10))
        last_page = int(meta.get("last_page", 1))
        if last_page <= 0:
            return None

        page = random.randint(1, last_page)

        resp2 = requests.get(
            f"{HADEETHENC_BASE}/hadeeths/list",
            params={
                "language": HADEETHENC_LANG,
                "category_id": category_id,
                "page": page,
                "per_page": per_page,
            },
            timeout=10,
        )
        if resp2.status_code != 200:
            print("Erreur HadeethEnc (list random page):", resp2.status_code, resp2.text)
            return None

        data2 = resp2.json()
        items = data2.get("data", [])
        if not items:
            return None

        return random.choice(items)

    except Exception as e:
        print("Exception HadeethEnc (random):", e)
        return None


def get_all_in_category(category_id: int, per_page: int = 20) -> list[dict]:
    """
    Récupère tous les hadiths d'une catégorie (en français), titres + IDs.
    On parcourt toutes les pages de /hadeeths/list.
    """
    all_items: list[dict] = []

    try:
        resp = requests.get(
            f"{HADEETHENC_BASE}/hadeeths/list",
            params={
                "language": HADEETHENC_LANG,
                "category_id": category_id,
                "page": 1,
                "per_page": per_page,
            },
            timeout=10,
        )
        if resp.status_code != 200:
            print("Erreur HadeethEnc (list all, page 1):", resp.status_code, resp.text)
            return []

        data = resp.json()
        meta = data.get("meta", {})
        first_items = data.get("data", []) or []
        all_items.extend(first_items)

        last_page = int(meta.get("last_page", 1))
        if last_page <= 1:
            return all_items

        for page in range(2, last_page + 1):
            try:
                resp_p = requests.get(
                    f"{HADEETHENC_BASE}/hadeeths/list",
                    params={
                        "language": HADEETHENC_LANG,
                        "category_id": category_id,
                        "page": page,
                        "per_page": per_page,
                    },
                    timeout=10,
                )
                if resp_p.status_code != 200:
                    print("Erreur HadeethEnc (list all, page", page, "):", resp_p.status_code, resp_p.text)
                    break

                data_p = resp_p.json()
                page_items = data_p.get("data", []) or []
                if not page_items:
                    break

                all_items.extend(page_items)
            except Exception as e:
                print("Exception HadeethEnc (list all, page", page, "):", e)
                break

    except Exception as e:
        print("Exception HadeethEnc (list all):", e)

    return all_items


def get_by_id(hadith_id: int) -> dict | None:
    """
    Récupère un hadith précis (arabe + français + meta) depuis HadeethEnc.
    """
    try:
        resp = requests.get(
            f"{HADEETHENC_BASE}/hadeeths/one",
            params={"id": hadith_id, "language": HADEETHENC_LANG},
            timeout=10,
        )
        if resp.status_code != 200:
            print("Erreur HadeethEnc (one):", resp.status_code, resp.text)
            return None
        data = resp.json()
        if not isinstance(data, dict):
            return None
        return data
    except Exception as e:
        print("Exception HadeethEnc (one):", e)
        return None


def get_random_global() -> tuple[dict | None, str | None]:
    """
    Hadith aléatoire global : on choisit une catégorie au hasard,
    puis un hadith aléatoire dans cette catégorie.
    Retourne (data_hadith_complet, label_categorie) ou (None, None).
    """
    cats = load_categories()
    if not cats:
        return None, None

    cat = random.choice(cats)
    try:
        cat_id = int(cat.get("id"))
    except Exception:
        return None, None

    label = cat.get("title", f"Catégorie {cat_id}")
    item = get_random_from_category(cat_id)
    if not item:
        return None, None

    try:
        h_id = int(item.get("id"))
    except Exception:
        return None, None

    data = get_by_id(h_id)
    if not data:
        return None, None

    return data, label
