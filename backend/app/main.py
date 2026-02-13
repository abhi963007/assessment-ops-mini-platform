import logging
import time
import uuid

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.structured_log import setup_logging, request_context, get_logger
from app.routes import ingest, attempts, leaderboard, upload

# Initialize structured logging
setup_logging(settings.LOG_LEVEL)
logger = get_logger('http')

app = FastAPI(
    title='Assessment Ops Mini Platform',
    description='Ingest, deduplicate, score, and analyze student assessment attempts.',
    version='1.0.0',
)

# CORS middleware for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)


@app.middleware('http')
async def structured_logging_middleware(request: Request, call_next):
    """
    Middleware that:
    1. Generates a unique request_id per request
    2. Sets request context for structured logging
    3. Logs request start/end with latency
    """
    req_id = str(uuid.uuid4())
    start_time = time.time()

    # Set context for all logs within this request
    ctx = {
        'request_id': req_id,
        'ip': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent'),
        'query_params': dict(request.query_params) if request.query_params else None,
    }
    token = request_context.set(ctx)

    logger.log_with_data(
        logging.INFO,
        f'Request started: {request.method} {request.url.path}',
        extra_data={
            'method': request.method,
            'path': request.url.path,
        },
    )

    try:
        response = await call_next(request)

        duration_ms = round((time.time() - start_time) * 1000, 2)

        logger.log_with_data(
            logging.INFO,
            f'Request completed: {request.method} {request.url.path} '
            f'-> {response.status_code} ({duration_ms}ms)',
            extra_data={
                'method': request.method,
                'path': request.url.path,
                'status_code': response.status_code,
                'duration_ms': duration_ms,
            },
        )

        response.headers['X-Request-ID'] = req_id
        return response

    except Exception as e:
        duration_ms = round((time.time() - start_time) * 1000, 2)
        logger.log_with_data(
            logging.ERROR,
            f'Request failed: {request.method} {request.url.path} -> {e}',
            extra_data={
                'method': request.method,
                'path': request.url.path,
                'error': str(e),
                'duration_ms': duration_ms,
            },
        )
        raise
    finally:
        request_context.reset(token)


# Register routers
app.include_router(ingest.router, tags=['Ingest'])
app.include_router(attempts.router, tags=['Attempts'])
app.include_router(leaderboard.router, tags=['Leaderboard'])
app.include_router(upload.router, tags=['Upload'])


@app.get('/api/health')
def health_check():
    """Health check endpoint."""
    return {'status': 'ok', 'service': 'assessment-ops'}
