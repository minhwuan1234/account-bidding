# Structural Chunker (bản local)

Ứng dụng Python chia PDF/DOCX theo cấu trúc tài liệu. Mỗi chunk gồm nội dung dưới **một tiêu đề gần nhất** cho đến tiêu đề kế tiếp, kèm đường dẫn mục, tên file và trang PDF. Bảng được giữ dưới dạng hàng/cột trong JSON. Chia tiếp theo ngữ nghĩa được bật mặc định; chủ đề của mỗi chunk được chọn từ chính nội dung chunk bằng embedding local. Sau đó ứng dụng chấm **tag chủ đề** và xếp chúng vào ba mức để quyết định tag nào đi tiếp. Không có giới hạn 500 token cho chunk. Phân tích và gợi ý chủ đề chạy local; bước gợi ý file và tạo bản tổng hợp dùng OpenAI API khi máy chủ có API key.

## Cài và chạy trên macOS

Cần Python 3.11 trở lên và kết nối Internet cho lần cài thư viện và tải mô hình đầu tiên. Mở Terminal tại thư mục này rồi chạy:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Mở [http://127.0.0.1:8765](http://127.0.0.1:8765). Thả một hoặc nhiều PDF/DOCX vào ô đầu trang hoặc bấm vào ô để chọn; phân tích bắt đầu tự động. Trong một lần chạy, ứng dụng **chia chunk, suy ra chủ đề và xếp tag vào approved và reject**. Tag Approved tự đi tiếp để gợi ý file. Trong lúc chờ, giao diện hiện một dòng tên các file đang được phân tích; khi hoàn tất, ứng dụng hiện **bản tổng hợp ngay trên màn hình chính** gồm phạm vi công việc, mốc thời gian, yêu cầu nộp và file đối chiếu. **Thư viện file** nằm ở tab riêng. Nhấn `Control+C` trong Terminal để dừng. Khi chạy local, ứng dụng chỉ lắng nghe `127.0.0.1`; bước gợi ý gửi text tag và mô tả Markdown tới OpenAI API.

### Semantic chunking

Chế độ **chia theo ngữ nghĩa trong từng mục** được bật mặc định với ngưỡng `0.85`. Tùy chọn này được ẩn khỏi giao diện. Mô hình mặc định là [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small), hỗ trợ nhiều ngôn ngữ. Lần dùng đầu tiên cần Internet để tải mô hình khoảng vài trăm MB vào bộ nhớ đệm của máy; sau đó việc chia ngữ nghĩa và suy ra chủ đề đều tính local. Bước chia ngữ nghĩa và suy ra chủ đề chạy trên máy; các lượt gợi ý file và tổng hợp gửi văn bản cần thiết tới OpenAI API.

## Thử nhanh

1. Mở tab **Thư viện file**, thêm `samples/sample.pdf` (có thể chọn nhiều file cùng lúc). Ứng dụng tự tạo mô tả Markdown; mở mục **Mô tả Markdown** để xem hoặc sửa.
2. Quay lại màn hình **Tổng quan bid**, thả `samples/sample.docx` vào ô tải file (cũng có thể thả nhiều file đầu vào cùng lúc). Đợi dòng trạng thái phân tích biến mất khi có kết quả.
3. Cấu hình `OPEN_AI_API_KEY` trên máy chủ. Gợi ý cho các tag `approved` sẽ chạy tự động. Xem text của từng tag, đánh dấu file muốn dùng, hoặc mở **Thêm file khác** để chọn file trong thư viện hay tải PDF/DOCX mới.
4. Xem bản tổng hợp ngay trên màn hình chính để xem yêu cầu, chọn hoặc tải thêm file cho từng yêu cầu, chỉnh trạng thái và in hoặc lưu PDF. Chạy kiểm thử bằng `python -m unittest -v`.


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

## Chọn tag để đi tiếp

Ứng dụng dùng embedding local để so **tên tag** với mô tả về yêu cầu và thông tin nền. Điểm 0–1 tính từ chênh lệch độ giống (`clamp(0.5 + margin / 0.12, 0, 1)`). Đây là điểm heuristic, không phải xác suất.

- `approved`: từ `0.50` trở lên, tự đi tiếp.
- `reject`: dưới `0.50`.

Không cần duyệt thủ công. Dữ liệu duyệt tag cũ trong SQLite được giữ nguyên nhưng không còn ảnh hưởng điểm chấm.

## Thư viện file và gợi ý theo tag

Trong **Thư viện file**, có thể chọn nhiều PDF/DOCX trong một lần và bấm **Lưu file**; ứng dụng lưu từng file riêng. Ứng dụng lưu nguyên file trong SQLite local (`data/tag_examples.sqlite3`) và **tự tạo mô tả Markdown** từ tiêu đề, câu và hàng bảng đại diện trong file. Mô tả này mang tính trích lọc, không phải bản tóm tắt do LLM viết; có thể sửa trong mục **Mô tả Markdown** của từng file. File và mô tả vẫn có ở lần mở ứng dụng sau. Bản ZIP không chứa database cá nhân.

Sau khi có tag `approved` và file trong thư viện, ứng dụng **tự gợi ý file** sau khi phân tích hoặc lưu file mới trong tab thư viện. Ứng dụng gửi text của từng tag (tối đa 30.000 ký tự cho mỗi tag) và **một mô tả Markdown cho mỗi file** trong thư viện tới OpenAI API. Model trả danh sách file có thể liên quan kèm lý do. Mục **File gợi ý theo tag** chỉ xuất hiện ở cuối màn hình chính sau khi bản tổng hợp hoàn tất và được thu gọn. Mở từng tag để xem text gốc, file gợi ý và đánh dấu file muốn giữ. Trong mục **Thêm file khác** của mỗi tag, bạn có thể chọn một file khác đã có trong thư viện hoặc tải thêm PDF/DOCX. File tải thêm được lưu vào thư viện, tự tạo mô tả Markdown và được chọn cho tag đó.

Bản tổng hợp và gợi ý file chỉ dùng các đoạn `approved`; các đoạn `reject` không đi tiếp. Danh sách yêu cầu hiển thị tên, trạng thái và file liên quan; mở từng mục để xem mô tả, nguồn và chỉnh file.

Để bật gợi ý trên máy cá nhân, mở `local_api_key.py` và dán key vào dòng `OPEN_AI_API_KEY = "..."`, sau đó tải lại trang. Nếu cài từ Git hoặc ZIP và chưa có file này, sao chép `local_api_key.example.py` thành `local_api_key.py` trước. File chứa key được Git bỏ qua và không nằm trong bản ZIP. Bạn cũng có thể đặt biến môi trường `OPEN_AI_API_KEY` trước khi chạy ứng dụng (tên `OPENAI_API_KEY` cũng được hỗ trợ); biến môi trường được ưu tiên. Key không xuất hiện trong giao diện, database hoặc JSON. Có thể đổi model bằng `OPENAI_MODEL` (mặc định `gpt-6-luna`). Các lượt gọi model gửi văn bản các đoạn tài liệu và mô tả Markdown, không gửi file nhị phân. Mỗi tag được gợi ý riêng; thời gian và chi phí phụ thuộc số tag và độ dài tài liệu.

Gợi ý chỉ dựa trên mô tả file; nó chưa xác nhận file đáp ứng yêu cầu. Bản tổng hợp trên màn hình chính dùng LLM để tổng hợp phạm vi, thời hạn và yêu cầu từ chunk Approved, liên kết từng yêu cầu với file có thể phù hợp. Bạn có thể chọn/bỏ file, tải thêm file và chỉnh trạng thái từng yêu cầu. Các lựa chọn ở bản tổng hợp được giữ trong phiên trình duyệt và trong JSON xuất ra; thư viện file và mô tả Markdown được lưu ở SQLite.

## Thời gian và chi phí mỗi lần chạy

Thời gian từ lúc bấm **Phân tích** đến khi gợi ý file và bản tổng hợp hoàn tất, cùng chi phí API ước tính bằng USD, vẫn được tính nội bộ nhưng không hiển thị trên màn hình chính. Mỗi lần bấm **Tạo lại** cũng được ghi thành một lượt riêng. Số lượt gọi model, token vào/ra và các lượt trước được giữ trong phiên trang hiện tại và kèm trong JSON xuất ra. Phân tích embedding local không phát sinh chi phí OpenAI API.

Chi phí được tính từ trường `usage` của từng phản hồi OpenAI Responses API. Với `gpt-6-luna` Standard, ứng dụng dùng đơn giá [$0,10/1 triệu token đầu vào, $0,01/1 triệu token đầu vào được cache, $0,125/1 triệu token ghi cache và $0,50/1 triệu token đầu ra](https://developers.openai.com/api/docs/models/gpt-6-luna). Nếu đổi sang model khác hoặc API không trả đủ dữ liệu, giao diện báo **Chưa xác định** thay vì hiển thị $0. Đây là ước tính, không phải số tiền thanh toán cuối cùng.

## Dữ liệu xuất

JSON có `schema_version: 10`, `documents` chứa toàn bộ chunk, `next_step_tags` chỉ chứa tag `approved`, `file_suggestions` chứa gợi ý cùng file đã chọn theo tag, và `bid_report` chứa bản tổng hợp cùng các chỉnh sửa file/trạng thái của bạn. Mỗi chunk giữ `file`, `section_path`, `pages`, `blocks` và `labels.topics`. `requirement_score`/`requirement_tier` là điểm và mức được tính tự động.

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

Khi bấm **Phân tích**, ứng dụng nhận file rồi xử lý trong nền; trang tự hỏi tiến độ và hiện chunk khi hoàn tất. Việc tải embedding model lần đầu có thể lâu hơn các lần sau nhưng không giữ một yêu cầu HTTP mở suốt quá trình. Nếu Railway thay phiên chạy giữa chừng, trang sẽ báo phiên phân tích đã mất và bạn có thể bấm **Phân tích** lại.

Railway dùng `Procfile` để chạy `python app.py`. Ứng dụng tự nghe trên `0.0.0.0` và cổng từ biến môi trường `PORT`; khi chạy trên máy cá nhân vẫn dùng `127.0.0.1:8765`. Nếu Railway đã có Start Command riêng, đặt nó thành `python app.py` hoặc bỏ giá trị cũ để Railpack đọc `Procfile`.

GitHub Actions secret `OPEN_AI_API_KEY` không tự chuyển sang Railway. Trong Railway, mở service **Variables**, thêm biến `OPEN_AI_API_KEY` với cùng giá trị và deploy thay đổi. File `local_api_key.py` chỉ dùng cho bản chạy trên máy cá nhân; không commit hoặc tải file này lên server.

SQLite trong thư mục `data/` là dữ liệu cục bộ của container. Nếu muốn giữ thư viện file và tag qua các lần deploy, cần gắn volume bền vững vào thư mục `data/` của ứng dụng. Giao diện hiện chưa có đăng nhập; chỉ nhập API key và tải tài liệu nhạy cảm khi bạn đã hạn chế quyền truy cập vào service.
