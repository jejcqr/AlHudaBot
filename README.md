# AlHudaBot

Bot Discord en français pour lire le Coran (texte arabe et traduction
française de Muhammad Hamidullah) et des hadiths, et recevoir chaque jour une
aya ou un hadith dans un salon.

## Fonctionnalités

- Lecture d'une aya ou d'une sourate entière, en arabe et en français, avec pagination
- Recherche dans la traduction française du Coran
- Aya du jour, aya et sourate aléatoires
- Hadiths de l'[Encyclopédie des hadiths traduits](https://hadeethenc.com) : catégories,
  recherche par catégorie, hadith par identifiant (arabe, français et explication)
- Hadith du jour, mis en cache en base pour être le même sur tous les serveurs
- Envois automatiques planifiés par serveur, à l'heure et dans le fuseau horaire choisis

## Commandes

| Commande | Rôle |
|---|---|
| `/aya` | affiche une aya (sourate et numéro) |
| `/sourate` | affiche une sourate entière, page par page |
| `/search` | cherche un texte dans la traduction française |
| `/randomaya` · `/randomsourate` | aya ou sourate aléatoire |
| `/dailyaya` | aya du jour |
| `/hadith` | affiche un hadith par son identifiant |
| `/hadithcategories` | liste ou recherche les catégories de hadiths |
| `/listhadiths` | liste les hadiths d'une catégorie |
| `/randomhadith` | hadith aléatoire, global ou dans une catégorie |
| `/dailyhadith` | hadith du jour |
| `/setdailyaya` · `/disabledailyaya` | active / désactive l'envoi quotidien de l'aya |
| `/setdailyhadith` · `/disabledailyhadith` | active / désactive l'envoi quotidien du hadith |
| `/help` | liste des commandes |
| `/reload` | recharge un module sans redémarrer (propriétaire du bot uniquement) |

## Technologies

- **Python 3.10+** avec [py-cord](https://pycord.dev) (commandes slash, vues à boutons)
- **MySQL / MariaDB** via `mysql-connector-python`, requêtes paramétrées
- **APScheduler** pour les envois quotidiens, **pytz** pour les fuseaux horaires
- **API HadeethEnc** (`hadeethenc.com/api/v1`) pour les hadiths

## Installation

### 1. Base de données

```bash
mysql -u root -p -e "CREATE DATABASE alhuda CHARACTER SET utf8mb4;
  CREATE USER 'alhudauser'@'localhost' IDENTIFIED BY 'motdepasse';
  GRANT ALL PRIVILEGES ON alhuda.* TO 'alhudauser'@'localhost';"
mysql -u root -p alhuda < quran_data.sql
```

Puis créer les tables des envois automatiques et du cache des hadiths :

```sql
CREATE TABLE IF NOT EXISTS quran_daily_verse_settings (
    guild_id   BIGINT UNSIGNED PRIMARY KEY,
    channel_id BIGINT UNSIGNED NOT NULL,
    hour       TINYINT UNSIGNED NOT NULL,
    minute     TINYINT UNSIGNED NOT NULL,
    timezone   VARCHAR(64) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
CREATE TABLE IF NOT EXISTS hadith_daily_settings LIKE quran_daily_verse_settings;
CREATE TABLE IF NOT EXISTS hadith_daily_cache (
    date_str   CHAR(10) PRIMARY KEY,
    hadeeth_id INT UNSIGNED NOT NULL,
    label      VARCHAR(255) NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 2. Bot Discord

1. Créer une application sur le [portail développeur Discord](https://discord.com/developers/applications),
   puis un bot, et copier son jeton.
2. L'inviter sur un serveur avec les scopes `bot` et `applications.commands`.

### 3. Lancement

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

Le bot lit sa configuration dans les variables d'environnement (voir `.env.example`) :

| Variable | Valeur |
|---|---|
| `DISCORD_TOKEN` | jeton du bot |
| `DB_HOST` | hôte MySQL (défaut : `localhost`) |
| `DB_USER` | utilisateur (défaut : `alhudauser`) |
| `DB_PASSWORD` | mot de passe (obligatoire) |
| `DB_NAME` | base (défaut : `alhuda`) |

```bash
set -a; source .env; set +a
python alhudabot.py
```

Les commandes `/setdaily…` et `/disabledaily…` ne vérifient pas les
permissions de l'utilisateur : pensez à les réserver aux modérateurs dans
*Paramètres du serveur → Intégrations → AlHudaBot*.

## Structure

```
alhudabot.py      démarrage, chargement des modules, planificateur
config.py         configuration (jeton, base, URL de l'API)
database.py       accès à la base (ayas, recherche, réglages, cache du hadith du jour)
quran_utils.py    mise en forme et pagination des ayas
hadeeth_api.py    client de l'API HadeethEnc
hadith_utils.py   mise en forme des hadiths
cogs/             commandes Discord regroupées par thème
quran_data.sql    texte arabe et traduction française du Coran
```

## Voir aussi

- [YeshuaBot](https://github.com/jejcqr/YeshuaBot), le bot équivalent pour la Bible et la liturgie catholique
