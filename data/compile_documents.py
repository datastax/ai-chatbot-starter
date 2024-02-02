# Add documents to the vectorstore, which is on the database, through an embeddings model
from dotenv import load_dotenv
from langchain.embeddings import OpenAIEmbeddings, VertexAIEmbeddings
from llama_index import (
    SimpleDirectoryReader,
    VectorStoreIndex,
    ServiceContext,
    StorageContext,
)
from llama_index.embeddings import LangchainEmbedding
from llama_index.node_parser import SimpleNodeParser
from llama_index.vector_stores import AstraDBVectorStore

from integrations.google import init_gcp, GECKO_EMB_DIM
from integrations.openai import OPENAI_EMB_DIM
from pipeline.config import LLMProvider, load_config

dotenv_path = ".env"
load_dotenv(dotenv_path)
config = load_config("config.yml")

# Provider for LLM
if config.llm_provider == LLMProvider.OpenAI:
    embedding_model = LangchainEmbedding(
        OpenAIEmbeddings(model=config.openai_embeddings_model)
    )
else:
    init_gcp(config)
    embedding_model = LangchainEmbedding(
        VertexAIEmbeddings(model_name=config.google_embeddings_model)
    )

embedding_dimension = (
    OPENAI_EMB_DIM if config.llm_provider == LLMProvider.OpenAI else GECKO_EMB_DIM
)

vectorstore = AstraDBVectorStore(
    token=config.astra_db_application_token,
    api_endpoint=config.astra_db_api_endpoint,
    collection_name=config.astra_db_table_name,
    embedding_dimension=embedding_dimension,
)

storage_context = StorageContext.from_defaults(vector_store=vectorstore)
service_context = ServiceContext.from_defaults(
    llm=None,
    embed_model=embedding_model,
    node_parser=SimpleNodeParser.from_defaults(
        # According to https://genai.stackexchange.com/questions/317/does-the-length-of-a-token-give-llms-a-preference-for-words-of-certain-lengths
        # tokens are ~4 chars on average, so estimating 1,000 char chunk_size & 500 char overlap as previously used
        chunk_size=250,
        chunk_overlap=125,
    ),
)


# Perform embedding and add to vectorstore
def add_documents(folder_path):
    documents = SimpleDirectoryReader(folder_path).load_data()
    VectorStoreIndex.from_documents(
        documents=documents,
        storage_context=storage_context,
        service_context=service_context,
        show_progress=True,
    )


if __name__ == "__main__":
    add_documents("output")
