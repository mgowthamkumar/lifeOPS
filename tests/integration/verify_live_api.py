import httpx

def main():
    client = httpx.Client(base_url="http://127.0.0.1:8000", timeout=15.0)

    # 1. Create collection
    col_res = client.post("/api/collections", json={
        "name": "Live Verification Collection",
        "description": "Verifying live multi-format document pipeline",
    })
    assert col_res.status_code == 201, f"Failed to create collection: {col_res.text}"
    col = col_res.json()
    col_id = col["id"]
    print(f"1. Created Collection: '{col['name']}' (ID: {col_id})")

    # 2. Upload and process real document
    doc_text = b"AI Engineer Candidate: 3 years Python, PyTorch, ChromaDB vector indexing, and FastAPI development."
    upload_res = client.post(
        "/api/documents/upload",
        data={"collection_id": col_id},
        files={"file": ("candidate_profile.txt", doc_text, "text/plain")},
    )
    assert upload_res.status_code == 201, f"Upload failed: {upload_res.text}"
    doc = upload_res.json()
    doc_id = doc["id"]
    print(f"2. Uploaded Document: '{doc['filename']}' | Status: {doc['status']} | Chunks: {doc['chunk_count']}")

    # 3. Retrieve details and chunks
    detail_res = client.get(f"/api/documents/{doc_id}")
    assert detail_res.status_code == 200
    detail = detail_res.json()
    first_chunk = detail["chunks"][0]
    print(f"3. Retrieved Details: {len(detail['chunks'])} chunks | First Chunk Vector ID: {first_chunk['vector_id']}")

    # 4. Reprocess document
    reprocess_res = client.post(f"/api/documents/{doc_id}/reprocess")
    assert reprocess_res.status_code == 200
    print(f"4. Reprocessed Document: Status={reprocess_res.json()['status']}")

    # 5. Update document to v2
    v2_text = b"AI Engineer Candidate v2: Added production Docker, LangChain, and advanced RAG architectures."
    update_res = client.put(
        f"/api/documents/{doc_id}/update",
        files={"file": ("candidate_profile_v2.txt", v2_text, "text/plain")},
    )
    assert update_res.status_code == 200
    updated_doc = update_res.json()
    print(f"5. Updated to v{updated_doc['current_version']}: '{updated_doc['filename']}' | Status: {updated_doc['status']}")

    # 6. Delete document
    del_doc_res = client.delete(f"/api/documents/{doc_id}")
    assert del_doc_res.status_code == 204
    print("6. Deleted Document & Purged Vectors from ChromaDB: 204 No Content")

    # 7. Delete collection
    del_col_res = client.delete(f"/api/collections/{col_id}")
    assert del_col_res.status_code == 204
    print("7. Deleted Collection & Cleaned ChromaDB Collection: 204 No Content")

    print("\nALL 7 LIVE API PIPELINE STEPS VERIFIED SUCCESSFULLY!")

if __name__ == "__main__":
    main()
