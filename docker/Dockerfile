FROM python:3.10-bookworm

WORKDIR /src

COPY requirements.txt .
RUN pip install -r requirements.txt
COPY ../scripts/set_oai_vars.sh .
COPY ../scripts/run.sh .
COPY ../app .

CMD ["bash", "run.sh"]