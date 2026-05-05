# Guia Windows: VM + banco + SQL

Este guia mostra como preparar o ambiente no Windows (host ou VM), subir o PostgreSQL com Docker e executar o SQL inicial do projeto `01-simple-react-agent`.

## 1) Pre-requisitos

- Windows 10/11 atualizado.
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) instalado e em execucao.
- [Git for Windows](https://git-scm.com/download/win) instalado.
- Python 3.10+ instalado.
- PowerShell disponivel.

## 2) Clonar repositorio e entrar na pasta

```powershell
git clone <URL_DO_REPOSITORIO>
cd course-ai-engineering
cd 01-simple-react-agent
```

## 3) Subir o banco PostgreSQL com Docker Compose

Na pasta `01-simple-react-agent`:

```powershell
docker compose -f database/docker-compose.yaml up -d
```

Validar se subiu:

```powershell
docker ps
```

Servico esperado:

- Container: `simple-react-agent-postgres`
- Porta: `5432`
- Banco: `app_db`
- Usuario: `app_user`
- Senha: `app_password`

## 4) Executar o SQL inicial

```powershell
Get-Content database/create_tables.sql | docker exec -i simple-react-agent-postgres psql -U app_user -d app_db
```

Validar tabelas:

```powershell
docker exec -it simple-react-agent-postgres psql -U app_user -d app_db -c "\dt"
```

Tabelas esperadas:

- `products`
- `inventory`
- `sales`

## 5) Preparar Python e dependencias

Na raiz `course-ai-engineering`:

```powershell
python -m venv myenv
.\myenv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## 6) Configurar variaveis do backend

Criar o arquivo `01-simple-react-agent/backend/.env`:

```env
GROQ_API_KEY=sua_chave
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app_db
POSTGRES_USER=app_user
POSTGRES_PASSWORD=app_password
```

## 7) Subir backend e frontend (em terminais separados)

**Importante:** backend e frontend devem rodar em **terminais separados**.

### Terminal 1 - Backend

```powershell
cd .\01-simple-react-agent\backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Terminal 2 - Frontend

```powershell
cd .\01-simple-react-agent\frontend
chainlit run app.py -w --port 8501
```

## 8) Comandos uteis

Parar banco:

```powershell
docker compose -f database/docker-compose.yaml down
```

Parar e apagar dados:

```powershell
docker compose -f database/docker-compose.yaml down -v
```
