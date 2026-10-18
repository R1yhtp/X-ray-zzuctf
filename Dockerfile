FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends iverilog \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --gid 10001 scope && useradd --uid 10001 --gid scope --no-create-home scope
WORKDIR /app
COPY rtl ./rtl
RUN mkdir build && iverilog -g2012 -s analyzer_tb -o build/sim.vvp rtl/display_core.sv rtl/analyzer_tb.sv
COPY app ./app
COPY player ./player
COPY LICENSE ./LICENSE
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8000
USER 10001:10001
EXPOSE 8000/tcp
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/healthz',timeout=2)"
CMD ["python", "app/server.py"]
