# ToDus Telegram Downloader — Codespaces + Render

Este proyecto recibe enlaces `https://s3.todus.cu/...`, los procesa con `todus-sdk==1.10.2` y devuelve el archivo como documento por Telegram.

## 1. Preparar la sesión ToDus mediante SMS (solo una vez)

La autenticación SMS se hace desde una terminal privada de GitHub Codespaces, no desde el chat de Telegram:

```bash
pip install -r requirements.txt
python setup_auth.py
```

El programa pide tu número, solicita el SMS, recibe el PIN de forma oculta y guarda el token de sesión en `.env`. No escribas el PIN ni el token en el código ni en mensajes de chat. El archivo `.env` está excluido de Git.

**Nota:** el flujo usa `ToDusClient2.request_code()`, `validate_code()` y `client.token` del SDK. Si la versión instalada no ofrece esos métodos o propiedades, el script se detiene sin guardar una credencial; no intenta métodos alternativos ni omite la confirmación SMS.

## 2. Configurar Telegram

- `TELEGRAM_BOT_TOKEN`: token creado con BotFather.
- `TODUS_TOKEN`: token de sesión que `setup_auth.py` guarda en `.env`.
- `ALLOWED_USER_IDS`: tu ID numérico de Telegram. Cuando el bot esté iniciado, envíale `/id`, copia el número y configúralo aquí.
- `MAX_UPLOAD_MB`: límite de tamaño (por defecto 49 MB).

Para probar en Codespaces, crea `.env` a partir de `.env.example`, completa los valores y ejecuta:

```bash
python main.py
```

Puedes dejar `TODUS_TOKEN` en el `.env` local de Codespaces o guardarlo como secreto de Codespaces. Si el Codespace ya estaba abierto al crear el secreto, reinícialo.

## 3. Render

El archivo `render.yaml` deja preparados los comandos:

- Build: `pip install -r requirements.txt`
- Start: `python main.py`

Cuando Render esté disponible, crea el servicio desde el repositorio y añade en Environment las variables `TELEGRAM_BOT_TOKEN`, `TODUS_TOKEN` y `ALLOWED_USER_IDS`. Codespaces y Render tienen variables separadas: el `.env` de Codespaces no se copia automáticamente a Render.

El plan gratuito puede suspender el servicio por inactividad. El endpoint `/health` responde para la comprobación del servicio.

## Seguridad y límites

- Nunca compartas el PIN SMS, el token de sesión ni el archivo `.env`.
- No subas `.env` a GitHub.
- Configura `ALLOWED_USER_IDS` para limitar el uso a tu cuenta.
- Si una credencial se expone, revoca la sesión desde las opciones disponibles de ToDus y autentícate de nuevo.
- La descarga real requiere una prueba con tu cuenta y un enlace válido. El proyecto no incluye credenciales ni puede garantizar la disponibilidad de los servidores de ToDus o Telegram.
