from langchain_ollama import ChatOllama

llm = ChatOllama(
    model="qwen3.5:0.8b",
    temperature=0,
    base_url="http://localhost:11434"
)

print(llm.invoke("Olá, como você está?"))

# Faça uma pergunta sobre os videos da PoD Academy e veja a resposta.
print(llm.invoke("Quais os videos da PoD Academy?"))