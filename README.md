# Titvo Security Scan Action

Este repositorio contiene un script de Python que permite ejecutar escaneos de seguridad usando la API de Titvo. Está diseñado para integrarse con GitHub y realizar análisis de seguridad sobre repositorios específicos.

## Descripción

La acción realiza las siguientes operaciones:
- Inicia un escaneo de seguridad en un repositorio de GitHub
- Consulta periódicamente el estado del escaneo hasta que se complete
- Reporta el resultado del escaneo (éxito o fallo)
- En caso de fallo, proporciona la URL del issue creado

## Requisitos

- Python 3.x
- Acceso a la API de Titvo (clave de API)
- Token de GitHub con permisos adecuados

## Uso

```bash
python main.py <titvo_api_key> <github_token> <github_repo_name> <github_commit_sha> <github_assignee>
```

### Parámetros

- `titvo_api_key`: Clave de API para autenticarse con el servicio de Titvo
- `github_token`: Token de acceso a GitHub para acceder al repositorio
- `github_repo_name`: Nombre del repositorio de GitHub a escanear (formato: usuario/repositorio)
- `github_commit_sha`: Hash SHA del commit a analizar
- `github_assignee`: Usuario de GitHub al que se asignarán los issues en caso de encontrar problemas

## Funcionamiento

1. El script inicia una solicitud de escaneo a la API de Titvo
2. Recibe un ID de escaneo
3. Consulta el estado del escaneo cada 60 segundos hasta que se complete o falle
4. Registra el tiempo total de ejecución
5. Muestra el resultado final del escaneo

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
          python main.py "${{ secrets.TITVO_API_KEY }}" "${{ secrets.GITHUB_TOKEN }}" "${{ github.repository }}" "${{ github.sha }}" "${{ github.actor }}"
```

## Licencia

Este proyecto está bajo la licencia Apache 2.0. Consulte el archivo [LICENSE](LICENSE) para más detalles. 