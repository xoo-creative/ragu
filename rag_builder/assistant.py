# from langchain.vectorstores import Chroma
# from langchain.chat_models import ChatOllama
from langchain.chat_models import ChatOpenAI
# from langchain.embeddings import FastEmbedEmbeddings
# from langchain.schema.output_parser import StrOutputParser
# from langchain.document_loaders import PyPDFLoader
# from langchain.text_splitter import RecursiveCharacterTextSplitter
# from langchain.schema.runnable import RunnablePassthrough
# from langchain.prompts import PromptTemplate
# from langchain.vectorstores.utils import filter_complex_metadata
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory

from rag_builder.commons.utils import load_prompt

import requests
from langchain.prompts import ChatPromptTemplate
from langchain.document_loaders import TextLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser
from langchain.embeddings import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.vectorstores import Weaviate
import weaviate
from weaviate.embedded import EmbeddedOptions

from dotenv import load_dotenv

load_dotenv()

class Assistant:
    
    def __init__(self) -> None:
        self.data = None
        # self.client = weaviate.Client(
        #     embedded_options = EmbeddedOptions()
        # )
        self.prompt = self.initialize_prompt()
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        pass

    def _load(self) -> None:
        url = "https://raw.githubusercontent.com/langchain-ai/langchain/master/docs/docs/modules/state_of_the_union.txt"
        res = requests.get(url)
        with open("state_of_the_union.txt", "w") as f:
            f.write(res.text)

        loader = TextLoader('./state_of_the_union.txt')
        self.documents = loader.load()

        return self.documents
    
    def _chunk(self):
        text_splitter = CharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        self.chunks = text_splitter.split_documents(self.documents)
        return self.chunks

    def embed_and_store(self):
        self.vectorstore = FAISS.from_documents(self.chunks, embedding=OpenAIEmbeddings())


    def initialize_prompt(self):
        template = load_prompt("test-prompt")
        prompt = ChatPromptTemplate.from_template(template)

        return prompt
    
    def test(self):
        self._load()

        self._chunk()

        self.embed_and_store()

        memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)

        conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(),
            memory=memory
        )
        query = input("What do you want to ask?")
        result = conversation_chain({"question": query})
        answer = result["answer"]
        print(answer)
    

    



       