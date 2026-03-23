FROM python:3.13-alpine3.21

WORKDIR /app

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copiar archivos del proyecto
COPY ./ /app
COPY pyproject.toml /app
COPY entrypoint.sh /app

# Crear usuario no privilegiado para seguridad
RUN adduser -D -u 1000 titvo

# Asignar permisos al usuario
RUN chown -R titvo:titvo /app
RUN chmod +x /app/entrypoint.sh

# Instalar dependencias con uv
RUN uv pip install --system -e .

# Cambiar al usuario no privilegiado
USER titvo

# Usar entrypoint en lugar de CMD
ENTRYPOINT ["/app/entrypoint.sh"]