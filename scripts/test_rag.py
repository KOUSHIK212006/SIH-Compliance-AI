"""Deterministic tests for the local RAG/evidence retrieval foundation."""
import tempfile
from pathlib import Path

from src.rag import (
    DocumentLoaderError,
    DocumentMetadata,
    EmbeddingError,
    EvidenceChunk,
    HashEmbeddingProvider,
    LocalVectorStore,
    VectorStoreError,
    chunk_document,
    load_pdf,
    retrieve_evidence,
    retrieve_ingredient_evidence,
)


def _write_test_pdf(path: Path) -> None:
    """Write a tiny local PDF fixture labeled TEST DATA."""
    streams = [
        b"BT /F1 12 Tf 72 720 Td (TEST DATA: sodium benzoate preservative) Tj ET",
        b"BT /F1 12 Tf 72 720 Td (TEST DATA: citric acid acidity regulator) Tj ET",
    ]
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R 4 0 R] /Count 2 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 6 0 R >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 5 0 R >> >> /Contents 7 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(streams[0])).encode() + b" >>\nstream\n" + streams[0] + b"\nendstream",
        b"<< /Length " + str(len(streams[1])).encode() + b" >>\nstream\n" + streams[1] + b"\nendstream",
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{index} 0 obj\n".encode())
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode())
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode())
    output.extend(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())
    path.write_bytes(output)


def _run_tests():
    metadata = DocumentMetadata(
        document_id="test-regulation",
        title="TEST DATA - Local Food Additive Notes",
        source="local_test_fixture.pdf",
        source_type="test_data",
        authority="TEST_AUTHORITY",
        section="TEST SECTION",
        version="test-v1",
    )
    assert metadata.to_dict()["document_id"] == "test-regulation"

    provider = HashEmbeddingProvider(dimension=64)
    vectors = provider.embed_texts(["sodium benzoate preservative"])
    assert len(vectors) == 1 and len(vectors[0]) == 64
    assert len(provider.embed_query("preservative")) == 64
    try:
        provider.embed_query("")
        raise AssertionError("empty query should fail")
    except EmbeddingError:
        pass

    with tempfile.TemporaryDirectory() as temp_dir:
        root = Path(temp_dir)
        pdf_path = root / "test_fixture.pdf"
        _write_test_pdf(pdf_path)
        loaded = load_pdf(str(pdf_path), metadata)
        assert len(loaded["pages"]) == 2
        assert loaded["pages"][0]["page"] == 1
        assert "sodium benzoate" in loaded["pages"][0]["text"]
        assert loaded["metadata"]["source_type"] == "test_data"

        chunks = chunk_document(loaded, chunk_size=20, overlap=3)
        assert len(chunks) == 2
        assert all(chunk.document_id == "test-regulation" for chunk in chunks)
        assert [chunk.page for chunk in chunks] == [1, 2]
        assert all(chunk.metadata["authority"] == "TEST_AUTHORITY" for chunk in chunks)

        store_path = root / "vectors.json"
        store = LocalVectorStore(str(store_path), provider)
        store.add_documents(chunks)
        store.persist()
        assert store_path.exists()
        results = retrieve_evidence("sodium benzoate preservative", store, top_k=2)
        assert len(results) == 2
        assert results[0].rank == 1
        assert results[0].score >= results[1].score
        assert results[0].chunk.document_id == "test-regulation"
        assert results[0].chunk.page == 1
        assert results[0].chunk.source == "local_test_fixture.pdf"
        assert results[0].chunk.metadata["source_type"] == "test_data"

        ingredient_results = retrieve_ingredient_evidence("SODIUM BENZOATE", store, context="beverage", top_k=1)
        assert len(ingredient_results) == 1
        assert ingredient_results[0].chunk.document_id == "test-regulation"

        filtered = retrieve_evidence("citric acid", store, top_k=1, authority="TEST_AUTHORITY", source_type="test_data")
        assert filtered and filtered[0].chunk.page == 2

        loaded_store = LocalVectorStore(str(store_path), provider)
        loaded_store.load()
        assert loaded_store.similarity_search("preservative", top_k=1)[0].chunk.document_id == "test-regulation"

        missing_store = LocalVectorStore(str(root / "missing.json"), provider)
        try:
            missing_store.load()
            raise AssertionError("missing index should fail")
        except VectorStoreError:
            pass
        try:
            store.similarity_search("")
            raise AssertionError("empty query should fail")
        except VectorStoreError:
            pass

    try:
        load_pdf("missing-test-file.pdf")
        raise AssertionError("missing PDF should fail")
    except DocumentLoaderError:
        pass
    try:
        chunk_document({"metadata": {}, "pages": []})
        raise AssertionError("missing document ID should fail")
    except ValueError:
        pass

    print("All RAG tests passed.")


if __name__ == "__main__":
    _run_tests()
