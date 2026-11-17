import asyncio
import logging
import os
import re
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, unquote

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from todus import ToDusClient

load_dotenv()

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
log = logging.getLogger("todus-telegram-bot")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TODUS_TOKEN = os.getenv("TODUS_TOKEN", "").strip()
ALLOWED_USER_IDS = {
    item.strip()
    for item in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if item.strip()
}
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "49"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Falta TELEGRAM_BOT_TOKEN.")
if not TODUS_TOKEN:
    raise RuntimeError("Falta TODUS_TOKEN.")

# ToDusClient es la variante stateless del SDK. En esta variante,
# los métodos de archivos reciben el token de sesión como primer argumento.
todus_client = ToDusClient()
download_lock = threading.Lock()


def is_allowed(update: Update) -> bool:
    user = update.effective_user
    return bool(user and str(user.id) in ALLOWED_USER_IDS)


def extract_todus_url(text: str) -> str | None:
    match = re.search(r"https?://[^\s<>()]+", text or "")
    if not match:
        return None

    url = match.group(0).rstrip(".,;!?)]}\"'")
    parsed = urlparse(url)

    # Solo aceptar enlaces del dominio de archivos de toDus.
    if parsed.scheme != "https" or parsed.hostname != "s3.todus.cu":
        return None
    return url


def safe_filename(url: str) -> str:
    raw = unquote(Path(urlparse(url).path).name) or "archivo_todus"
    raw = re.sub(r"[^A-Za-z0-9._() -]", "_", raw).strip(" .")
    return (raw or "archivo_todus")[:120]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_message.reply_text(
        "Hola. Envíame /id para conocer tu ID de Telegram. "
        "El administrador debe añadirlo a ALLOWED_USER_IDS antes de que puedas descargar."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update):
        await update.effective_message.reply_text("No estás autorizado. Usa /id y pide al administrador que te añada.")
        return
    await update.effective_message.reply_text(
        "Envíame un enlace HTTPS de https://s3.todus.cu/ y lo intentaré descargar "
        "con tu sesión de toDus para devolvértelo como documento.\n"
        f"Límite configurado: {MAX_UPLOAD_MB} MB."
    )


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user:
        await update.effective_message.reply_text(f"Tu ID de Telegram es: {user.id}")


def download_with_sdk(token: str, url: str, folder: str, filename: str):
    # ToDus SDK: resuelve la URL real mediante XMPP y descarga el archivo.
    with download_lock:
        return todus_client.download_file_to_folder(token, url, folder, filename)


def unpack_download_result(result, folder: str, filename: str) -> str:
    """Normaliza el resultado documentado como tupla o una ruta devuelta."""
    candidates = []

    if isinstance(result, (tuple, list)):
        for item in result:
            if isinstance(item, (str, os.PathLike)):
                candidates.append(os.fspath(item))
    elif isinstance(result, (str, os.PathLike)):
        candidates.append(os.fspath(result))

    # Algunas versiones devuelven tamaño y ruta; otras pueden devolver solo tamaño.
    candidates.extend([
        os.path.join(folder, filename),
        os.path.join(folder, Path(filename).name),
    ])

    for candidate in candidates:
        if os.path.isfile(candidate):
            return candidate

    # Si el SDK guarda el archivo con otro nombre, detectar el único archivo creado.
    files = [
        os.path.join(folder, name)
        for name in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, name))
    ]
    if len(files) == 1:
        return files[0]

    raise RuntimeError(f"No se pudo localizar el archivo descargado. Resultado del SDK: {result!r}")


async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.effective_message
    if not message:
        return

    if message.chat.type != "private":
        await message.reply_text("Por seguridad, envíame el enlace en un chat privado con el bot.")
        return

    if not is_allowed(update):
        await message.reply_text("No estás autorizado. Usa /id y pide al administrador que te añada.")
        return

    url = extract_todus_url(message.text or message.caption or "")
    if not url:
        await message.reply_text(
            "No reconozco el enlace. Debe ser HTTPS y pertenecer a s3.todus.cu."
        )
        return

    filename = safe_filename(url)
    status = await message.reply_text("⏳ Resolviendo el enlace con toDus y descargando el archivo…")

    try:
        with tempfile.TemporaryDirectory(prefix="todus_dl_") as folder:
            result = await asyncio.to_thread(
                download_with_sdk, TODUS_TOKEN, url, folder, filename
            )
            file_path = unpack_download_result(result, folder, filename)
            actual_size = os.path.getsize(file_path)

            if actual_size <= 0:
                raise RuntimeError("El archivo descargado está vacío.")
            if actual_size > MAX_UPLOAD_BYTES:
                await status.edit_text(
                    f"El archivo pesa {actual_size / (1024 * 1024):.1f} MB. "
                    f"El límite configurado para Telegram es {MAX_UPLOAD_MB} MB."
                )
                return

            await status.edit_text("✅ Descarga terminada. Enviando el archivo a Telegram…")
            with open(file_path, "rb") as stream:
                await message.reply_document(
                    document=stream,
                    filename=Path(file_path).name,
                    caption="Archivo original descargado desde toDus",
                    read_timeout=180,
                    write_timeout=180,
                    connect_timeout=30,
                    pool_timeout=30,
                )
        await status.delete()
    except Exception:
        log.exception("Error procesando enlace toDus")
        try:
            await status.edit_text(
                "❌ No se pudo completar la descarga. Comprueba que el enlace siga activo "
                "y que TODUS_TOKEN sea válido. Revisa los logs para ver el error técnico."
            )
        except Exception:
            pass


class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/health"):
            self.send_response(404)
            self.end_headers()
            return
        body = b"ok"
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        log.info("health: " + fmt, *args)


def start_health_server():
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log.info("Health endpoint activo en el puerto %s", port)


def main():
    start_health_server()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(MessageHandler(filters.TEXT | filters.CAPTION, handle_link))

    log.info("Bot iniciado. Usuarios autorizados configurados: %s", len(ALLOWED_USER_IDS))
    if not ALLOWED_USER_IDS:
        log.warning("ALLOWED_USER_IDS está vacío: solo /id y /start funcionarán.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
