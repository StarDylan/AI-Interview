import ssl
import logging
from pathlib import Path
from config.settings import CERT_FILE, KEY_FILE

logger = logging.getLogger(__name__)

def create_ssl_context() -> ssl.SSLContext:
    """Create SSL context for secure WebSocket connections"""
    try:
        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        
        # Verify certificate files exist
        if not CERT_FILE.exists():
            raise FileNotFoundError(f"Certificate file not found: {CERT_FILE}")
        
        if not KEY_FILE.exists():
            raise FileNotFoundError(f"Key file not found: {KEY_FILE}")
        
        ssl_context.load_cert_chain(certfile=str(CERT_FILE), keyfile=str(KEY_FILE))
        
        logger.info(f"SSL context created with cert: {CERT_FILE} and key: {KEY_FILE}")
        return ssl_context
        
    except Exception as e:
        logger.error(f"Failed to create SSL context: {e}")
        raise