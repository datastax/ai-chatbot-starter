# Add documents to the vectorstore, which is on the database, through an embeddings model
import sys
import os

from dotenv import load_dotenv
from langchain.embeddings import VertexAIEmbeddings
from llama_index import VectorStoreIndex, ServiceContext, StorageContext
from llama_index.embeddings import LangchainEmbedding
from llama_index.node_parser import SimpleNodeParser
from llama_index.vector_stores import CassandraVectorStore

sys.path.append("../")
from chatbot_api.compile_docs import convert_scraped_files_to_documents
from integrations.astra import init_astra_session_keyspace_tablename
from integrations.google import init_gcp, GECKO_EMB_DIM

dotenv_path = "../.env"
load_dotenv(dotenv_path)

session, keyspace, table_name = init_astra_session_keyspace_tablename()
init_gcp()

# ENV setup
embedding_model = LangchainEmbedding(
    VertexAIEmbeddings(model_name="textembedding-gecko@latest")
)

vectorstore = CassandraVectorStore(
    session=session,
    keyspace=keyspace,
    table=table_name,
    embedding_dimension=GECKO_EMB_DIM,
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
    documents = convert_scraped_files_to_documents(folder_path)
    VectorStoreIndex.from_documents(
        documents=documents,
        storage_context=storage_context,
        service_context=service_context,
        show_progress=True,
    )


def list_folders(directory):
    return [
        d for d in os.listdir(directory) if os.path.isdir(os.path.join(directory, d))
    ]


for folder in list_folders("."):
    add_documents(folder)
