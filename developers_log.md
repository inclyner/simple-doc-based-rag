#Developer Log
This developer log includes the main decisions and my reasoning for them




#random thoughts to organize later

i'll install fastapi and dockerize it once its up and running well
fast api is intalled, i'll think about the endpoints needed:
- (GET) /health ->health endpoint
- (POST) /files ->upload knowledge file
- (DELETE) /files/{doc_id} ->delete knowledge file
- (POST) /ask ->query llm

I'll be using LangChain, it already implements a lot of usefull features that i'll be using (i don't have to reinvent the wheel here):
- Document Loading
- Text splitting
- Embeddings
- Vector store
- Retrieval-Augmented QA Chain

I'm considering LangGraph overkill on this project, although after tests i might need the retries, but for now i'll keep it simple

i'll think about the unit tests now, after thinking about the tests it become easier to predict mistakes when programming:
- add file -> result is the creation of a new folder, the document in questions, and its generated metadata
- delete file -> result is the docs folder is deleted successfully
- ask a question that goes against its preceding knowledge, if a docs says that the sky is green, the llm should reply that the sky is green, this should be tested about 100 times, if this test doesnt pass the 100 tries, retries will ahve to be added
- ask a question out of scope, if the info is not on its knowledge base it should refuse with "i dont know"
- test for bad embeddings, synonims should work
- ask for info with a citation, check citation
- ask a question from deleted doc, -> shouldnt reply with that info

with these tests i can cover about 80% of the issues i can find with RAG systems

development of files.py
chose model intfloat/e5-base-v2 for embedding, fast, accurate in english, works on cpu
i'm using chroma, a vector database, runs offline, allows me to filter by metadata, and chroma's langchain adapter makes it simple to implement/read
made two docs with fake facts that go directly against common llm knowledge


#Next Steps
