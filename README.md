# 🎵 Bot Telegram Téléchargeur YouTube

Bot Telegram permettant de télécharger l'audio (MP3) ou la vidéo (MP4) depuis YouTube avec une interface conviviale.

## Fonctionnalités

- ✨ Recherche de vidéos YouTube
- 🎵 Téléchargement en format MP3 (audio)
- 🎥 Téléchargement en format MP4 (vidéo, 720p max)
- 📊 Statistiques de téléchargement
- 🌍 Interface en français
- ⚡ File d'attente de téléchargement
- 📱 Interface utilisateur intuitive

## Prérequis

- Python 3.10+
- FFmpeg
- Token de bot Telegram
- Compte Render pour le déploiement

## Configuration locale

1. Clonez le repository :
```bash
git clone [votre-repo-url]
cd [nom-du-dossier]
```

2. Créez un fichier `.env` à la racine du projet :
```
TELEGRAM_BOT_TOKEN=votre_token_bot
ADMIN_TELEGRAM_ID=votre_id_telegram
```

3. Installez les dépendances :
```bash
pip install -r requirements.txt
```

4. Lancez le bot :
```bash
python bot.py
```

## Déploiement sur Render

1. Créez un nouveau Web Service sur Render
2. Connectez votre repository GitHub
3. Configurez les variables d'environnement :
   - `TELEGRAM_BOT_TOKEN`
   - `ADMIN_TELEGRAM_ID`
4. Sélectionnez la branche à déployer
5. Définissez la commande de démarrage : `python bot.py`

## Limitations

- Taille maximale des fichiers : 50 MB
- Téléchargements limités à un par 30 secondes
- Qualité vidéo limitée à 720p

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou une pull request.

## Licence

MIT License
