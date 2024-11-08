# syntax=docker/dockerfile:experimental
FROM python:3.11-slim-bookworm

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Set user and group
ARG USERNAME="appuser"
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
RUN groupadd --gid $USER_GID $USERNAME && \
    useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    chown -R $USER_UID:$USER_GID /home/$USERNAME

USER $USERNAME

# Set working directory
WORKDIR /home/$USERNAME/code

# Copy application code
COPY . .

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user -r requirements.txt
ENV POSTGRES_HOST=postgres \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=db_name \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=password \
    MAILJET_API_KEY=a \
    MAILJET_SECRET_KEY=a


# Collect static files
RUN python manage.py collectstatic --noinput

# Run command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
