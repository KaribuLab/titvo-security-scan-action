# Titvo Security Scan Action

Este repositorio contiene un script de Python que permite ejecutar escaneos de seguridad usando la API de Titvo. Está diseñado para integrarse con GitHub y realizar análisis de seguridad sobre repositorios específicos.

## Descripción

La acción realiza las siguientes operaciones:
- Inicia un escaneo de seguridad en un repositorio de GitHub
- Consulta periódicamente el estado del escaneo hasta que se complete
- Reporta el resultado del escaneo (éxito o fallo)
- Muestra las URLs del issue y del reporte devueltas por la API, también con advertencias

## Requisitos

- Python 3.x
- Acceso a la API de Titvo (clave de API)
- Token de GitHub con permisos adecuados

## Uso

```bash
python main.py <titvo_api_endpoint> <titvo_api_key> <github_token> <github_repo_name> <github_commit_sha> <github_assignee> <github_branch> <scan_mode>
```

### Parámetros

- `titvo_api_endpoint`: URL base de la API de Titvo (por ejemplo `https://api.ejemplo.com`). El script concatena las rutas `/run-scan` y `/scan-status` a esta URL
- `titvo_api_key`: Clave de API para autenticarse con el servicio de Titvo
- `github_token`: Token de acceso a GitHub para acceder al repositorio
- `github_repo_name`: Nombre del repositorio de GitHub a escanear (formato: usuario/repositorio)
- `github_commit_sha`: Hash SHA del commit a analizar
- `github_assignee`: Usuario de GitHub al que se asignarán los issues en caso de encontrar problemas
- `github_branch`: Nombre de la rama (branch) a escanear
- `scan_mode`: Indica si el escaneo debe ser completo (`full`) o por commit (`commit`). Por defecto es `commit`.

## Funcionamiento

1. El script inicia una solicitud de escaneo a la API de Titvo
2. Recibe un ID de escaneo
3. Consulta el estado del escaneo cada 60 segundos hasta que se complete o falle
4. Registra el tiempo total de ejecución
5. Muestra el resultado final del escaneo

El `status` principal indica el estado de ejecución. Si es `COMPLETED` y
`result.status` es `WARNING`, la acción muestra una advertencia informativa y
termina correctamente (código 0). Los enlaces `result.html_url` (issue) y
`result.report_url` (reporte) se muestran independientemente del estado del
resultado, siempre que la API los proporcione. La acción no crea el issue ni
el reporte: los genera el servicio de escaneo. `code_insights_url` de Bitbucket
no es una URL de issue de GitHub.

## Ejemplo de integración con GitHub Actions

```yaml
name: Titvo Security Scan

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.x'
          
      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install requests
          
      - name: Run Titvo Security Scan
        run: |
          python main.py "${{ vars.TITVO_API_ENDPOINT }}" "${{ secrets.TITVO_API_KEY }}" "${{ secrets.GITHUB_TOKEN }}" "${{ github.repository }}" "${{ github.sha }}" "${{ github.actor }}" "${{ github.ref_name }}" "full"
```

Sustituye `vars.TITVO_API_ENDPOINT` por la variable o secreto donde guardes la URL base de la API, o un valor literal acorde a tu entorno Titvo.

### Uso como acción de GitHub (`action.yaml`)

Si usas esta acción con `uses:`, pasa el endpoint con el input `titvo_api_endpoint` (primer argumento que recibe el contenedor):

```yaml
- uses: ./
  with:
    titvo_api_endpoint: ${{ vars.TITVO_API_ENDPOINT }}
    titvo_api_key: ${{ secrets.TITVO_API_KEY }}
    github_token: ${{ secrets.GITHUB_TOKEN }}
    github_repo_name: ${{ github.repository }}
    github_commit_sha: ${{ github.sha }}
    github_assignee: ${{ github.actor }}
    github_branch: ${{ github.ref_name }}
    scan_mode: full
```

### Continuar el pipeline aunque Titvo falle

Configura el input `no_fail: 'true'` para que la acción termine con código 0
aunque el escaneo termine en `FAILED` o `ERROR`, o haya errores de comunicación
o respuesta de la API de Titvo. Por defecto es `'false'`: esos fallos terminan
con código 1.

```yaml
  with:
    # ...inputs de Titvo...
    no_fail: 'true'
```

El fallo real se conserva en los logs y en la notificación de Slack, incluidos
los enlaces al reporte y al issue disponibles. Solo cambia el código de salida;
no convierte el resultado del escaneo en exitoso. Los errores de configuración
de Slack siguen siendo errores. Para ejecutar Python directamente, utiliza
la variable de entorno `NO_FAIL=true`.

### Notificaciones de fallo a Slack

Opcionalmente configura **uno** de `slack_bot_token` o `slack_webhook_url`.
`slack_channel` es **obligatorio y válido solo con `slack_bot_token`**;
no debe indicarse con webhook. Sin estos inputs, las notificaciones están desactivadas.
Una configuración incompleta o ambos métodos a la vez produce un error de configuración.

Con bot token:

```yaml
- uses: ./
  with:
    titvo_api_endpoint: ${{ vars.TITVO_API_ENDPOINT }}
    titvo_api_key: ${{ secrets.TITVO_API_KEY }}
    github_token: ${{ secrets.GITHUB_TOKEN }}
    github_repo_name: ${{ github.repository }}
    slack_bot_token: ${{ secrets.SLACK_BOT_TOKEN }}
    slack_channel: C0123456789
```

El bot necesita el scope `chat:write` y acceso al canal (invítalo al canal,
especialmente si es privado). Usa el ID del canal como `slack_channel`.

Para usar un incoming webhook, reemplaza `slack_bot_token` por:

```yaml
    slack_webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

Elimina también `slack_channel` del ejemplo al usar webhook.

**Los webhooks de Slack tienen un canal fijo:** publican en el canal vinculado
al crear el webhook. Slack no permite cambiar ese destino en cada envío.
Usa bot token si necesitas seleccionar el destino desde el action.

Se envía un único mensaje con encabezado **🚨 FALLA** y indicador rojo cuando
el escaneo termina en `FAILED` o `ERROR`, o falla la comunicación/respuesta de
la API. `COMPLETED`, incluido `result.status: WARNING`, no notifica.
El mensaje incluye repositorio, SHA y enlace al commit, rama, actor, action,
workflow, job, intento y enlace a la ejecución, además de los enlaces al reporte
y al issue devueltos por Titvo. Si el fallo ocurre antes de generarlos, aparecen
como «No disponible». Los errores de Slack se registran sin exponer credenciales
y conservan el código de fallo del escaneo.

Al ejecutar Python directamente, configura `SLACK_WEBHOOK_URL`, o bien
`SLACK_BOT_TOKEN` junto con `SLACK_CHANNEL` (solo válido para bot token).
El contexto de la ejecución se obtiene
de las variables `GITHUB_*` que GitHub Actions proporciona automáticamente.

## Licencia

Este proyecto está bajo la licencia Apache 2.0. Consulte el archivo [LICENSE](LICENSE) para más detalles.
