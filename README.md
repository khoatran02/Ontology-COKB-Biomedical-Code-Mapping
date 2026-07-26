# Ontology-Grounded Traffic Sign Knowledge Graph

Backend nền cho hệ thống biểu diễn, kiểm chứng, suy luận và truy xuất lai biển báo
giao thông Việt Nam.

Kiến trúc lưu trữ:

- Apache Jena Fuseki/TDB2 là nguồn chân lý RDF/OWL.
- FAISS là vector index dẫn xuất.
- SQLite lưu job, ánh xạ `faiss_id ↔ rdf_uri` và index manifest.
- File system lưu ảnh/crop. Base source chưa ingest dataset.

## Chạy local

Yêu cầu Python 3.11–3.13. Ví dụ với `uv`:

```bash
uv venv --python 3.12
uv sync --extra dev --extra validation
cp .env.example .env
uv run traffic-sign-kg
```

Mở:

```text
http://localhost:8000/docs
http://localhost:8000/api/v1/health/live
http://localhost:8000/api/v1/health/ready
```

Khởi động Fuseki:

```bash
docker compose -f deployment/compose.yaml up -d fuseki
```

Nạp ontology nền:

```bash
./scripts/load_ontology.sh
```

## Smoke test không cần dataset/model

Development profile có `DeterministicEmbeddingProvider`. Provider này chỉ tạo vector ổn
định từ text để kiểm tra pipeline; không được dùng làm kết quả nghiên cứu.

```bash
curl -X POST http://localhost:8000/api/v1/vector-indexes/ontology-concepts/rebuild \
  -H 'content-type: application/json' \
  -d '{
    "dimension": 64,
    "model_id": "deterministic-dev",
    "model_revision": "v1",
    "items": [
      {
        "rdf_uri": "https://example.org/traffic-sign-kg/ontology#ProhibitionSign",
        "entity_type": "ontology_class",
        "text": "biển báo cấm"
      }
    ]
  }'
```

Sau đó:

```bash
curl -X POST http://localhost:8000/api/v1/search/vector \
  -H 'content-type: application/json' \
  -d '{
    "index_name": "ontology-concepts",
    "text": "biển cấm",
    "candidate_limit": 10
  }'
```

## Dataset và model thật

Dataset adapter, YOLO parsing, crop generation và pretrained embedding model được để
ở phase tiếp theo. Các adapter phải tạo stable RDF URI và `VectorBuildItem`; không ghi
ontology fact trực tiếp vào FAISS.

Tài liệu chi tiết:

- [Architecture](docs/architecture.md)
- [Proposal](docs/Ontology-Grounded-Traffic-Sign-Knowledge-Graph-Proposal.md)

