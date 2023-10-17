import os
from abc import ABC, abstractmethod
import sys
from typing import List, Optional, Tuple

from langchain.embeddings.base import Embeddings
from langchain.embeddings import OpenAIEmbeddings, VertexAIEmbeddings
from llama_index import VectorStoreIndex, ServiceContext
from llama_index.vector_stores import CassandraVectorStore
from llama_index.embeddings import LangchainEmbedding
from vertexai.preview.language_models import TextGenerationModel

sys.path.append(os.getcwd())
from chatbot_api.prompt_util import get_template
from integrations.astra import DEFAULT_TABLE_NAME
from integrations.google import GECKO_EMB_DIM, init_gcp
from integrations.openai import OPENAI_EMB_DIM, init_chat_completion


class Assistant(ABC):
    def __init__(
        self,
        embeddings: Optional[Embeddings] = None,
        table_name: str = DEFAULT_TABLE_NAME,
        k: int = 4,
        llm_provider: str = "openai",
    ):
        # Set the embeddings, keyspace, and table name from the args/kwargs
        self.embeddings = embeddings
        self.table_name = table_name

        embedding_dimension = OPENAI_EMB_DIM if llm_provider == "openai" else GECKO_EMB_DIM

        # Initialize the vector store, which contains the vector embeddings of the data
        # NOTE: With cassio init, session & keyspace are inferred from global default
        self.vectorstore = CassandraVectorStore(
            session=None,
            keyspace=None,
            table=table_name,
            embedding_dimension=embedding_dimension,
        )

        self.embedding_model = LangchainEmbedding(self.embeddings)

        self.service_context = ServiceContext.from_defaults(
            llm=None, embed_model=self.embedding_model
        )

        self.index = VectorStoreIndex.from_vector_store(
            vector_store=self.vectorstore, service_context=self.service_context
        )

        self.query_engine = self.index.as_query_engine(similarity_top_k=k)

    # Get a response from the vector search, aka the relevant data
    def find_relevant_docs(self, query: str) -> Tuple[str, str]:
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
        embeddings: Optional[Embeddings] = None,
        table_name: str = DEFAULT_TABLE_NAME,
        temp: float = 0.2,
        top_p: float = 0.8,
        top_k: int = 40,
        max_tokens_response: int = 256,
        k: int = 4,
        company: str = "",
        custom_rules: Optional[List[str]] = None,
    ):
        if embeddings is None:
            self.llm_provider = os.getenv("LLM_PROVIDER", "openai")
            if self.llm_provider == "openai":
                embeddings = OpenAIEmbeddings(model=os.getenv("OPENAI_EMBEDDINGS_MODEL", "text-embedding-ada-002"))
                model = init_chat_completion()
            else:
                init_gcp()
                embeddings = VertexAIEmbeddings(model_name=os.getenv("GOOGLE_EMBEDDINGS_MODEL", "textembedding-gecko@latest"))
                model = TextGenerationModel.from_pretrained(os.getenv("GOOGLE_TEXTGEN_MODEL", "text-bison@001"))

        super().__init__(embeddings, table_name, k, self.llm_provider)

        self.parameters = {
            "temperature": temp,  # Temperature controls the degree of randomness in token selection.
            "max_output_tokens": max_tokens_response,  # Token limit determines the maximum amount of text output.
            "top_p": top_p,
            # Tokens are selected from most probable to least until the sum of their probabilities equals the top_p value.
            "top_k": top_k,  # A top_k of 1 means the selected token is the most probable among all tokens.
        }
        self.model = model
        self.company = company
        self.custom_rules = custom_rules or []

    def get_response(
        self,
        user_input: str,
        persona: str,
        user_context: str = "",
        include_context: bool = True,
    ) -> Tuple[str, str, str]:
        responses_from_vs = self.find_relevant_docs(query=user_input)
        # Ensure that we include the prompt context assuming the parameter is provided
        context = user_input
        if include_context:
            context = get_template(
                persona,
                responses_from_vs,
                user_input,
                user_context,
                self.company,
                self.custom_rules,
            )

        if self.llm_provider == "openai":
            bot_response_raw = self.model.create(
                model=os.getenv("OPENAI_TEXTGEN_MODEL", "gpt-3.5-turbo"),
                messages=[
                    {"role": "system", "content": context},
                    {"role": "user", "content": user_input},
                ],
            )

            bot_response = bot_response_raw["choices"][0]["message"]["content"]
        else:
            bot_response = self.model.predict(context, **self.parameters).text

        return bot_response, responses_from_vs, context
