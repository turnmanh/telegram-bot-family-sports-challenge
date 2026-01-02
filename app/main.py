import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from core.config import settings
from app.routes import router
from app.bot import create_bot_application

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize bot
    logger.info("Starting up Telegram Bot...")
    bot_app = create_bot_application()
    await bot_app.initialize()
    await bot_app.start()
    
    # Ensure no webhook is active before polling
    logger.info("Deleting any existing webhook...")
    await bot_app.bot.delete_webhook(drop_pending_updates=True)
    
    logger.info("Starting polling...")
    await bot_app.updater.start_polling()
    
    # Store bot_app in state
    app.state.bot_app = bot_app
    
    yield
    
    # Shutdown
    logger.info("Shutting down...")
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "Telegram Sport Challenge Bot is running"}
