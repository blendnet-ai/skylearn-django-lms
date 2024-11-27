# syntax=docker/dockerfile:experimental
FROM python:3.11-slim-bookworm

# Standard recommendation for Python Docker Images
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MAKEFLAGS=-j2


ARG USERNAME="appuser"
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# Create the user
# Ref: https://code.visualstudio.com/remote/advancedcontainers/add-nonroot-user
# We install all dependencies together as the later half of the image lacks root access
RUN apt-get update && apt-get dist-upgrade --yes
RUN apt-get install build-essential nasm yasm libx264-dev libx265-dev libvpx-dev libmp3lame-dev libopus-dev wget --yes
RUN mkdir ~/ffmpeg && cd ~/ffmpeg && wget https://ffmpeg.org/releases/ffmpeg-6.1.1.tar.xz && tar -xf ffmpeg-6.1.1.tar.xz
RUN cd ~/ffmpeg/ffmpeg-6.1.1 && chmod +x configure && ./configure && make install

RUN apt-get install --yes build-essential python3-dev libpq-dev git openssh-client && \
    apt-get autoremove --yes && apt-get autoclean --yes && apt-get clean

RUN echo "--> $USERNAME $USER_UID $USER_GID"

RUN groupadd --gid 1000 $USERNAME \
    && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME && \
    chown -R $USER_UID:$USER_GID /home/$USERNAME

# RUN --mount=type=ssh mkdir -m 0600 ~/.ssh && \
#     ssh-keyscan github.com >> ~/.ssh/known_hosts && \
#     pip install git+ssh://git@github.com/blendnet-ai/pip-module.git#pip-module

USER $USERNAME
ENV PATH "$PATH:/home/$USERNAME/.local/bin"

# Copy application code
COPY  --chown=$USER_UID:$USER_GID . /home/$USERNAME/code/
ENV PYTHONPATH=/home/$USERNAME/code/
# Install dependencies
COPY --chown=$USER_UID:$USER_GID requirements.txt /home/$USERNAME/code/
COPY --chown=$USER_UID:$USER_GID download_nltk_punk.py /home/$USERNAME/code/
WORKDIR /home/$USERNAME/code
#Ignoring 71720-2 for Litellm. TODO: Fix as soon as possible
RUN pip install safety && safety check -r /home/$USERNAME/code/requirements.txt --ignore 71720 --ignore 71721 --ignore 71722 --ignore 73564
RUN pip install -r /home/$USERNAME/code/requirements.txt
RUN python download_nltk_punk.py
RUN python -m spacy download en_core_web_sm

# We want to build with closest to production environment as possible
ARG DJANGO_DEBUG=FALSE



ENV POSTGRES_HOST=postgres \
    POSTGRES_PORT=5432 \
    POSTGRES_DB=db_name \
    POSTGRES_USER=postgres \
    POSTGRES_PASSWORD=password \
    MAILJET_API_KEY=a \
    MAILJET_SECRET_KEY=a \
    ENV="build"\
    REDIS_DB=1 \
    REDIS_HOST=redis \
    REDIS_PORT=6379 \
    REDIS_USER=user \
    REDIS_PASSWORD=dummy \
    CACHE_ENABLED=TRUE \


# Collect static files
RUN python manage.py collectstatic --noinput

# Run command
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
