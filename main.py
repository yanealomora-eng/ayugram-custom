#!/usr/bin/env python3
"""
jirgram - Advanced Telegram Client
Based on TDLib with ghost mode, anti-delete, and customization features
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

try:
    from telegram.client import Telegram
    from telegram.text import Spoiler, Bold, Italic
except ImportError:
    print("Error: python-telegram library not installed")
    print("Install it with: pip install python-telegram")
    sys.exit(1)

# Import local modules
try:
    from modules.database import MessageDatabase
    from modules.ghost_mode import GhostModeHandler
    from modules.anti_delete import AntiDeleteHandler
    from modules.message_history import MessageHistoryHandler
    import config
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure you have:")
    print("  1. Created config.py from config.example.py")
    print("  2. Created the 'modules' folder with required files")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class JirgramClient:
    """
    Main Telegram client with advanced features:
    - Ghost Mode: Hide online status, typing, read receipts
    - Anti-Delete: Save deleted messages
    - Message History: Track edits
    - Customization: Themes, filters, automation
    """

    def __init__(self):
        # Load configuration
        self.api_id = config.API_ID
        self.api_hash = config.API_HASH
        self.phone = config.PHONE
        self.encryption_key = config.ENCRYPTION_KEY

        # Feature flags from config
        self.ghost_mode_enabled = getattr(config, 'GHOST_MODE', True)
        self.hide_online = getattr(config, 'HIDE_ONLINE', True)
        self.hide_typing = getattr(config, 'HIDE_TYPING', True)
        self.hide_read = getattr(config, 'HIDE_READ', True)
        self.save_deleted = getattr(config, 'SAVE_DELETED_MESSAGES', True)

        # Initialize components
        self.db = MessageDatabase()
        self.ghost_handler = GhostModeHandler(self.hide_online, self.hide_typing, self.hide_read)
        self.anti_delete_handler = AntiDeleteHandler(self.db)
        self.history_handler = MessageHistoryHandler(self.db)

        self.tg = None
        self.is_running = False

    def init_client(self):
        """Initialize TDLib Telegram client"""
        logger.info("Initializing Telegram client...")

        self.tg = Telegram(
            api_id=self.api_id,
            api_hash=self.api_hash,
            phone=self.phone,
            database_encryption_key=self.encryption_key,
            files_directory='tdlib_data',
        )

        # Register event handlers
        self._register_handlers()

        logger.info("Client initialized successfully")

    def _register_handlers(self):
        """Register all event handlers"""
        self.tg.add_message_handler(self.handle_new_message)
        self.tg.add_update_handler('updateDeleteMessages', self.handle_delete_message)
        self.tg.add_update_handler('updateMessageEdited', self.handle_edit_message)

        if self.ghost_mode_enabled:
            self.tg.add_update_handler('updateUserStatus', self.ghost_handler.handle_status_update)

    async def handle_new_message(self, update):
        """Handle incoming messages"""
        if update.get('@type') == 'updateNewMessage':
            message = update.get('message', {})

            # Save message for anti-delete
            if self.save_deleted:
                await self.anti_delete_handler.save_message(message)

            # Log message (optional, can be disabled)
            chat_id = message.get('chat_id')
            text = self._extract_text(message)
            logger.debug(f"New message in chat {chat_id}: {text[:50]}")

    async def handle_delete_message(self, update):
        """Handle message deletion"""
        if self.save_deleted:
            await self.anti_delete_handler.handle_deletion(update)

    async def handle_edit_message(self, update):
        """Handle message edits"""
        await self.history_handler.handle_edit(update, self.tg)

    def _extract_text(self, message: dict) -> str:
        """Extract text content from message"""
        content = message.get('content', {})

        if content.get('@type') == 'messageText':
            return content.get('text', {}).get('text', '')

        return f"[{content.get('@type', 'Unknown')}]"

    async def send_message(self, chat_id: int, text: str, silent: bool = False):
        """Send a message"""
        result = await self.tg.call_method('sendMessage', {
            'chat_id': chat_id,
            'input_message_content': {
                '@type': 'inputMessageText',
                'text': {
                    '@type': 'formattedText',
                    'text': text
                }
            },
            'disable_notification': silent or self.ghost_mode_enabled
        })

        return result

    async def get_deleted_messages(self, chat_id: int):
        """Get all deleted messages from a chat"""
        return await self.anti_delete_handler.get_deleted_messages(chat_id)

    async def get_message_history(self, chat_id: int, message_id: int):
        """Get edit history of a message"""
        return await self.history_handler.get_edit_history(chat_id, message_id)

    def run(self):
        """Start the client"""
        logger.info("="*70)
        logger.info("🔥 jirgram Client Starting...")
        logger.info("="*70)
        logger.info(f"👻 Ghost Mode: {self.ghost_mode_enabled}")
        logger.info(f"   - Hide Online: {self.hide_online}")
        logger.info(f"   - Hide Typing: {self.hide_typing}")
        logger.info(f"   - Hide Read: {self.hide_read}")
        logger.info(f"🛡️  Anti-Delete: {self.save_deleted}")
        logger.info("="*70)

        self.is_running = True
        self.tg.login()
        self.tg.idle()

    def stop(self):
        """Stop the client"""
        logger.info("Stopping jirgram client...")
        self.is_running = False
        if self.tg:
            self.tg.stop()


def check_configuration():
    """
    Verify that configuration is properly set up
    """
    try:
        import config
        if config.API_ID == 'YOUR_API_ID' or not config.API_ID:
            return False
        return True
    except ImportError:
        return False


def print_setup_instructions():
    """
    Print setup instructions for first-time users
    """
    print("\n" + "="*70)
    print("⚠️  CONFIGURATION REQUIRED")
    print("="*70)
    print("\nYou need to configure your Telegram API credentials:")
    print("\n1. Copy the example config:")
    print("   cp config.example.py config.py")
    print("\n2. Get your API credentials:")
    print("   - Visit: https://my.telegram.org")
    print("   - Log in with your phone number")
    print("   - Go to 'API development tools'")
    print("   - Create a new application")
    print("   - Copy your api_id and api_hash")
    print("\n3. Edit config.py and set:")
    print("   - API_ID = 'your_api_id'")
    print("   - API_HASH = 'your_api_hash'")
    print("   - PHONE = '+1234567890'  # Your phone number")
    print("   - ENCRYPTION_KEY = 'secure_password'  # Any secure password")
    print("\n4. Configure features (Ghost Mode, Anti-Delete, etc.)")
    print("\n5. Run again: python main.py")
    print("\n" + "="*70 + "\n")


def main():
    """
    Main entry point
    """
    # Check if config is set up
    if not check_configuration():
        print_setup_instructions()
        return

    # Initialize and run client
    try:
        client = JirgramClient()
        client.init_client()
        client.run()
    except KeyboardInterrupt:
        logger.info("\nReceived interrupt signal, shutting down...")
        if 'client' in locals():
            client.stop()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
