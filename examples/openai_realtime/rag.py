import logging
import os

import nest_asyncio
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import SimpleNodeParser
from pydantic import BaseModel

import outspeed as sp

nest_asyncio.apply()

PARENT_DIR = os.path.dirname(os.path.abspath(__file__))


class Query(BaseModel):
    query_for_neural_search: str


class RAGResult(BaseModel):
    result: str


class RAGTool(sp.Tool):
    name = "rag"
    description = "Search the knowledge base for information"
    parameters_type = Query
    response_type = RAGResult

    def __init__(self):
        super().__init__()
        documents = SimpleDirectoryReader(f"{PARENT_DIR}/data/").load_data()
        node_parser = SimpleNodeParser.from_defaults(chunk_size=512)
        nodes = node_parser.get_nodes_from_documents(documents=documents)
        vector_index = VectorStoreIndex(nodes)
        self.query_engine = vector_index.as_query_engine(similarity_top_k=2)

    async def run(self, query: Query) -> RAGResult:
        logging.info(f"Searching for: {query.query_for_neural_search}")
        response = self.query_engine.query(query.query_for_neural_search)
        logging.info(f"RAG Response: {response}")
        return RAGResult(result=str(response))


@sp.App()
class VoiceBot:
    async def setup(self) -> None:
        # download and install dependencies
        documents = SimpleDirectoryReader(f"{PARENT_DIR}/data/").load_data()
        node_parser = SimpleNodeParser.from_defaults(chunk_size=512)
        nodes = node_parser.get_nodes_from_documents(documents=documents)
        vector_index = VectorStoreIndex(nodes)
        self.query_engine = vector_index.as_query_engine(similarity_top_k=2)
        # Initialize the AI services
        self.llm_node = sp.OpenAIRealtime(
            tools=[
                RAGTool(),
            ]
        )

    @sp.streaming_endpoint()
    async def run(self, audio_input_queue: sp.AudioStream, text_input_queue: sp.TextStream):
        # Set up the AI service pipeline
        audio_output_stream: sp.AudioStream
        audio_output_stream, text_output_stream = self.llm_node.run(text_input_queue, audio_input_queue)

        return audio_output_stream, text_output_stream

    async def teardown(self) -> None:
        """
        Clean up resources when the VoiceBot is shutting down.
        """
        await self.llm_node.close()


if __name__ == "__main__":
    # Start the VoiceBot when the script is run directly
    VoiceBot().start()
