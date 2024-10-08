import streamlit as st
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import os
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import google.generativeai as genai
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv

# Load environment variables from .env file and configure Google API
# This is crucial for securely managing API keys and other sensitive information
load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_pdf_text(pdf_docs):
    """
    Extract text content from uploaded PDF documents.
    
    Args:
    pdf_docs (list): List of uploaded PDF file objects.
    
    Returns:
    str: Concatenated text content from all pages of all PDFs.
    """
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text()
    return text

def get_text_chunks(text):
    """
    Split the extracted text into smaller, overlapping chunks for better processing.
    
    Args:
    text (str): The full text extracted from PDFs.
    
    Returns:
    list: A list of text chunks.
    """
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    chunks = text_splitter.split_text(text)
    return chunks

def get_vector_store(text_chunks):
    """
    Create a vector store from the text chunks using FAISS and Google's embedding model.
    
    Args:
    text_chunks (list): List of text chunks to be embedded and stored.
    
    Side effect:
    Saves the vector store locally for future use.
    """
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    vector_store = FAISS.from_texts(text_chunks, embedding=embeddings)
    vector_store.save_local("faiss_index")

def get_conversational_chain():
    """
    Set up the conversational chain for question answering using a custom prompt template.
    
    Returns:
    Chain: A LangChain QA chain configured with the Gemini Pro model and custom prompt.
    """
    prompt_template = """
    Answer the question in detail using the provided context. If the answer cannot be found 
    in the context or can't be answered with the knowledge you already have, respond with 
    'answer not available in the context'. Do not provide any misleading or made-up information
    until and unless the question requires you to generate content based on the given context.\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """

    # Initialize the Gemini Pro model with a slight randomness in responses
    model = ChatGoogleGenerativeAI(model="gemini-pro", temperature=0.7)
    
    # Create a prompt template for consistent questioning
    prompt = PromptTemplate(template=prompt_template, input_variables=["context", "question"])
    
    # Set up the QA chain with the model and prompt
    chain = load_qa_chain(model, chain_type="stuff", prompt=prompt)
    return chain

def user_input(user_question):
    """
    Process user input, search for relevant information, and generate a response.
    
    Args:
    user_question (str): The question input by the user.
    
    Side effect:
    Displays the AI-generated answer in the Streamlit app.
    """
    # Load the previously saved vector store
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
    
    # Perform a similarity search to find relevant document chunks
    docs = new_db.similarity_search(user_question)

    # Get the QA chain and run the query
    chain = get_conversational_chain()
    response = chain(
        {"input_documents": docs, "question": user_question},
        return_only_outputs=True
    )

    # Display the response in the Streamlit app
    print(response)  # For debugging purposes
    st.write(response["output_text"] + "\n\nNOTE:\nThese Responses are generated by AI so they may not be accurate, please verify the answers from the original sources")

def main():
    """
    Main function to set up and run the Streamlit app interface.
    This function defines the layout and interaction flow of the app.
    """
    # Configure the Streamlit page
    st.set_page_config("EDUHELPER", page_icon="📚")
    st.header("EDUHELPER: Chat with the PDF Files")

    # Main area for user input and displaying responses
    user_question = st.text_input("Ask a Question from the PDF Files")
    if user_question:
        user_input(user_question)

    # Sidebar for PDF upload and processing
    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader("Upload your PDF Files and Click on the Submit & Process Button", accept_multiple_files=True)
        if st.button("Submit & Process"):
            with st.spinner("Processing..."):
                raw_text = get_pdf_text(pdf_docs)
                text_chunks = get_text_chunks(raw_text)
                get_vector_store(text_chunks)
                st.success("Done")
    
    # Footer with creator information
    html_temp = """
    <div style="text-align: center; font-size: 14px; padding: 5px;">
    Created by Aritro Saha - 
    <a href="https://aritro.tech/">Website</a> | 
    <a href="https://github.com/halcyon-past">GitHub</a> | 
    <a href="https://www.linkedin.com/in/aritro-saha/">LinkedIn</a>
    </div>
    """
    st.markdown(html_temp, unsafe_allow_html=True)

# Entry point of the script
if __name__ == "__main__":
    main()