# Teste rápido: busca por similaridade nos dois índices Pinecone (mesmos nomes do ingest_pipeline).
# Confere se há vetores e metadados. Rode: python test.py (nesta pasta, com .env preenchido).

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_pinecone import PineconeVectorStore

# ---------------------------------------------------------------------------
# Mesma lógica de .env do ingest: 02-agentic-rag/.env e depois data-engineering/.env
# ---------------------------------------------------------------------------
pasta_dest_script = Path(__file__).resolve().parent
pasta_raiz_agentic_rag = pasta_dest_script.parent
load_dotenv(pasta_raiz_agentic_rag / ".env")
load_dotenv(pasta_dest_script / ".env", override=True)

chave_google = os.environ.get("GOOGLE_API_KEY", "").strip()
chave_pinecone = os.environ.get("PINECONE_API_KEY", "").strip()
if not chave_google:
    print("Falta GOOGLE_API_KEY no .env", file=sys.stderr)
    sys.exit(1)
if not chave_pinecone:
    print("Falta PINECONE_API_KEY no .env", file=sys.stderr)
    sys.exit(1)

# Mesmo modelo de embedding do ingest (tem que ser igual ao usado ao subir os dados)
nome_modelo_embedding = os.environ.get("GOOGLE_EMBEDDING_MODEL", "models/text-embedding-004")

embeddings = GoogleGenerativeAIEmbeddings(
    model=nome_modelo_embedding,
    google_api_key=chave_google,
)

# Nomes dos índices (iguais ao ingest_pipeline.py)
nome_indice_resumos = "pod-academy"
nome_indice_titulos = "titles-videos"

# Perguntas de teste (em português; o vetor do índice de resumos veio do texto resumido)
consulta_resumo = "dados produtos analytics live entrevista"
# Para o índice de títulos, buscamos por palavras parecidas com um título de vídeo
consulta_titulo = "dados carreira mercado"

# ---------------------------------------------------------------------------
# Índice pod-academy: page_content = resumo gerado pelo Groq (chave "text" no Pinecone via LangChain).
# ---------------------------------------------------------------------------
print("=== Índice:", nome_indice_resumos, "===")
vs_resumos = PineconeVectorStore.from_existing_index(
    index_name=nome_indice_resumos,
    embedding=embeddings,
)
resultados_resumos = vs_resumos.similarity_search_with_score(consulta_resumo, k=3)
if not resultados_resumos:
    print("Nenhum resultado (rode o ingest_pipeline.py de novo após a mudança para LangChain).")
else:
    for doc, score in resultados_resumos:
        print(f"  score={score:.4f} | video_id={doc.metadata.get('video_id')} | título={doc.metadata.get('video_title', '')[:70]}…")
        print(f"            resumo (trecho): {doc.page_content[:220]}…")
        print(f"            canal={doc.metadata.get('channel', '')[:60]}…")

print()

# ---------------------------------------------------------------------------
# Índice titles-videos: page_content = título do vídeo (vetor embedado do título).
# ---------------------------------------------------------------------------
print("=== Índice:", nome_indice_titulos, "===")
vs_titulos = PineconeVectorStore.from_existing_index(
    index_name=nome_indice_titulos,
    embedding=embeddings,
)
resultados_titulos = vs_titulos.similarity_search_with_score(consulta_titulo, k=3)
if not resultados_titulos:
    print("Nenhum resultado.")
else:
    for doc, score in resultados_titulos:
        print(f"  score={score:.4f} | video_id={doc.metadata.get('video_id')} | título={doc.page_content[:90]}…")

print()
print("Se apareceram linhas acima, os dados estão indexados. Scores são similaridade do Pinecone (cosine).")
