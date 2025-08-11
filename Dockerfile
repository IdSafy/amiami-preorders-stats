ARG PYTHON_BASE=3.13-slim
ARG NODE_BASE=20.17.0


#----------------
# frontend build stage
#----------------
FROM node:${NODE_BASE} AS frontend_build

WORKDIR /build/

COPY frontend/package*.json ./

RUN npm install --legacy-peer-deps

COPY frontend/ ./

RUN npm run build


#----------------
# backend build stage
#----------------
FROM python:${PYTHON_BASE} AS backend_build

# install PDM
RUN pip install -U pdm
# disable update check
ENV PDM_CHECK_UPDATE=false
# copy files
COPY pyproject.toml pdm.lock README.md /project/

# install dependencies and project into the local packages directory
WORKDIR /project
RUN pdm install --check --prod --no-editable

#----------------
# main image
#----------------
FROM python:${PYTHON_BASE}

WORKDIR /app

COPY --from=backend_build /project/.venv/lib/python3.13/site-packages/  /usr/local/lib/python3.13/site-packages/

COPY src/ src/
COPY entrypoint.sh entrypoint.sh

COPY --from=frontend_build /build/dist/ ./frontend/dist/

ENTRYPOINT [ "/bin/sh", "./entrypoint.sh" ]
