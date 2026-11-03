# Structural Chunker (bản local)

Ứng dụng Python chia PDF/DOCX theo cấu trúc tài liệu. Mỗi chunk gồm nội dung dưới **một tiêu đề gần nhất** cho đến tiêu đề kế tiếp, kèm đường dẫn mục, tên file và trang PDF. Bảng được giữ dưới dạng hàng/cột trong JSON. Chia tiếp theo ngữ nghĩa được bật mặc định; chủ đề của mỗi chunk được chọn từ chính nội dung chunk bằng embedding local. Sau đó ứng dụng chấm **tag chủ đề** và xếp chúng vào ba mức để quyết định tag nào đi tiếp. Không có giới hạn 500 token cho chunk. Phân tích và gợi ý chủ đề chạy local; chỉ bước gợi ý file bằng LLM mới gọi OpenAI API khi bạn chọn dùng và nhập API key.

## Cài và chạy trên macOS

Cần Python 3.11 trở lên và kết nối Internet cho lần cài thư viện và tải mô hình đầu tiên. Mở Terminal tại thư mục này rồi chạy:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Mở [http://127.0.0.1:8765](http://127.0.0.1:8765). Chọn một hoặc nhiều PDF/DOCX rồi bấm **Phân tích**. Trong một lần chạy, ứng dụng **chia chunk, suy ra chủ đề và xếp tag vào approved, considerable và reject**. Bạn có thể duyệt tag, thêm file vào thư viện SQLite local, nhận gợi ý từ model, chọn file và bấm **Xuất JSON**. Nhấn `Control+C` trong Terminal để dừng. Khi chạy local, ứng dụng chỉ lắng nghe `127.0.0.1`; bước gợi ý gửi text tag và mô tả Markdown tới OpenAI API.

### Semantic chunking

Chế độ **Chia theo ngữ nghĩa trong từng mục** được bật mặc định trong **Tùy chọn chia đoạn**. Ngưỡng giống nhau mặc định là `0.85`: tăng ngưỡng sẽ chia nhiều hơn, giảm ngưỡng sẽ giữ các đoạn gần nhau hơn. Mô hình mặc định là [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small), hỗ trợ nhiều ngôn ngữ. Lần dùng đầu tiên cần Internet để tải mô hình khoảng vài trăm MB vào bộ nhớ đệm của máy; sau đó việc chia ngữ nghĩa và suy ra chủ đề đều tính local. Không tải tài liệu của bạn lên dịch vụ ngoài.

## Thử nhanh

1. Thêm `samples/sample.pdf` vào **Thư viện file** (có thể chọn nhiều file cùng lúc). Ứng dụng tự tạo mô tả Markdown; mở mục **Mô tả Markdown** để xem hoặc sửa.
2. Chọn `samples/sample.docx` trong ô **Phân tích tài liệu** và bấm **Phân tích** (cũng có thể chọn nhiều file đầu vào cùng lúc). Giao diện hiện ba nhóm tag; rê chuột vào tag để xem nội dung chunk.
3. Cấu hình `OPEN_AI_API_KEY` trên máy chủ, rồi bấm **Gợi ý file** khi có tag `approved`. Xem text của từng tag, đánh dấu file gợi ý muốn dùng, hoặc mở **Thêm file khác** để chọn file trong thư viện hay tải PDF/DOCX mới.
4. Bấm **Xuất JSON** để lấy chunk, gợi ý và danh sách file bạn đã chọn. Chạy kiểm thử bằng `python -m unittest -v`.


Để thấy sự khác biệt của chế độ semantic, chọn `samples/semantic_sample.docx`. Với ngưỡng `0.85`, ứng dụng tách phần thiết kế và phần thanh toán thành 2 chunk dù chúng nằm dưới cùng một tiêu đề.

Các file mẫu đã có sẵn. `make_samples.py` chỉ cần dùng khi muốn tạo lại `sample.docx`, `sample.pdf` và `styleless_rfq.docx`; lúc đó cài thêm `reportlab` (`python -m pip install reportlab`).

## Quy tắc chia

- DOCX: nhận tiêu đề từ style Heading 1–6; nếu không có style, thử mẫu đánh số như `1.`, `1.2` hoặc `SECTION 1: ...`. Đọc đoạn văn và bảng đúng thứ tự trong tài liệu.
- PDF: lấy chữ và tọa độ bằng `pdfplumber`; đoán tiêu đề từ cỡ chữ, chữ đậm, đánh số hoặc mẫu `SECTION 1: ...`. Bảng có đường kẻ được tách và giữ hàng/cột. Số trang là trang PDF (bắt đầu từ 1).
- Mỗi tiêu đề bắt đầu một mục mới. Nội dung trước tiêu đề đầu tiên thuộc phần mở đầu. Không cắt tiếp theo độ dài.
- Nếu bật semantic, ứng dụng tách đoạn văn thành **từng câu**, tính embedding cho từng câu rồi so độ giống nhau của các câu liền kề **trong cùng mục**. Một điểm giảm cục bộ xuống dưới ngưỡng sẽ tạo ranh giới chunk mới; các câu liên quan được gom lại. Bảng luôn giữ nguyên hàng/cột và đi cùng phần nội dung trước nó. Không đặt trần kích thước cho chunk đầu ra.

## Nhãn chunk

Mỗi chunk có `labels.topics` với một chủ đề. Ứng dụng trích các cụm từ có thể làm chủ đề **từ chính nội dung chunk**, tính embedding cho các câu/hàng bảng và các cụm đó, rồi chọn cụm gần nhất với ý chính của chunk. Không có danh sách chủ đề cố định. Vì embedding không tự sinh chữ, chủ đề là một cụm **có trong tài liệu**, không phải câu mới do LLM viết. `labels.topic_details` lưu cụm được chọn, điểm giống nhau và đoạn bằng chứng; `labels.source` là `content_embedding`. Điểm giống nhau **không phải xác suất đúng**; cần rà soát với tài liệu thật.

Giao diện chỉ hiện các nhóm tag; nội dung chunk xuất hiện trong khung xem trước khi rê chuột vào tag. Tên file, nội dung từng chunk, `section_path`, trang và các metadata gốc vẫn được giữ trong JSON.

## Duyệt tag để chọn bước tiếp theo

Ứng dụng dùng cùng embedding model local để so **tên tag** với mô tả về yêu cầu và mô tả về thông tin nền. Bước này không so embedding của cả chunk. Điểm 0–1 được tính từ chênh lệch độ giống (`clamp(0.5 + margin / 0.12, 0, 1)`) và có thể được nâng bởi các tag bạn đã duyệt trước đó. Đây là điểm heuristic, **không phải xác suất**.

- `approved`: điểm từ `0.75` trở lên.
- `considerable`: từ `0.50` đến dưới `0.75`.
- `reject`: dưới `0.50`.

Chỉ tag `approved` xuất hiện trong `next_step_tags` để dùng cho bước sau. Cả ba nhóm vẫn hiện trên giao diện. Rê chuột vào tag để xem nội dung đoạn. Bấm tag để duyệt thủ công, chuyển nó lên `approved` và lưu tên cùng embedding tag trong SQLite local tại `data/tag_examples.sqlite3`. Bấm lần nữa để bỏ duyệt; tag trở về mức do máy chấm. Lần phân tích sau, embedding của tag mới được so với các tag mẫu bạn đã duyệt. Tag được máy xếp `approved` không tự lưu làm mẫu.

Các ngưỡng trên đang dùng thử và có thể cần chỉnh sau khi xem dữ liệu thật.

## Thư viện file và gợi ý theo tag

Trong **Thư viện file**, có thể chọn nhiều PDF/DOCX trong một lần và bấm **Lưu file**; ứng dụng lưu từng file riêng. Ứng dụng lưu nguyên file trong cùng SQLite local với tag đã duyệt (`data/tag_examples.sqlite3`) và **tự tạo mô tả Markdown** từ tiêu đề, câu và hàng bảng đại diện trong file. Mô tả này mang tính trích lọc, không phải bản tóm tắt do LLM viết; có thể sửa trong mục **Mô tả Markdown** của từng file. File và mô tả vẫn có ở lần mở ứng dụng sau. Bản ZIP không chứa database cá nhân.

Sau khi có tag `approved`, bấm **Gợi ý file**. Ứng dụng gửi text của từng tag (tối đa 30.000 ký tự cho mỗi tag) và **một mô tả Markdown cho mỗi file** trong thư viện tới OpenAI API. Model trả danh sách file có thể liên quan kèm lý do. Giao diện hiển thị tên tag, toàn bộ text tag và các file được gợi ý; bạn đánh dấu file muốn giữ. Trong mục **Thêm file khác** của mỗi tag, bạn có thể chọn một file khác đã có trong thư viện hoặc tải thêm PDF/DOCX. File tải thêm được lưu vào thư viện, tự tạo mô tả Markdown và được chọn cho tag đó.

Để bật gợi ý, đặt biến môi trường `OPEN_AI_API_KEY` trước khi chạy ứng dụng (tên `OPENAI_API_KEY` cũng được hỗ trợ). Key không xuất hiện trong giao diện, database hoặc JSON. Có thể đổi model bằng `OPENAI_MODEL` (mặc định `gpt-6-luna`). Cuộc gọi model chỉ gửi text tag và mô tả Markdown, không gửi file nhị phân. Mỗi tag được gọi riêng nên thời gian và chi phí phụ thuộc số tag `approved` và độ dài mô tả.

Gợi ý chỉ dựa trên mô tả file; nó chưa xác nhận file đáp ứng yêu cầu. Các lựa chọn file được giữ trong phiên trình duyệt hiện tại và có trong JSON xuất ra; thư viện file và mô tả Markdown được lưu ở SQLite.

## Dữ liệu xuất

JSON có `schema_version: 9`, `documents` chứa toàn bộ chunk, `next_step_tags` chỉ chứa tag `approved`, và `file_suggestions` chứa gợi ý cùng `selected_file_ids` của từng tag nếu đã chạy. Mỗi chunk giữ `file`, `section_path`, `pages`, `blocks` cùng `labels.topics`. Các trường `requirement_model_score`, `requirement_model_tier` lưu điểm/mức máy chấm; `requirement_score`, `requirement_tier` là kết quả sau khi duyệt thủ công; `approved_by_user` phân biệt lựa chọn của bạn.

## Giới hạn hiện tại

- PDF scan chỉ chứa ảnh cần OCR trước khi phân tích. PDF nhiều cột hoặc bảng không có đường kẻ có thể bị đọc sai thứ tự hoặc không nhận thành bảng.
- PDF không có cấu trúc Heading thực, nên việc nhận tiêu đề là heuristic và cần kiểm tra bằng mắt.
- Semantic chunking phụ thuộc vào ngưỡng, chất lượng mô hình và cách nhận ranh giới câu; cần xem lại các ranh giới trong JSON xuất ra. Mô hình chỉ đọc tối đa 512 token cho mỗi câu đầu vào. Một câu dài hơn giới hạn này có thể bị cắt khi tính embedding, dù nội dung xuất ra vẫn đầy đủ.
- Chủ đề được trích từ cụm từ trong chunk, nên có thể chưa diễn đạt trọn ý hoặc chọn một ý phụ khi chunk chứa nhiều chủ đề. Có thể cần cải thiện cách trích chủ đề ở các phiên bản sau.
- DOCX không cung cấp số trang ổn định trước khi dàn trang; `pages` sẽ là `[]`, `page_start`/`page_end` là `null`.
- Mục chỉ có tiêu đề và không có nội dung sẽ không sinh chunk riêng.

## Giao diện

Bố cục dashboard và bảng màu tham khảo nằm trong [design.md](design.md).

## Chạy trên Railway

Railway dùng `Procfile` để chạy `python app.py`. Ứng dụng tự nghe trên `0.0.0.0` và cổng từ biến môi trường `PORT`; khi chạy trên máy cá nhân vẫn dùng `127.0.0.1:8765`. Nếu Railway đã có Start Command riêng, đặt nó thành `python app.py` hoặc bỏ giá trị cũ để Railpack đọc `Procfile`.

GitHub Actions secret `OPEN_AI_API_KEY` không tự chuyển sang Railway. Trong Railway, mở service **Variables**, thêm biến `OPEN_AI_API_KEY` với cùng giá trị và deploy thay đổi. Không đưa giá trị key vào Git hoặc file trong project.

SQLite trong thư mục `data/` là dữ liệu cục bộ của container. Nếu muốn giữ thư viện file và tag qua các lần deploy, cần gắn volume bền vững vào thư mục `data/` của ứng dụng. Giao diện hiện chưa có đăng nhập; chỉ nhập API key và tải tài liệu nhạy cảm khi bạn đã hạn chế quyền truy cập vào service.
