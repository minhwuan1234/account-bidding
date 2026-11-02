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

Mở [http://127.0.0.1:8765](http://127.0.0.1:8765). Chọn một hoặc nhiều PDF/DOCX rồi bấm **Phân tích**. Trong một lần chạy, ứng dụng **chia chunk, suy ra chủ đề và xếp tag vào approved, considerable và reject**. Bạn có thể duyệt tag, thêm file sẵn có vào thư viện SQLite local, rồi đối chiếu và bấm **Xuất JSON**. Nhấn `Control+C` trong Terminal để dừng. Ứng dụng chỉ lắng nghe `127.0.0.1`; tệp không được gửi lên dịch vụ ngoài.

### Semantic chunking

Chế độ **Chia theo ngữ nghĩa trong từng mục** được bật mặc định trong **Tùy chọn chia đoạn**. Ngưỡng giống nhau mặc định là `0.85`: tăng ngưỡng sẽ chia nhiều hơn, giảm ngưỡng sẽ giữ các đoạn gần nhau hơn. Mô hình mặc định là [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small), hỗ trợ nhiều ngôn ngữ. Lần dùng đầu tiên cần Internet để tải mô hình khoảng vài trăm MB vào bộ nhớ đệm của máy; sau đó việc chia ngữ nghĩa và suy ra chủ đề đều tính local. Không tải tài liệu của bạn lên dịch vụ ngoài.

## Thử nhanh

1. Thêm `samples/sample.pdf` vào **Thư viện file** (có thể chọn nhiều file cùng lúc). Ứng dụng tự tạo mô tả Markdown; mở mục **Mô tả Markdown** để xem hoặc sửa.
2. Chọn `samples/sample.docx` trong ô **Phân tích tài liệu** và bấm **Phân tích** (cũng có thể chọn nhiều file đầu vào cùng lúc). Giao diện hiện ba nhóm tag; rê chuột vào tag để xem nội dung chunk.
3. Nếu có tag `approved`, chọn **Tôi tự chọn file**, đánh dấu `sample.pdf` trong thư viện và bấm **Đối chiếu**. Khi đã cấu hình OpenAI API key, thử **LLM gợi ý theo từng tag** để xem text đầy đủ và file LLM đề xuất cho mỗi tag.
4. Bấm **Xuất JSON** để xem chunk, nguồn và kết quả đối chiếu. Chạy kiểm thử bằng `python -m unittest -v`.


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

## Thư viện file và đối chiếu yêu cầu

Trong **Thư viện file**, có thể chọn nhiều PDF/DOCX trong một lần và bấm **Lưu file**; ứng dụng lưu từng file riêng. Ứng dụng lưu nguyên file trong cùng SQLite local với tag đã duyệt (`data/tag_examples.sqlite3`) và **tự tạo mô tả Markdown** từ tiêu đề, câu và hàng bảng đại diện trong file. Mô tả này mang tính trích lọc, không phải bản tóm tắt do LLM viết; có thể sửa trong mục **Mô tả Markdown** của từng file. File và mô tả vẫn có ở lần mở ứng dụng sau. Bản ZIP không chứa database cá nhân.

Sau khi có tag `approved`, bấm **Đối chiếu**. Chế độ mặc định **LLM gợi ý theo từng tag** gửi toàn bộ text của từng tag (tối đa 30.000 ký tự cho mỗi tag) cùng mô tả Markdown của các file trong thư viện tới OpenAI API. LLM chọn file có thể liên quan và giải thích lý do bằng JSON có cấu trúc. Giao diện hiển thị **tên tag, toàn bộ text tag, file được gợi ý và lý do** riêng cho từng tag. Sau đó ứng dụng đọc nội dung file được chọn và tìm bằng chứng cho từng câu yêu cầu. Bạn cũng có thể chọn **Tôi tự chọn file**, đánh dấu file trong thư viện để đối chiếu mà không gọi OpenAI API. Ứng dụng chỉ lấy câu/hàng bảng có dấu hiệu yêu cầu (`must`, `shall`, `submit`, `provide`, `deadline`, `phải`, `nộp`, v.v.) từ **chunk approved**.

Để bật LLM, nhập OpenAI API key trong ô **Kết nối** của ứng dụng. Key chỉ giữ trong bộ nhớ của phiên chạy, không lưu trong database hoặc JSON. Bạn cũng có thể đặt `OPENAI_API_KEY` trong môi trường trước khi chạy `python app.py`; đổi model bằng `OPENAI_MODEL` (mặc định `gpt-6-luna`). Nếu chưa có key, chế độ thủ công vẫn hoạt động. Cuộc gọi LLM chỉ gửi text tag và mô tả Markdown, không gửi file nhị phân. Mỗi tag được gọi riêng nên thời gian và chi phí phụ thuộc số tag `approved` và độ dài mô tả.

Kết quả có ba mức: **Có bằng chứng gần** (điểm ≥ `0.82`), **Cần kiểm tra** (`0.72–<0.82`) và **Chưa tìm thấy** (< `0.72`). Nếu con số trong yêu cầu không xuất hiện trong bằng chứng gần nhất, kết quả sẽ không tự báo là đã khớp. Các mốc này chỉ để sàng lọc và cần điều chỉnh với dữ liệu thật. Mỗi kết quả cho biết câu yêu cầu, tag nguồn, file được chọn, đoạn bằng chứng gần nhất, điểm giống và trang nguồn khi có.

**Có bằng chứng gần** chưa xác nhận bạn đáp ứng yêu cầu; **Chưa tìm thấy** chưa chứng minh chắc chắn file của bạn thiếu thông tin. Hãy kiểm tra bằng mắt, nhất là điều kiện về số lượng, thời hạn, mức kinh nghiệm và phủ định. Bước trích câu yêu cầu và tìm bằng chứng vẫn dùng quy tắc cùng embedding local, có thể bỏ sót yêu cầu không có từ khóa rõ ràng và có thể gợi ý nhầm file khi mô tả Markdown chưa đủ chi tiết.

## Dữ liệu xuất

JSON có `schema_version: 8`, `documents` chứa toàn bộ chunk, `next_step_tags` chỉ chứa tag `approved`, và `comparison` chứa kết quả đối chiếu nếu đã chạy. Mỗi chunk giữ `file`, `section_path`, `pages`, `blocks` cùng `labels.topics`. Các trường `requirement_model_score`, `requirement_model_tier` lưu điểm/mức máy chấm; `requirement_score`, `requirement_tier` là kết quả sau khi duyệt thủ công; `approved_by_user` phân biệt lựa chọn của bạn.

## Giới hạn hiện tại

- PDF scan chỉ chứa ảnh cần OCR trước khi phân tích. PDF nhiều cột hoặc bảng không có đường kẻ có thể bị đọc sai thứ tự hoặc không nhận thành bảng.
- PDF không có cấu trúc Heading thực, nên việc nhận tiêu đề là heuristic và cần kiểm tra bằng mắt.
- Semantic chunking phụ thuộc vào ngưỡng, chất lượng mô hình và cách nhận ranh giới câu; cần xem lại các ranh giới trong JSON xuất ra. Mô hình chỉ đọc tối đa 512 token cho mỗi câu đầu vào. Một câu dài hơn giới hạn này có thể bị cắt khi tính embedding, dù nội dung xuất ra vẫn đầy đủ.
- Chủ đề được trích từ cụm từ trong chunk, nên có thể chưa diễn đạt trọn ý hoặc chọn một ý phụ khi chunk chứa nhiều chủ đề. Có thể cần cải thiện cách trích chủ đề ở các phiên bản sau.
- DOCX không cung cấp số trang ổn định trước khi dàn trang; `pages` sẽ là `[]`, `page_start`/`page_end` là `null`.
- Mục chỉ có tiêu đề và không có nội dung sẽ không sinh chunk riêng.

## Giao diện

Bố cục dashboard và bảng màu tham khảo nằm trong [design.md](design.md).
