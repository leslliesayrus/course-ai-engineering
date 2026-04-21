# Script: lê os JSONs de vídeo, gera resumo (Groq), grava vetores no Pinecone e salva no SQLite.
# Para rodar: python ingest_pipeline.py (pode ser nesta pasta ou em 02-agentic-rag).
# O .env pode ficar em 02-agentic-rag/.env ou em data-engineering/.env (este último vale se os dois existirem).

import json
import os
import sqlite3
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone

# ---------------------------------------------------------------------------
# Pastas e nomes fixos (não precisa mudar se os arquivos estiverem no lugar certo)
# ---------------------------------------------------------------------------
pasta_dest_script = Path(__file__).resolve().parent
pasta_raiz_agentic_rag = pasta_dest_script.parent
pasta_dados = pasta_dest_script / "data"
arquivo_sqlite = pasta_dest_script / "videos.db"
nome_indice_resumos = "pod-academy"
nome_indice_titulos = "titles-videos"

# ---------------------------------------------------------------------------
# Carrega o .env: primeiro o da pasta 02-agentic-rag, depois o desta pasta (data-engineering).
# Se existirem os dois, o .env ao lado deste script sobrescreve (override=True).
# ---------------------------------------------------------------------------
load_dotenv(pasta_raiz_agentic_rag / ".env")
load_dotenv(pasta_dest_script / ".env", override=True)

# ---------------------------------------------------------------------------
# Confere se as três chaves obrigatórias existem (senão o programa para e avisa)
# ---------------------------------------------------------------------------
chave_groq = os.environ.get("GROQ_API_KEY", "").strip()
chave_google = os.environ.get("GOOGLE_API_KEY", "").strip()
chave_pinecone = os.environ.get("PINECONE_API_KEY", "").strip()
if not chave_groq:
    print("Falta GROQ_API_KEY no .env", file=sys.stderr)
    sys.exit(1)
if not chave_google:
    print("Falta GOOGLE_API_KEY no .env", file=sys.stderr)
    sys.exit(1)
if not chave_pinecone:
    print("Falta PINECONE_API_KEY no .env", file=sys.stderr)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Modelos (podem ser trocados no .env: GROQ_MODEL e GOOGLE_EMBEDDING_MODEL)
# ---------------------------------------------------------------------------
nome_modelo_groq = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")
nome_modelo_embedding = os.environ.get("GOOGLE_EMBEDDING_MODEL", "models/text-embedding-004")

# ---------------------------------------------------------------------------
# Prepara o “cérebro” do Groq (vai escrever os resumos)
# ---------------------------------------------------------------------------
llm = ChatGroq(model=nome_modelo_groq, temperature=0)

# ---------------------------------------------------------------------------
# Prepara o gerador de embeddings do Google (transforma texto em vetor)
# ---------------------------------------------------------------------------
embeddings = GoogleGenerativeAIEmbeddings(
    model=nome_modelo_embedding,
    google_api_key=chave_google,
)

# ---------------------------------------------------------------------------
# Conecta no Pinecone e cria as “lojas” LangChain (embeddings = texto do Document)
# ---------------------------------------------------------------------------
cliente_pinecone = Pinecone(api_key=chave_pinecone)
indice_resumos = cliente_pinecone.Index(nome_indice_resumos)
indice_titulos = cliente_pinecone.Index(nome_indice_titulos)
# page_content vira o texto embedado; o LangChain também grava esse texto em metadata["text"] no Pinecone.
loja_resumos = PineconeVectorStore(index=indice_resumos, embedding=embeddings)
loja_titulos = PineconeVectorStore(index=indice_titulos, embedding=embeddings)

# ---------------------------------------------------------------------------
# Abre o banco SQLite local e cria a tabela se ainda não existir
# ---------------------------------------------------------------------------
conexao_sqlite = sqlite3.connect(arquivo_sqlite)
conexao_sqlite.execute(
    """
    CREATE TABLE IF NOT EXISTS videos (
        channel TEXT NOT NULL,
        video_title TEXT NOT NULL,
        video_id TEXT PRIMARY KEY,
        content TEXT NOT NULL
    )
    """
)
conexao_sqlite.commit()

# ---------------------------------------------------------------------------
# Lista todos os arquivos .json da pasta data
# ---------------------------------------------------------------------------
if not pasta_dados.is_dir():
    print(f"Pasta não encontrada: {pasta_dados}", file=sys.stderr)
    sys.exit(1)
lista_jsons = sorted(pasta_dados.glob("*.json"))
if not lista_jsons:
    print(f"Nenhum arquivo .json em {pasta_dados}", file=sys.stderr)
    sys.exit(1)

print(f"Processando {len(lista_jsons)} arquivos JSON…")

# ---------------------------------------------------------------------------
# Para cada arquivo JSON: ler → resumir → vetores no Pinecone → linha no SQLite
# ---------------------------------------------------------------------------
for caminho_json in lista_jsons:
    with open(caminho_json, encoding="utf-8") as f:
        registro = json.load(f)

    canal = registro.get("channel") or ""
    titulo_video = registro.get("video_title") or ""
    id_video = registro.get("video_id") or caminho_json.stem
    texto_transcricao = registro.get("content") or ""

    # Se não tiver texto, pula este arquivo
    if not texto_transcricao.strip():
        print(f"[ignorado] {caminho_json.name}: conteúdo vazio")
        continue

    print(f"  {id_video} — {titulo_video[:60]}…")

    # --- Bloco: pedir ao Groq um resumo em até 7 linhas ---
    texto_instrucao_sistema = (
        "Você resume transcrições de vídeos em português. "
        "Produza um resumo objetivo com no máximo 7 linhas (parágrafos curtos ou linhas numeradas). "
        "Não use markdown. Não invente fatos que não estejam no texto."
    )
    texto_usuario = f"Transcrição:\n\n{texto_transcricao[:120000]}"
    resposta_llm = llm.invoke(
        [
            SystemMessage(content=texto_instrucao_sistema),
            HumanMessage(content=texto_usuario),
        ]
    )
    resumo = (resposta_llm.content or "").strip()
    linhas_resumo = resumo.splitlines()
    if len(linhas_resumo) > 7:
        resumo = "\n".join(linhas_resumo[:7])

    # --- Bloco: índice pod-academy — embeda o RESUMO (Groq) e sobe com LangChain add_documents ---
    documento_resumo = Document(
        page_content=resumo,
        metadata={
            "video_title": titulo_video[:500],
            "video_id": id_video,
            "channel": canal[:500],
        },
    )
    loja_resumos.add_documents([documento_resumo], ids=[id_video])

    # --- Bloco: índice titles-videos — embeda o TÍTULO do vídeo; metadata com video_id (LangChain acrescenta "text" com o título) ---
    documento_titulo = Document(
        page_content=titulo_video,
        metadata={"video_id": id_video},
    )
    loja_titulos.add_documents([documento_titulo], ids=[id_video])

    # --- Bloco: guardar no SQLite a linha com canal, título, id e transcrição inteira ---
    conexao_sqlite.execute(
        """
        INSERT INTO videos (channel, video_title, video_id, content)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(video_id) DO UPDATE SET
            channel = excluded.channel,
            video_title = excluded.video_title,
            content = excluded.content
        """,
        (canal, titulo_video, id_video, texto_transcricao),
    )
    conexao_sqlite.commit()

# ---------------------------------------------------------------------------
# Fecha o SQLite e mostra onde ficou o arquivo
# ---------------------------------------------------------------------------
conexao_sqlite.close()
print(f"Concluído. Banco SQLite salvo em: {arquivo_sqlite}")
