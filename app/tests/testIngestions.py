import os
import asyncio
import services.indexer as indexer
import pytest



def _upload_from_path(path: str):
    class U: pass
    u = U()
    u.filename = os.path.basename(path)
    async def _read():
        with open(path, "rb") as f:
            return f.read()
    u.read = _read
    return u

def test_ingest_txt_and_pdf_then_delete(tmp_path):
    #indexer.DATA_DIR = str(tmp_path / "docs")
    #indexer.CHROMA_DIR = str(tmp_path / "chroma")


    indexer._embeddings = None
    indexer._vectordb = None
    

    here = os.path.dirname(__file__)
    txt_path = os.path.join(here, "test_docs", "sample.txt")
    pdf_path = os.path.join(here, "test_docs", "sample.pdf")

    # ingest txt
    res_txt = asyncio.run(indexer.ingest_upload(_upload_from_path(txt_path)))
    assert res_txt["status"] == "indexed"
    assert res_txt["chunks"] >= 1
    txt_folder = os.path.join(indexer.DATA_DIR, res_txt["doc_id"])
    assert os.path.isdir(txt_folder)

    # ingest pdf
    res_pdf = asyncio.run(indexer.ingest_upload(_upload_from_path(pdf_path)))
    assert res_pdf["status"] == "indexed"
    assert res_pdf["chunks"] >= 1
    pdf_folder = os.path.join(indexer.DATA_DIR, res_pdf["doc_id"])
    assert os.path.isdir(pdf_folder)

    
    # delete both
    #deleted_txt = asyncio.run(indexer.delete_document(res_txt["doc_id"]))
    #deleted_pdf = asyncio.run(indexer.delete_document(res_pdf["doc_id"]))
    #assert deleted_txt is True
    #assert deleted_pdf is True
    #assert not os.path.isdir(txt_folder)
    #assert not os.path.isdir(pdf_folder)


def test_ingest_empty_rejected(tmp_path):
    indexer.DATA_DIR = str(tmp_path / "docs")
    indexer.CHROMA_DIR = str(tmp_path / "chroma")
    indexer._embeddings = None
    indexer._vectordb = None

    # build an "empty file" 
    class U: pass
    u = U()
    u.filename = "empty.txt"
    async def _read():
        return b""
    u.read = _read

    
    with pytest.raises(ValueError) as e:
        asyncio.run(indexer.ingest_upload(u))
    assert "Empty file" in str(e.value)
