FROM python:3.11-bookworm AS base
WORKDIR /code
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY src src

FROM base AS test
COPY tests/test_requirements.txt .coveragerc ./
RUN pip install -r test_requirements.txt
COPY tests tests

FROM base AS build
CMD [ "python", "-m", "src.export" ]