FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app

RUN useradd --create-home agentuser || true
RUN chown -R agentuser:agentuser /app

USER agentuser

ENV PYTHONUNBUFFERED=1
ENV AGENT_BASE_DIR=/workspace

EXPOSE 8000

CMD ["uvicorn", "src.agent.main:app", "--host", "0.0.0.0", "--port", "8000"]
