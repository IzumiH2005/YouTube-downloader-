from flask import Flask
from threading import Thread, Event
from bot import YouTubeAudioDownloaderBot
import logging
import sys
import atexit
import os
import time

# Configuration des logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
bot_instance = None
stop_event = Event()
bot_lock = Event()

@app.route('/')
def home():
    return "Bot is alive!", 200

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def start_bot():
    global bot_instance
    if not bot_lock.is_set():
        try:
            bot_lock.set()  # Marquer que le bot est en cours de démarrage
            if bot_instance is None:
                bot_instance = YouTubeAudioDownloaderBot()
                bot_instance.run(stop_event)
        except Exception as e:
            logger.error(f"Erreur lors du démarrage du bot : {e}")
            if bot_instance:
                bot_instance = None
        finally:
            bot_lock.clear()  # Libérer le verrou

def cleanup():
    logger.info("Nettoyage des ressources...")
    stop_event.set()
    if bot_instance:
        logger.info("Arrêt du bot...")
        time.sleep(2)  # Laisser le temps au bot de s'arrêter proprement
    bot_lock.clear()

def keep_alive():
    # Enregistrer la fonction de nettoyage
    atexit.register(cleanup)

    # Démarrer le serveur Flask dans un thread
    server = Thread(target=run_flask, daemon=True)
    server.start()
    logger.info("Serveur web démarré")

    # S'assurer qu'aucune autre instance n'est en cours d'exécution
    time.sleep(1)  # Attendre que le serveur Flask soit prêt

    # Démarrer le bot dans le thread principal
    logger.info("Démarrage du bot...")
    start_bot()

if __name__ == "__main__":
    try:
        keep_alive()
    except KeyboardInterrupt:
        logger.info("Arrêt du serveur et du bot...")
        cleanup()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Erreur critique : {e}")
        cleanup()
        sys.exit(1)