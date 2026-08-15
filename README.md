# Ontology-Grounded Traffic Sign Knowledge Graph

Đồ án biểu diễn và suy luận tri thức biển báo giao thông Việt Nam theo hướng
COKB, được grounding bằng OWL/RDF và kiểm chứng bằng SHACL.

MVP dùng annotation YOLO có sẵn làm bằng chứng. Nó không cần detection model
hay vector database để chạy ba bài toán suy luận cốt lõi. Trong hệ thống thực
tế, detector chỉ bổ sung candidate observations; Qdrant chỉ là projection tìm
kiếm tùy chọn và không phải nguồn chân lý ngữ nghĩa.

## Những gì đã chạy được

- COKB runtime với `(C,H,R,Ops,Funcs,Rules)`, 12 `FactKind`, forward chaining,
  goal heuristic, conflict detection và proof trace.
- OWL ontology cho visual evidence, sign occurrence, sign taxonomy, traffic
  rules, vehicle categories, problems và inference runs.
- Semantic catalog đủ 52 class IDs, gồm mapping status và OWL `hasValue`
  restrictions cho các lớp có meaning đã mô hình hóa.
- Ba problem types: `InterpretSign`, `EvaluateManeuver`,
  `EffectiveRestriction`.
- YOLO annotation adapter cho 3.216 ảnh / 8.334 boxes, không gọi model.
- RDF mapper tách `Image`, `ImageRegion`, `TrafficSignOccurrence` và
  `ClassificationAssertion`.
- SHACL validation với `ont_graph`, gold/invalid fixtures và luồng
  accepted/review/quarantine.
- Named-graph SPARQL queries và loader ontology/catalog cho Fuseki.
- FastAPI semantic endpoints và regression tests.

Trạng thái chi tiết: [docs/implement_state.md](docs/implement_state.md).
Kế hoạch chuẩn: [docs/cokb-implementation-plan.md](docs/cokb-implementation-plan.md).

## Chạy local

Yêu cầu Python 3.11–3.13:

```bash
uv venv --python 3.12
uv sync --extra dev --extra validation
cp .env.example .env
uv run traffic-sign-kg
```

API docs: `http://localhost:8000/docs`.

Ví dụ kết luận biển P.123b cấm ô tô con rẽ phải:

```bash
curl -X POST http://localhost:8000/api/v1/problems/evaluate-maneuver \
  -H 'content-type: application/json' \
  -d '{"class_id":32,"vehicle":"PassengerCar","maneuver":"TurnRight"}'
```

Giới hạn tốc độ P.127*50:

```bash
curl -X POST http://localhost:8000/api/v1/problems/effective-restriction \
  -H 'content-type: application/json' \
  -d '{"class_id":38}'
```

Kiểm tra profile và sample annotation:

```bash
curl http://localhost:8000/api/v1/ingestions/profile
curl -X POST 'http://localhost:8000/api/v1/ingestions/validate-sample?limit=5'
```

## Fuseki / RDF graph database

```bash
docker compose -f deployment/compose.yaml up -d fuseki
PYTHONPATH=src .venv/bin/python scripts/load_named_graphs.py
```

Loader nạp ontology và catalog vào hai named graphs riêng. Asserted, inferred,
review và quarantine graphs sẽ được ghi bởi ingestion/materialization pipeline ở
phase tiếp theo; query templates không phụ thuộc default-union graph.

## Kiểm thử

```bash
.venv/bin/ruff check src tests scripts
.venv/bin/pytest
```

## Semantic contract quan trọng

```text
Image --hasRegion--> ImageRegion --depicts--> TrafficSignOccurrence
ClassificationAssertion --assertionSubject--> TrafficSignOccurrence
ClassificationAssertion --assertedType--> OWL Sign Class
TrafficSignOccurrence --rdf:type--> OWL Sign Class   (chỉ khi Accepted)
TrafficSignOccurrence --conveysRule--> TrafficRule   (suy ra)
TrafficRule --prohibits/requires--> Maneuver
```

Không tìm thấy luật cấm dẫn đến `UNKNOWN`, không tự suy ra `PERMITTED`.
