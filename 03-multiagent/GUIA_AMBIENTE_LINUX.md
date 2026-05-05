# Guia Linux: VM + banco + SQL

Este guia mostra como preparar uma VM Linux, subir o PostgreSQL com Docker e executar o SQL inicial do projeto `01-simple-react-agent`.

## 1) Pre-requisitos

- VM Linux (recomendado: Ubuntu 22.04+).
- Minimo recomendado:
  - 2 vCPU
  - 4 GB RAM
  - 25 GB disco
- Internet para instalar dependencias.

## 2) Preparar sistema

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y git curl ca-certificates gnupg lsb-release python3 python3-pip python3-venv
```

## 3) Instalar Docker e Compose plugin

```bash
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Opcional (rodar Docker sem `sudo`):

```bash
sudo usermod -aG docker $USER
newgrp docker
```

Validar:

```bash
docker --version
docker compose version
```

## 4) Clonar repositorio e entrar na pasta

```bash
git clone <URL_DO_REPOSITORIO>
cd course-ai-engineering
cd 01-simple-react-agent
```

## 5) Subir o banco PostgreSQL

```bash
docker compose -f database/docker-compose.yaml up -d
docker ps
```

Servico esperado:

- Container: `simple-react-agent-postgres`
- Porta: `5432`
- Banco: `app_db`
- Usuario: `app_user`
- Senha: `app_password`

## 6) Executar o SQL inicial

```bash
docker exec -i simple-react-agent-postgres \
  psql -U app_user -d app_db < database/create_tables.sql
```

Validar tabelas:

```bash
docker exec -it simple-react-agent-postgres psql -U app_user -d app_db -c "\dt"
```

Tabelas esperadas:

- `products`
- `inventory`
- `sales`

## 7) Preparar Python e dependencias

Na raiz `course-ai-engineering`:

```bash
python3 -m venv myenv
source myenv/bin/activate
pip install -r requirements.txt
```

## 8) Configurar variaveis do backend

Criar `01-simple-react-agent/backend/.env`:

```env
GROQ_API_KEY=sua_chave
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=app_password
```

## 9) Subir backend e frontend (em terminais separados)

**Importante:** backend e frontend devem rodar em **terminais separados**.

### Terminal 1 - Backend

```bash
cd 01-simple-react-agent/backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 - Frontend

```bash
cd 01-simple-react-agent/frontend
chainlit run app.py -w --port 8501
```

## 10) Comandos uteis

Parar banco:

```bash
docker compose -f database/docker-compose.yaml down
```

Parar e apagar dados:

```bash
docker compose -f database/docker-compose.yaml down -v
```
