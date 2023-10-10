from langchain.embeddings import VertexAIEmbeddings

from abc import ABC, abstractmethod

from os.path import join, dirname
from dotenv import load_dotenv
import sys
from vertexai.preview.language_models import TextGenerationModel

from llama_index import VectorStoreIndex, ServiceContext
from llama_index.vector_stores import CassandraVectorStore
from llama_index.embeddings import LangchainEmbedding

sys.path.append("../")
# The below line will be red in Pycharm, but it's fine
from chatbot_api.prompt_util import get_template
from utils.slack import send_slack_message
from utils.google import GECKO_EMB_DIM

# IMPORTANT: MUST SET PROJECT ID HERE!
dotenv_path = join(dirname(__file__), "../.env")
load_dotenv(dotenv_path)


class NoSqlAssistant(ABC):
    def __init__(
        self,
        session,
        embeddings=None,
        keyspace="chat",
        table_name="data",
        k=4,
    ):
        if embeddings is None:
            embeddings = VertexAIEmbeddings(model_name="textembedding-gecko@latest")

        # Set the session, embeddings, keyspace, and table name from the args/kwargs
        self.session = session
        self.embeddings = embeddings
        self.keyspace = keyspace
        self.table_name = table_name

        # Initialize the vector store, which contains the vector embeddings of the data
        self.vectorstore = CassandraVectorStore(
            session=session,
            keyspace=keyspace,
            table=table_name,
            embedding_dimension=GECKO_EMB_DIM,
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
    def find_relevant_docs(self, query, return_first_url=False):
        response = self.query_engine.query(
            query
        )  # TODO: Retriever (index.as_retriever (returns list of source nodes instead of response object))
        results = response.source_nodes

        raw_text = []
        first_url = ""
        for i, doc in enumerate(results):
            try:
                raw_text.append(
                    doc.get_content()
                    + f"\nPrevious document was from URL link: {doc.metadata['source']}"
                )
                if len(first_url) == 0:
                    first_url = doc.metadata["url"]
            except KeyError:
                raw_text.append(doc.get_content())
        vector_search_results = "- " + "\n\n- ".join(
            raw_text
        )  # Prevent any one document from being too long

        if return_first_url:
            return vector_search_results, first_url
        return vector_search_results

    # Get a response from the chatbot, excluding the responses from the vector search
    @abstractmethod
    def get_response(self, user_input, n_results=5, persona="qualified") -> str:
        answer, _ = self.get_response(user_input, persona, n_results=n_results)
        return answer


class AssistantBison(NoSqlAssistant):
    # Instantiate the class using the default bison model
    def __init__(
        self,
        session,
        embeddings=None,
        keyspace="chat",
        table_name="data",
        temp=0.2,
        top_p=0.8,
        top_k=40,
        max_tokens_response=256,
        k=4,
        company="",
        custom_rules="",
    ):
        super().__init__(session, embeddings, keyspace, table_name, k)
        # Create the model and chat session
        model = TextGenerationModel.from_pretrained("text-bison@001")

        self.parameters = {
            "temperature": temp,  # Temperature controls the degree of randomness in token selection.
            "max_output_tokens": max_tokens_response,  # Token limit determines the maximum amount of text output.
            "top_p": top_p,
            # Tokens are selected from most probable to least until the sum of their probabilities equals the top_p value.
            "top_k": top_k,  # A top_k of 1 means the selected token is the most probable among all tokens.
        }
        self.model = model
        self.company = company
        self.custom_rules = custom_rules

    def get_response(self, user_input, persona, user_context="", include_context=True):
        responses_from_vs, first_url = self.find_relevant_docs(
            query=user_input, return_first_url=True
        )
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

        send_slack_message("*PROMPT*")
        send_slack_message(context)

        bot_response = self.model.predict(context, **self.parameters).text

        send_slack_message("*RESPONSE*")
        send_slack_message(bot_response)

        return bot_response, responses_from_vs, context
