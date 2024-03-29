from langchain_openai import ChatOpenAI
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from lxml.html import fromstring
from bs4 import BeautifulSoup

from ragu.commons.utils import load_prompt

import requests
from langchain_core.documents import Document
from langchain.prompts import ChatPromptTemplate
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from openai import OpenAI

from dotenv import load_dotenv

import logging

load_dotenv()

class Assistant:
    
    def __init__(self) -> None:
        self.data = None
        self.prompt = self.initialize_prompt()
        self.llm = ChatOpenAI(model_name="gpt-3.5-turbo", temperature=0)
        self.memory = ConversationBufferMemory(memory_key='chat_history', return_messages=True)
        self.initialized = False
        self.openai_direct_client = OpenAI()
        self.documents_loaded = []
        pass
    
    def parse_file_contents(self, file_contents: list[str]) -> list[Document]:
        if len(file_contents) == 0:
            return []
        
        logging.info("Creating documents from uploaded files. ")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
        )
        return text_splitter.create_documents(file_contents)

    def initialize_knowledge(self, urls: list[str], file_contents: list[str]):

        self.documents = self.read_urls(urls)

        self.documents += self.parse_file_contents(file_contents)

        self._chunk()
        self.embed_and_store()

        self.conversation_chain = ConversationalRetrievalChain.from_llm(
            llm=self.llm,
            chain_type="stuff",
            retriever=self.vectorstore.as_retriever(search_kwargs={'k': 9}),
            memory=self.memory
        )

        self.initialized = True

    def read_urls(self, list_of_urls = list[str]) -> list[Document]:

        if len(list_of_urls) == 0:
            return []
        
        url_texts = []
        for url in list_of_urls:
            url_texts.append(self.read_url(url.strip()))

        logging.info("Creating documents from content from urls.")

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=100,
        )
        return text_splitter.create_documents(url_texts)
    
    def add_knowledge_source(self, name: str):
        self.documents_loaded.append(name)

    def read_url(self, url) -> str:

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text()

        logging.info(f"soup get text looks like {text}")

        tree = fromstring(response.content)
        title = tree.findtext('.//title')
        self.documents_loaded.append(f"[URL] {title}")

        return text
    
    def current_knowledge(self) -> str:
        """
        Renders all current sources of information into a comma separated string.
        """
        return ", ".join(self.documents_loaded)


            
    def _chunk(self):
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
        self.chunks = text_splitter.split_documents(self.documents)
        return self.chunks

    def embed_and_store(self):
        logging.debug("Loading documents into FAISS...")
        self.vectorstore = FAISS.from_documents(self.chunks, embedding=OpenAIEmbeddings())


    def initialize_prompt(self):
        template = load_prompt("rag")
        prompt = ChatPromptTemplate.from_template(template)

        return prompt
    
    def is_inappropriate(self, query: str) -> bool:
        """
        Returns true if the query is inappropriate
        """
        response = self.openai_direct_client.moderations.create(input=query, model="text-moderation-latest")

        output = response.results[0]
        logging.debug(f"Moderation output for query {query}: {output}")
        return output.flagged

    
    def ask(self, query: str) -> str:
        """
        Asks the assistant a question, returns an answer related to the text.
        """

        if not self.initialized:
            raise RuntimeError("You have not run 'Assistant.initialize()' yet, so the vector store is empty.")

        result = self.conversation_chain.invoke({"question": query})
        answer = result["answer"]

        return answer

    



       