"""Environment validation; no production demo credentials."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).with_name('.env'), override=False)

def validate_environment():
    if os.getenv('ENV', 'development').lower() != 'production':
        return
    for key in ('CASO16_SECRET_KEY', 'POSTGRES_PASSWORD', 'DATABASE_URL'):
        value = os.getenv(key, '')
        if not value or any(marker in value.lower() for marker in ('demo', 'change-me', 'super-secret', 'changeme')):
            raise RuntimeError(f'{key} debe configurarse sin valores de demostración en producción')
    if len(os.environ['CASO16_SECRET_KEY']) < 32:
        raise RuntimeError('CASO16_SECRET_KEY requiere al menos 32 caracteres')

validate_environment()
