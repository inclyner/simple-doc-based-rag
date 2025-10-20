#Developer Log
This developer log includes the main decisions and my reasoning for them




#random thoughts to organize later

i'll install fastapi and dockerize it once its up and running well
update: For simplicity, this project runs directly with uvicorn. Dockerization was omitted to keep the setup lightweight, but the application can be containerized easily if needed

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
- delete file -> result is the docs folder is deleted successfully along with the data on chromadb
- ask a question that goes against its preceding knowledge, if a docs says that the sky is green, the llm should reply that the sky is green, this should be tested about 100 times, if this test doesnt pass the 100 tries, retries will have to be added
- ask a question out of scope, if the info is not on its knowledge base it should refuse with "this information is not available in my current knowledge base."
- test for bad embeddings, synonims should work
- ask a question from deleted doc, -> shouldnt reply with that info

with these tests i can cover about 80% of the issues i can find with RAG systems

development of files.py
chose model intfloat/e5-base-v2 for embedding, fast, accurate in english, works on cpu
i'm using chroma, a vector database, runs offline, allows me to filter by metadata, and chroma's langchain adapter makes it simple to implement/read
made two docs with fake facts that go directly against common llm knowledge

development of ask.py
i'll be using "TNG: DeepSeek R1T2 Chimera (free)" it's fast, it's free, and it's in the top free weekly llms , i'll be uploading the .env file to git because i have a free api key, otherwise it'd be local only
for the RAG i'll be using the top 4 most relevant documents (K=4), although this depends on what data is in the db, if the data is dense i'd choose closer to 2 or even 1 for extreme cases, the llm will be called with temperature 0 so the results are reliable

endpoint is complete and answergin only based on provided context
i will now implement the tests to make sure everything is working correctly
after understandign that with temperature 0 the model will always reply the same, i'll remove the 100x test, which now seems to be unnecessary
the synonym test is failing so i'll activate the huggingfaceEmbeddings normalize embaddings setting


#Next Steps

Market research into various areas where this technology might be useful, develop the front end with the industry in mind (some industries might be more accustomed to certain types of frontends and ux's)
make the product scalable, implement streaming responses, research cost effective models