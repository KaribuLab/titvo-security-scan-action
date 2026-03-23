import json
import logging
import sys
import time
from datetime import datetime

import requests

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

LOGGER = logging.getLogger("titvo-security-scan")

TITVO_API_ENDPOINT_ARG = 1
TITVO_API_KEY_ARG = 2
GITHUB_TOKEN_ARG = 3
GITHUB_REPO_NAME_ARG = 4
GITHUB_COMMIT_SHA_ARG = 5
GITHUB_ASSIGNEE_ARG = 6


def main(
    titvo_api_endpoint,
    titvo_api_key,
    github_token,
    github_repo_name,
    github_commit_sha,
    github_assignee,
):
    # Registrar tiempo de inicio
    start_time = datetime.now()

    LOGGER.info(
        "Primeros datos: \n - %s,\n - %s,\n - %s,\n - %s,\n - %s,\n - %s",
        f"'{titvo_api_endpoint}'",
        f"'{titvo_api_key[0:5]}...{titvo_api_key[-5:]}'",
        f"'{github_token[0:5]}...{github_token[-5:]}'",
        f"'{github_repo_name}'",
        f"'{github_commit_sha}'",
        f"'{github_assignee}'",
    )

    # Preparar datos para la primera petición
    headers = {"x-api-key": titvo_api_key, "Content-Type": "application/json"}

    LOGGER.debug("headers: %s", headers)

    payload = {
        "source": "github",
        "args": {
            "github_assignee": github_assignee,
            "github_token": github_token,
            "github_repo_name": github_repo_name,
            "github_commit_sha": github_commit_sha,
            "repository_url": f"https://github.com/{github_repo_name}.git"
        },
    }

    # Realizar la primera petición POST
    LOGGER.info(
        "Iniciando escaneo: %s", json.dumps(payload).replace(github_token, "********")
    )
    response = requests.post(
        f"{titvo_api_endpoint}/run-scan", headers=headers, json=payload, timeout=60
    )

    if response.status_code != 200:
        LOGGER.error(
            "Error en la petición inicial: %s - %s", response.status_code, response.text
        )
        exit(1)

    # Obtener scan_id de la respuesta
    response_data = response.json()
    scan_id = response_data.get("scan_id")

    if not scan_id:
        LOGGER.error("No se recibió scan_id en la respuesta")
        exit(1)

    LOGGER.info("Scan ID recibido: %s", scan_id)

    # Consultar estado del escaneo
    status = None
    while status not in ["COMPLETED", "FAILED", "ERROR"]:
        # Esperar 60 segundos entre peticiones
        time.sleep(60)

        # Realizar petición POST para verificar estado
        status_payload = {"scan_id": scan_id}

        check_response = requests.post(
            f"{titvo_api_endpoint}/scan-status",
            headers=headers,
            json=status_payload,
            timeout=60,
        )

        if check_response.status_code != 200:
            LOGGER.error(
                "Error al verificar estado: %s - %s",
                check_response.status_code,
                check_response.text,
            )
            exit(1)

        check_data = check_response.json()
        status = check_data.get("status")
        if status == "IN_PROGRESS":
            LOGGER.info("Escaneo en progreso...")

    # Calcular tiempo transcurrido
    end_time = datetime.now()
    elapsed = end_time - start_time
    hours, remainder = divmod(elapsed.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = elapsed.microseconds // 1000
    elapsed_str = (
        f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{milliseconds:03}"
    )

    LOGGER.info("Tiempo de ejecución: %s", elapsed_str)

    # Procesar resultado final
    if status == "FAILED":
        issue_url = check_data.get("result").get("issue_url", "No disponible")
        LOGGER.error(
            "Escaneo fallido. Estado: %s, URL del issue: %s", status, issue_url
        )
        exit(1)
    else:
        LOGGER.info("Escaneo completado con éxito. Estado: %s", status)


if __name__ == "__main__":
    # Verificar que se proporcionen todos los argumentos necesarios
    if len(sys.argv) != GITHUB_ASSIGNEE_ARG + 1:
        LOGGER.error(
            "Uso: python main.py <titvo_api_endpoint> <titvo_api_key> <github_token> "
            "<github_repo_name> <github_commit_sha> <github_assignee>"
        )
        sys.exit(1)

    # Obtener argumentos por posición
    cli_titvo_api_endpoint = sys.argv[TITVO_API_ENDPOINT_ARG]
    cli_titvo_api_key = sys.argv[TITVO_API_KEY_ARG]
    cli_github_token = sys.argv[GITHUB_TOKEN_ARG]
    cli_github_repo_name = sys.argv[GITHUB_REPO_NAME_ARG]
    cli_github_commit_sha = sys.argv[GITHUB_COMMIT_SHA_ARG]
    cli_github_assignee = sys.argv[GITHUB_ASSIGNEE_ARG]

    # Invocar la función principal con los argumentos
    main(
        cli_titvo_api_endpoint,
        cli_titvo_api_key,
        cli_github_token,
        cli_github_repo_name,
        cli_github_commit_sha,
        cli_github_assignee,
    )
