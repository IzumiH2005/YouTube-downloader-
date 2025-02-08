import os
import logging
import asyncio
import re
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    ConversationHandler
)
from telegram import ParseMode
from telegram import error as telegram_error
from telegram.utils.request import Request
import tempfile
import hashlib

from config import Config
from locales import MESSAGES
from cache import Cache
from db_models import Database
from download_manager import DownloadManager

# Configuration des logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class YouTubeAudioDownloaderBot:
    # États de conversation
    (SEARCH_QUERY, SELECT_RESULT, SELECT_FORMAT) = range(3)

    def __init__(self):
        # Initialize components
        self.config = Config()
        self.cache = Cache()
        self.db = Database()
        self.download_manager = DownloadManager()

        # Amélioration de la gestion des instances
        self._request = Request(
            con_pool_size=8,
            connect_timeout=30,
            read_timeout=30
        )

        # Initialize properties
        self.active_downloads = {}
        self.retry_attempts = {}
        self.max_retries = 3
        self._tmp_dir = tempfile.mkdtemp()

    def start_command(self, update: Update, context) -> int:
        """Commande de démarrage du bot"""
        keyboard = [
            [
                InlineKeyboardButton("🔍 Rechercher", callback_data='search'),
                InlineKeyboardButton("❓ Aide", callback_data='help')
            ],
            [
                InlineKeyboardButton("📊 Mes Stats", callback_data='stats')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        update.message.reply_text(
            MESSAGES['fr']['welcome'],
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )
        return ConversationHandler.END

    def callback_handler(self, update: Update, context) -> int:
        """Gérer les interactions avec les boutons"""
        query = update.callback_query
        query.answer()

        if query.data == 'search':
            query.edit_message_text(
                "🔍 Envoyez le titre ou l'URL de la vidéo à télécharger :"
            )
            return self.SEARCH_QUERY

        elif query.data == 'help':
            help_text = (
                "*🤖 Guide d'utilisation* \n\n"
                "• Envoyez un titre ou une URL YouTube\n"
                "• Le bot vous proposera les résultats\n"
                "• Sélectionnez la vidéo à télécharger\n\n"
                "_Limitations_ :\n"
                "• Fichiers < 50 MB\n"
                "• Téléchargement toutes les 30 secondes"
            )
            query.edit_message_text(
                help_text,
                parse_mode=ParseMode.MARKDOWN
            )
            return ConversationHandler.END

        elif query.data == 'stats':
            self.show_stats(update, context)
            return ConversationHandler.END

    def search_audio(self, update: Update, context) -> int:
        """Rechercher et proposer des résultats audio"""
        query = update.message.text

        search_message = update.message.reply_text(
            "🔍 Recherche en cours...\nVeuillez patienter quelques secondes ⏳",
            parse_mode=ParseMode.MARKDOWN
        )

        try:
            search_results = self.download_manager.search_video(query)

            if not search_results:
                search_message.edit_text("❌ Aucun résultat trouvé.")
                return ConversationHandler.END

            keyboard = []
            for i, video in enumerate(search_results[:self.config.MAX_SEARCH_RESULTS]):
                title = video['title'][:50] + ('...' if len(video['title']) > 50 else '')
                keyboard.append([
                    InlineKeyboardButton(
                        f"{i+1}. {title}",
                        callback_data=f"select_video_{i}"
                    )
                ])

            keyboard.append([
                InlineKeyboardButton("🔙 Annuler", callback_data="cancel")
            ])

            search_message.edit_text(
                "🎵 Sélectionnez une vidéo :",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

            context.user_data['search_results'] = search_results
            return self.SELECT_RESULT

        except Exception as e:
            logger.error(f"Erreur de recherche : {e}")
            search_message.edit_text(f"❌ Erreur lors de la recherche : {str(e)}")
            return ConversationHandler.END

    def process_download(self, update: Update, context) -> int:
        """Process download with format selection"""
        query = update.callback_query
        user_id = update.effective_user.id

        if query.data == 'cancel':
            query.edit_message_text("❌ Recherche annulée.")
            return ConversationHandler.END

        try:
            if query.data.startswith('format_'):
                format_type = query.data.split('_')[1]
                video_data = context.user_data.get('selected_video')

                if not video_data:
                    query.edit_message_text("❌ Erreur : vidéo non trouvée.")
                    return ConversationHandler.END

                # Message de téléchargement avec limite de taille
                download_message = (
                    f"🔽 Téléchargement en cours : *{video_data['title']}*\n"
                    f"Format : {'🎵 MP3' if format_type == 'mp3' else '🎥 MP4'}\n"
                    f"Taille maximale autorisée : {self.config.MAX_FILE_SIZE_MB}MB"
                )
                query.edit_message_text(
                    download_message,
                    parse_mode=ParseMode.MARKDOWN
                )

                try:
                    file_path, info, file_size = self.download_manager.download_media(
                        video_data['url'],
                        format_type=format_type
                    )

                    if format_type == 'mp3':
                        with open(file_path, 'rb') as audio:
                            update.effective_chat.send_audio(
                                audio,
                                title=video_data['title'],
                                performer=info.get('uploader', 'Unknown'),
                                duration=info.get('duration', 0)
                            )
                    else:  # mp4
                        with open(file_path, 'rb') as video:
                            update.effective_chat.send_video(
                                video,
                                caption=video_data['title'],
                                supports_streaming=True,
                                duration=info.get('duration', 0)
                            )

                    self.db.log_download(
                        user_id,
                        info,
                        self.download_manager._calculate_file_hash(file_path),
                        format_type,
                        file_size
                    )

                    os.remove(file_path)
                    success_message = (
                        f"✅ Téléchargé : *{video_data['title']}*\n"
                        f"Format : {'🎵 MP3' if format_type == 'mp3' else '🎥 MP4'}\n"
                        f"Taille : {file_size:.1f}MB"
                    )
                    query.edit_message_text(
                        success_message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return ConversationHandler.END

                except ValueError as e:
                    error_message = (
                        f"❌ *Erreur* : {str(e)}\n"
                        "Essayez une vidéo plus courte ou un format différent."
                    )
                    query.edit_message_text(
                        error_message,
                        parse_mode=ParseMode.MARKDOWN
                    )
                    return ConversationHandler.END

            match = re.match(r'select_video_(\d+)', query.data)
            if not match:
                query.edit_message_text("❌ Sélection invalide.")
                return ConversationHandler.END

            index = int(match.group(1))
            search_results = context.user_data.get('search_results', [])

            if index >= len(search_results):
                query.edit_message_text("❌ Vidéo non trouvée.")
                return ConversationHandler.END

            video = search_results[index]
            context.user_data['selected_video'] = video

            # Afficher les options de format
            keyboard = [
                [
                    InlineKeyboardButton("🎵 MP3 (Audio)", callback_data='format_mp3'),
                    InlineKeyboardButton("🎥 MP4 (Vidéo)", callback_data='format_mp4')
                ],
                [InlineKeyboardButton("🔙 Annuler", callback_data='cancel')]
            ]

            estimated_size = video.get('filesize', 0) / (1024 * 1024)  # Convert to MB
            format_message = (
                f"*{video['title']}*\n\n"
                f"📊 Durée : {int(video['duration'] / 60)}:{int(video['duration'] % 60):02d}\n"
                f"👤 Chaîne : {video['uploader']}\n"
                f"💾 Taille estimée : {estimated_size:.1f} MB\n\n"
                "Choisissez le format de téléchargement :"
            )

            query.edit_message_text(
                format_message,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
            return self.SELECT_FORMAT

        except Exception as e:
            logger.error(f"Erreur de téléchargement : {e}")
            query.edit_message_text(f"❌ Erreur : {str(e)}")
            return ConversationHandler.END

    def show_stats(self, update: Update, context):
        """Display enhanced user statistics"""
        query = update.callback_query
        user_id = update.effective_user.id
        user_language = context.user_data.get('language', 'fr')  # Changed default to French

        stats = self.db.get_user_stats(user_id)
        if stats:
            total_downloads, last_download, unique_downloads, favorites_count, total_size = stats

            stats_text = (
                f"*📊 Vos Statistiques*\n\n"  # Changed to French
                f"• Téléchargements totaux : {total_downloads or 0}\n"
                f"• Téléchargements uniques : {unique_downloads or 0}\n"
                f"• Favoris : {favorites_count or 0}\n"
                f"• Taille totale : {total_size:.1f} MB\n"
                f"• Dernier téléchargement : {last_download or 'Jamais'}"
            )
        else:
            stats_text = "Aucune statistique disponible."  # Changed to French

        if query:
            query.edit_message_text(
                stats_text,
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            update.message.reply_text(stats_text, parse_mode=ParseMode.MARKDOWN)

    def setup_bot(self):
        """Setup bot with enhanced conversation handler"""
        # Utilisation d'un seul updater avec timeout optimisé
        updater = Updater(
            self.config.TELEGRAM_BOT_TOKEN,
            use_context=True,
            request_kwargs={'read_timeout': 30, 'connect_timeout': 30},
            workers=4
        )
        dp = updater.dispatcher

        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', self.start_command),
                CallbackQueryHandler(self.callback_handler)
            ],
            states={
                self.SEARCH_QUERY: [
                    MessageHandler(
                        Filters.text & ~Filters.command,
                        self.search_audio
                    )
                ],
                self.SELECT_RESULT: [
                    CallbackQueryHandler(self.process_download)
                ],
                self.SELECT_FORMAT: [
                    CallbackQueryHandler(self.process_download)
                ]
            },
            fallbacks=[CommandHandler('cancel', self.start_command)]
        )

        dp.add_handler(conv_handler)
        return updater

    def run(self, stop_event=None):
        """Run bot with improved instance management"""
        retries = 0
        max_retries = 3
        retry_delay = 5

        def stop_handler():
            if stop_event and stop_event.is_set():
                logger.info("Arrêt du bot demandé...")
                return True
            return False

        while retries < max_retries and not (stop_event and stop_event.is_set()):
            try:
                logger.info("🚀 Bot YouTube Audio démarré...")
                updater = self.setup_bot()

                # Nettoyage des mises à jour en attente
                updater.start_polling(
                    drop_pending_updates=True,
                    timeout=30,
                    bootstrap_retries=3,
                    poll_interval=2.0,
                    read_latency=4.0,
                    allowed_updates=['message', 'callback_query']
                )

                # Gestion propre de l'arrêt
                if stop_event:
                    while not stop_event.is_set():
                        time.sleep(1)
                    updater.stop()
                    logger.info("Bot arrêté proprement")
                else:
                    updater.idle()
                break

            except telegram_error.Conflict as e:
                logger.error(f"Conflit détecté, tentative de redémarrage: {e}")
                time.sleep(retry_delay * (retries + 1))
                retries += 1
                continue

            except Exception as e:
                logger.error(f"Erreur critique: {e}")
                raise

            finally:
                # Nettoyage des fichiers temporaires
                if hasattr(self, '_tmp_dir') and os.path.exists(self._tmp_dir):
                    try:
                        import shutil
                        shutil.rmtree(self._tmp_dir)
                    except Exception as e:
                        logger.error(f"Erreur lors du nettoyage: {e}")

if __name__ == "__main__":
    bot = YouTubeAudioDownloaderBot()
    bot.run()