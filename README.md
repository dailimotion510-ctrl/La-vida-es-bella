# ToDus Telegram Downloader — Codespaces + Render

Proyecto Python para recibir un enlace `https://s3.todus.cu/...`, resolverlo con `todus-sdk==1.10.2`, descargar el archivo y enviarlo como documento por Telegram.

## Importante sobre el SDK

La documentación del SDK indica que `ToDusClient` es la variante stateless y que sus métodos reciben el token como primer argumento. La API de archivos documenta `get_real_download_url`, `download_file` y `download_file_to_folder`.

Este proyecto usa:

```python
from todus import ToDusClient
client = ToDusClient()
client.download_file_to_folder(TODUS_TOKEN, url, folder, filename)
```

La descarga real todavía debe probarse con un token y un enlace válidos. El proyecto no contiene credenciales.

## 1. Abrir en GitHub Codespaces

1. Sube el contenido de este ZIP a un repositorio de GitHub.
2. Abre el repositorio y pulsa **Code → Codespaces → Create codespace on main**.
3. Codespaces detectará `.devcontainer/devcontainer.json` e instalará las dependencias.
4. Configura los secretos en el entorno de Codespaces o crea un archivo `.env` a partir de `.env.example`.
5. Ejecuta `python main.py`.

### Variables necesarias

- `TELEGRAM_BOT_TOKEN`: token entregado por BotFather.
- `TODUS_TOKEN`: token de sesión de tu cuenta toDus.
- `ALLOWED_USER_IDS`: tu ID numérico de Telegram. Puedes obtenerlo enviando `/id` al bot; mientras no lo añadas, el bot no aceptará enlaces.
- `MAX_UPLOAD_MB`: límite del archivo que se intentará enviar a Telegram (por defecto 49 MB).
- `PORT`: puerto del endpoint de salud (por defecto 8000).

En Codespaces, puedes crear ` .env ` en la raíz con esas variables. El archivo está excluido por `.gitignore`; no lo subas al repositorio.

## 2. Desplegar en Render cuando vuelva a estar disponible

Este repositorio incluye `render.yaml` como Blueprint.

1. En Render, crea un Blueprint desde el repositorio.
2. Render detectará `render.yaml`.
3. Añade los valores secretos `TELEGRAM_BOT_TOKEN`, `TODUS_TOKEN` y `ALLOWED_USER_IDS`.
4. Usa el servicio web y los comandos ya definidos en el Blueprint.

Build command: `pip install -r requirements.txt`

Start command: `python main.py`

El servicio expone `/health`. En el plan gratuito de Render puede suspenderse por inactividad; el bot podría dejar de responder mientras esté suspendido. El disco del servicio también es efímero, pero los archivos descargados se guardan temporalmente y se borran después de enviarse.

## Seguridad

- No pegues tus tokens en el código ni en el chat.
- No subas `.env` a GitHub.
- Mantén `ALLOWED_USER_IDS` configurado para que otros usuarios no puedan usar tu bot.
- Si un token se publica accidentalmente, renuévalo.

## Limitación de Telegram

El límite configurado es conservador (49 MB). El tamaño máximo permitido puede variar según la API y el método de alojamiento de Telegram.
