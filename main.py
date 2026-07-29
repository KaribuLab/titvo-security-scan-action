import logging
import sys
import time
from datetime import UTC, datetime

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
GITHUB_BRANCH_ARG = 7
SCAN_MODE = 8


def main(
    titvo_api_endpoint,
    titvo_api_key,
    github_token,
    github_repo_name,
    github_commit_sha,
    github_assignee,
    github_branch,
    scan_mode,
):
    # Registrar tiempo de inicio
    start_time = datetime.now(UTC)

    LOGGER.info(
        "Primeros datos: \n - %s,\n - %s,\n - %s,\n - %s",
        f"'{titvo_api_endpoint}'",
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
            "github_branch": github_branch,
            "repository_url": f"https://github.com/{github_repo_name}.git",
            "scan_mode": scan_mode,
        },
    }

    # Realizar la primera petición POST
    LOGGER.info("Iniciando escaneo: %s - %s", github_commit_sha, github_repo_name)
    response = requests.post(
        f"{titvo_api_endpoint}/run-scan", headers=headers, json=payload, timeout=60
    )

    if response.status_code != 200:
        LOGGER.error(
            "Error en la petición inicial: %s - %s", response.status_code, response.text
        )
        sys.exit(1)

    # Obtener scan_id de la respuesta
    response_data = response.json()
    scan_id = response_data.get("scan_id")

    if not scan_id:
        LOGGER.error("No se recibió scan_id en la respuesta")
        sys.exit(1)

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
            sys.exit(1)

        check_data = check_response.json()
        status = check_data.get("status")
        if status == "IN_PROGRESS":
            LOGGER.info("Escaneo en progreso...")

    # Calcular tiempo transcurrido
    end_time = datetime.now(UTC)
    elapsed = end_time - start_time
    hours, remainder = divmod(elapsed.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    milliseconds = elapsed.microseconds // 1000
    elapsed_str = (
        f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}.{milliseconds:03}"
    )

    LOGGER.info("Tiempo de ejecución: %s", elapsed_str)

    result_payload = check_data.get("result")
    if not isinstance(result_payload, dict):
        result_payload = {}

    issue_url = result_payload.get("html_url", "No disponible")
    report_url = result_payload.get("report_url", "No disponible")

    if report_url:
        LOGGER.info(
            "- URL del reporte: %s",
            report_url,
        )
    if issue_url:
        LOGGER.info("- URL del issue: %s", issue_url)

    # Procesar resultado final
    if status == "FAILED" or status == "ERROR":
        LOGGER.error("Escaneo fallido. Estado: %s", status)
        sys.exit(1)
    else:
        LOGGER.info("Escaneo completado con éxito.")
        sys.exit(0)


EXPECTED_ARGS = 8

if __name__ == "__main__":
    # Obtener argumentos por posición
    argc = len(sys.argv)
    if argc < EXPECTED_ARGS + 1:
        LOGGER.error(
            "Argumentos insuficientes: se esperaban %d, se recibieron %d. "
            "Uso: python main.py <titvo_api_endpoint> <titvo_api_key> <github_token> "
            "<github_repo_name> <github_commit_sha> <github_assignee> <github_branch> "
            "<scan_mode>",
            EXPECTED_ARGS,
            argc - 1,
        )
        sys.exit(1)

    # Pad argv con strings vacíos si faltan argumentos
    padded_argv = sys.argv + [''] * (EXPECTED_ARGS + 1 - argc)

    cli_titvo_api_endpoint = padded_argv[TITVO_API_ENDPOINT_ARG]
    cli_titvo_api_key = padded_argv[TITVO_API_KEY_ARG]
    cli_github_token = padded_argv[GITHUB_TOKEN_ARG]
    cli_github_repo_name = padded_argv[GITHUB_REPO_NAME_ARG]
    cli_github_commit_sha = padded_argv[GITHUB_COMMIT_SHA_ARG]
    cli_github_assignee = padded_argv[GITHUB_ASSIGNEE_ARG]
    cli_github_branch = padded_argv[GITHUB_BRANCH_ARG]
    cli_scan_mode = padded_argv[SCAN_MODE] or 'commit'
    # Invocar la función principal con los argumentos
    main(
        cli_titvo_api_endpoint,
        cli_titvo_api_key,
        cli_github_token,
        cli_github_repo_name,
        cli_github_commit_sha,
        cli_github_assignee,
        cli_github_branch,
        cli_scan_mode,
    )
