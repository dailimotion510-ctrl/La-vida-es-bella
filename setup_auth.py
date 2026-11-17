"""
Autenticación inicial de ToDus por SMS.

Ejecutar desde una terminal privada de Codespaces:
    python setup_auth.py

El PIN SMS se solicita oculto y no se envía a Telegram ni se imprime.
El script guarda el token de sesión en .env (ignorado por Git).
"""
import getpass
import os
import re
from pathlib import Path

from dotenv import set_key
from todus import ToDusClient2

ENV_FILE = Path(".env")


def main():
    phone = input("Número de teléfono de ToDus (con código de país): ").strip()
    if not re.fullmatch(r"\+?[0-9]{8,15}", phone):
        raise SystemExit("Formato de teléfono no válido. Vuelve a ejecutar el script.")

    client = ToDusClient2(phone)

    print("\nSolicitando el código SMS a ToDus…")
    request_code = getattr(client, "request_code", None)
    validate_code = getattr(client, "validate_code", None)
    if not callable(request_code) or not callable(validate_code):
        raise SystemExit(
            "La versión instalada del SDK no expone request_code()/validate_code(). "
            "No se ha guardado ningún dato. Comprueba la documentación de la versión 1.10.2."
        )

    request_code()
    pin = getpass.getpass("Introduce el PIN recibido por SMS (entrada oculta): ").strip()
    if not pin:
        raise SystemExit("No se introdujo ningún PIN.")

    client.validate_code(pin)
    client.login()

    session_token = getattr(client, "token", None)
    if not isinstance(session_token, str) or not session_token.strip():
        raise SystemExit(
            "La autenticación terminó, pero el SDK no expuso client.token como texto. "
            "No se guardó nada para evitar guardar una credencial incorrecta."
        )

    set_key(str(ENV_FILE), "TODUS_TOKEN", session_token.strip())
    try:
        os.chmod(ENV_FILE, 0o600)
    except OSError:
        pass

    print("\n✅ Sesión autenticada y guardada en .env.")
    print("No compartas ese archivo ni publiques el token.")
    print("En Render tendrás que copiar el valor de TODUS_TOKEN a la variable de entorno.")
    print("En Codespaces puedes usar el .env local o crear el secreto TODUS_TOKEN.")


if __name__ == "__main__":
    main()
