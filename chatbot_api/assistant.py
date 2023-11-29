from abc import ABC, abstractmethod
from typing import List, Optional, Tuple

from langchain.embeddings.base import Embeddings
from langchain.embeddings import OpenAIEmbeddings, VertexAIEmbeddings
from langchain.llms import VertexAI
from llama_index import VectorStoreIndex, ServiceContext
from llama_index.vector_stores import AstraDBVectorStore
from llama_index.embeddings import LangchainEmbedding
from llama_index.llms import OpenAI
from llama_index.response.schema import StreamingResponse

from chatbot_api.prompt_util import get_template
from integrations.google import GECKO_EMB_DIM, init_gcp
from integrations.openai import OPENAI_EMB_DIM
from pipeline.config import Config, LLMProvider


class Assistant(ABC):
    def __init__(
        self,
        config: Config,
        embeddings: Embeddings,
        k: int = 4,
        llm=None,
    ):
        self.config = config
        self.embedding_model = LangchainEmbedding(embeddings)
        self.llm = llm

        embedding_dimension = (
            OPENAI_EMB_DIM
            if self.config.llm_provider == LLMProvider.OpenAI
            else GECKO_EMB_DIM
        )

        # Initialize the vector store, which contains the vector embeddings of the data
        self.vectorstore = AstraDBVectorStore(
            token=self.config.astra_db_application_token,
            api_endpoint=self.config.astra_db_api_endpoint,
            collection_name=self.config.astra_db_table_name,
            embedding_dimension=embedding_dimension,
        )

        self.service_context = ServiceContext.from_defaults(
            llm=llm, embed_model=self.embedding_model
        )

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vectorstore, service_context=self.service_context
        )

        self.query_engine = self.index.as_query_engine(
            similarity_top_k=k, streaming=True
        )

    # Get a response from the vector search, aka the relevant data
    def find_relevant_docs(self, query: str) -> str:
        response = self.query_engine.query(
            query
        )  # TODO: Retriever (index.as_retriever (returns list of source nodes instead of response object))
        results = response.source_nodes

        raw_text = []
        for doc in results:
            try:
                raw_text.append(
                    doc.get_content()
                    + f"\nPrevious document was from URL link: {doc.metadata['source']}"
                )
            except KeyError:
                raw_text.append(doc.get_content())
        vector_search_results = "- " + "\n\n- ".join(
            raw_text
        )  # Prevent any one document from being too long

        return vector_search_results

    # Get a response from the chatbot, excluding the responses from the vector search
    @abstractmethod
    def get_response(
        self,
        user_input: str,
        persona: str,
        user_context: str = "",
        include_context: bool = True,
    ) -> Tuple[str, str, str]:
        """
        :returns: Should return a tuple of
                  (bot response, vector store responses string, user context)
        """


class AssistantBison(Assistant):
    # Instantiate the class using the default bison model
    def __init__(
        self,
        config: Config,
        temp: float = 0.2,
        max_tokens_response: int = 256,
        k: int = 4,
        company: str = "",
        custom_rules: Optional[List[str]] = None,
    ):
        # Choose the embeddings and LLM based on the llm_provider
        if config.llm_provider == LLMProvider.OpenAI:
            embeddings = OpenAIEmbeddings(model=config.openai_embeddings_model)
            llm = OpenAI(model=config.openai_textgen_model)

        elif config.llm_provider == LLMProvider.Google:
            init_gcp(config)
            embeddings = VertexAIEmbeddings(model_name=config.google_embeddings_model)
            llm = VertexAI(model_name=config.google_textgen_model)

        else:
            raise AssertionError("LLM Provider must be one of openai or google")

        super().__init__(config, embeddings, k, llm)

        self.parameters = {
            "temperature": temp,  # Temperature controls the degree of randomness in token selection.
            "max_tokens": max_tokens_response,  # Token limit determines the maximum amount of text output.
        }

        self.company = company
        self.custom_rules = custom_rules or []

    def get_response(
        self,
        user_input: str,
        persona: str,
        user_context: str = "",
        include_context: bool = True,
    ) -> Tuple[StreamingResponse, str, str]:
        responses_from_vs = self.find_relevant_docs(query=user_input)
        # Ensure that we include the prompt context assuming the parameter is provided
        context = user_input
        if include_context:
            # If we have a special tag, include no further context from the vector DB
            if "[NO CONTEXT]" in user_context:
                responses_from_vs = ""

            context = get_template(
                persona,
                responses_from_vs,
                user_input,
                user_context,
                self.company,
                self.custom_rules,
            )

        bot_response = self.query_engine.query(context)

        return bot_response, responses_from_vs, context
