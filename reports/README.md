# Báo cáo đồ án Ontology COKB

Tệp gốc: `main.tex`. Nội dung tiếng Việt, tập trung vào COKB trong source hiện có.
Thông tin học viên, mã số và giảng viên được giữ theo mẫu ban đầu; ngày báo cáo
được cập nhật sang tháng 9/2026.

## Biên dịch

Chạy từ thư mục `reports/`, chọn một trong hai cách:

~~~sh
latexmk -xelatex -interaction=nonstopmode -halt-on-error main.tex
~~~

~~~sh
tectonic --keep-logs main.tex
~~~

XeLaTeX dùng các font TeX Gyre Termes, Heros và Cursor trong TeX Live.
Trên Overleaf, đặt Main document là `main.tex` và compiler là XeLaTeX.
Nếu dùng pdfLaTeX, preamble có nhánh mã hóa T5; nhánh này chưa được kiểm tra biên dịch.
Không cần BibTeX/Biber vì tài liệu tham khảo nằm trong `references.tex`.

Bản PDF đã được biên dịch và kiểm tra bằng Tectonic 0.15.0 với bundle
TeX Live 2022.0r0. Nếu máy chủ bundle mặc định không truy cập được:

~~~sh
tectonic -w https://data1.fullyjustified.net/tlextras-2022.0r0.tar --keep-logs main.tex
~~~

## Cấu trúc

- `sections/01_problem.tex`: bài toán và ý nghĩa thực tế.
- `sections/02_knowledge_model.tex`: sáu thành phần COKB, ontology và ràng buộc.
- `sections/03_reasoning.tex`: toán tử, công thức năm luật, proof, độ phức tạp.
- `sections/04_implementation.tex`: kiến trúc, module, import/export và ví dụ.
- `sections/05_evaluation.tex`: dữ liệu, metrics, ma trận nhầm lẫn, biểu đồ, ca sai.
- `sections/06_discussion.tex`: đóng góp, giới hạn và hướng phát triển.
- `sections/07_reproduction.tex`: phụ lục lệnh chạy và đối chiếu source.
- `artifacts/`: kết quả thực nghiệm, log test, hash source/gold và store mẫu.

## Bổ sung hình

Đặt ảnh đúng tên; báo cáo tự thay khung mô tả bằng ảnh:

| File | Nội dung cần chụp hoặc vẽ |
|---|---|
| `images/cli_demo.png` | Truy vấn K05.1: hai mapping, mức A/UNASSESSED và rule ID. |
| `images/proof_graph.png` | Mapping → assessment; proof → assessment, rule, premise, evidence. Dùng tên cạnh đúng như Turtle. |
| `images/test_results.png` | Log test thật và metrics JSON. Hiện ghi nhận 18 đạt, 1 skip SHACL. |

Mỗi khung trong LaTeX có caption, label và mô tả cụ thể.
Hai sơ đồ TikZ và biểu đồ PGFPlots đã được vẽ, không cần ảnh ngoài.

## Tái lập số liệu

Từ thư mục gốc repo:

~~~sh
.venv/bin/python reports/scripts/collect_evidence.py
~~~

Script lưu `artifacts/summary.json`, `evaluation.json`, `unit_tests.txt`,
query/explain JSON và `demo/`. Mỗi lần chạy ghi lại các artifact này.
Các bảng/biểu đồ trong LaTeX là snapshot được đối chiếu với lần chạy cho báo cáo;
nếu thay code hoặc gold, phải cập nhật cả bảng, biểu đồ và phần nhận xét.

Kết quả hiện tại: 500 cặp, 22 được đánh giá, 21 đúng, 478 UNASSESSED.
Graph nguồn còn là LFS pointer; graph store đọc được 0 quad ở lần kiểm tra.
SHACL có code và test tùy chọn nhưng bị skip trong môi trường dùng để thu thập số liệu.

Tài liệu tham khảo đã kiểm tra từ bài báo gốc và W3C. Các công thức đánh giá,
chuẩn hóa và khớp luật được mô hình hóa từ code, không gán cho bài báo COKB.
