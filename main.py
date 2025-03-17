import logging
import time
import sys
from datetime import datetime
import requests

BASE_URL = "https://4psk9bcsud.execute-api.us-east-1.amazonaws.com/v1"

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

LOGGER = logging.getLogger("titvo-security-scan")


def main(
    titvo_api_key, github_token, github_repo_name, github_commit_sha, github_assignee
):
    # Registrar tiempo de inicio
    start_time = datetime.now()

    LOGGER.info(
        "Primeros datos: %s, %s, %s, %s, %s",
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
        "github_token": github_token,
        "github_repo_name": github_repo_name,
        "github_commit_sha": github_commit_sha,
        "github_assignee": github_assignee,
    }

    # Realizar la primera petición POST
    LOGGER.info("Iniciando escaneo...")
    response = requests.post(
        f"{BASE_URL}/run-scan", headers=headers, json=payload, timeout=60
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
    while status not in ["COMPLETED", "FAILED"]:
        # Esperar 60 segundos entre peticiones
        time.sleep(60)

        # Realizar petición POST para verificar estado
        status_payload = {"scan_id": scan_id}

        check_response = requests.post(
            f"{BASE_URL}/scan-status", headers=headers, json=status_payload, timeout=60
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
        issue_url = check_data.get("issue_url", "No disponible")
        LOGGER.error(
            "Escaneo fallido. Estado: %s, URL del issue: %s", status, issue_url
        )
        exit(1)
    else:
        LOGGER.info("Escaneo completado con éxito. Estado: %s", status)


if __name__ == "__main__":
    # Verificar que se proporcionen todos los argumentos necesarios
    if len(sys.argv) != 6:
        LOGGER.error(
            "Uso: python main.py <titvo_api_key> <github_token> "
            "<github_repo_name> <github_commit_sha> <github_assignee>"
        )
        sys.exit(1)

    # Obtener argumentos por posición
    cli_titvo_api_key = sys.argv[1]
    cli_github_token = sys.argv[2]
    cli_github_repo_name = sys.argv[3]
    cli_github_commit_sha = sys.argv[4]
    cli_github_assignee = sys.argv[5]

    # Invocar la función principal con los argumentos
    main(
        cli_titvo_api_key,
        cli_github_token,
        cli_github_repo_name,
        cli_github_commit_sha,
        cli_github_assignee,
    )
