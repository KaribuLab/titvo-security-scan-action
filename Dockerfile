FROM python:3.12.8-alpine3.21

WORKDIR /app

# Copiar archivos del proyecto
COPY ./ /app
COPY requirements.txt /app
COPY entrypoint.sh /app

# Crear usuario no privilegiado para seguridad
RUN adduser -D -u 1000 titvo

# Asignar permisos al usuario
RUN chown -R titvo:titvo /app
RUN chmod +x /app/entrypoint.sh

# Instalar dependencias
RUN pip install -r requirements.txt

# Cambiar al usuario no privilegiado
USER titvo

# Usar entrypoint en lugar de CMD
ENTRYPOINT ["/app/entrypoint.sh"]