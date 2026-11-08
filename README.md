# Structural Chunker (bản local)

## Cấu trúc mã nguồn

```text
app.py                 Điểm khởi chạy
frontend/              HTML, CSS, JavaScript và HTTP handler
business/              Đọc tài liệu, chunking, tag, gợi ý file, tạo báo cáo
database/              Lưu file trong MySQL trên Railway hoặc SQLite local
data/                  SQLite local (không đưa lên Git)
test_*.py              Bài kiểm tra
```

Luồng phụ thuộc: `frontend → business → database`. `app.py` chỉ khởi chạy máy chủ. File tĩnh được phục vụ từ `frontend/` qua `/app.js`, `/styles.css` và `/favicon.svg`.

Tab **Lịch sử bid** lưu mỗi lượt phân tích thành một bản ghi trong SQLite local hoặc MySQL trên Railway. Bản ghi gồm các tài liệu đã xử lý, bản tổng hợp và file thư viện đã chọn. Mở lại bid để chọn thêm file cho mục còn thiếu; thay đổi được lưu ngay. File gốc của tài liệu RFP và thư viện vẫn ở các bảng tài liệu riêng.

### Kết nối Railway MySQL

Ứng dụng nhận `MYSQL_URL` từ service Railway, hoặc bộ biến `MYSQLHOST`, `MYSQLPORT`, `MYSQLUSER`, `MYSQLPASSWORD`, `MYSQLDATABASE`. Trong Railway, thêm biến tham chiếu từ MySQL service vào **service ứng dụng** (ví dụ `MYSQL_URL=${{MySQL.MYSQL_URL}}`). Gọi `GET /api/database-status` để thử kết nối bằng `SELECT 1`; phản hồi chỉ có `configured` và `connected`, không trả về mật khẩu.

Khi chạy trên Railway, mọi PDF/DOCX tải lên để **phân tích RFP** hoặc thêm vào **Thư viện file** được lưu trong MySQL cùng tóm tắt nội dung. Bản gốc được chia thành các phần nhị phân tối đa 1 MiB để ghi trong một giao dịch; bảng được tạo tự động lần đầu. RFP được lưu ngay khi nhận upload và được cập nhật tóm tắt khi bắt đầu phân tích. Nếu chưa trích xuất được chữ, tóm tắt ghi rõ cần kiểm tra/OCR. Nếu Railway thiếu cấu hình MySQL, upload báo lỗi thay vì ghi vào SQLite tạm.

Trên máy local không có biến MySQL, ứng dụng tiếp tục lưu vào SQLite `data/tag_examples.sqlite3`. Endpoint `/api/database-status` khi đó trả `{"configured": false, "connected": false}`. Tag mẫu vẫn dùng SQLite. **File đã lưu trong SQLite trước đây không tự chuyển sang MySQL**; cần tải lại lên Railway nếu muốn đưa chúng vào database đó.

Ứng dụng Python chia PDF/DOCX theo cấu trúc tài liệu. Mỗi chunk gồm nội dung dưới **một tiêu đề gần nhất** cho đến tiêu đề kế tiếp, kèm đường dẫn mục, tên file và trang PDF. Bảng được giữ dưới dạng hàng/cột trong JSON. Chia tiếp theo ngữ nghĩa được bật mặc định; chủ đề của mỗi chunk được chọn từ chính nội dung chunk bằng embedding OpenAI API. Sau đó ứng dụng chấm **tag chủ đề** và xếp chúng vào ba mức để quyết định tag nào đi tiếp. Không có giới hạn 500 token cho chunk. Chia tài liệu chạy trên máy chủ; embedding, gợi ý file và tạo bản tổng hợp dùng OpenAI API khi máy chủ có API key.

## Cài và chạy trên macOS

Cần Python 3.11 trở lên và kết nối Internet cho lần cài thư viện và tải mô hình đầu tiên. Mở Terminal tại thư mục này rồi chạy:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

Mở [http://127.0.0.1:8765](http://127.0.0.1:8765). Thả một hoặc nhiều PDF/DOCX vào ô đầu trang hoặc bấm vào ô để chọn, sau đó bấm nút xanh **Phân tích tài liệu** để xác nhận chạy. Trong một lần chạy, ứng dụng **chia chunk, suy ra chủ đề và xếp tag vào approved và reject**. Mọi tag đều được xét để gợi ý file; điểm Approved/Reject chỉ được giữ làm thông tin tham khảo. Trong lúc chờ, giao diện hiện một dòng tên các file đang được phân tích; khi hoàn tất, ứng dụng hiện **bản tổng hợp ngay trên màn hình chính** gồm phạm vi công việc, mốc thời gian, yêu cầu nộp và file đối chiếu. **Thư viện file** nằm ở tab riêng. Nhấn `Control+C` trong Terminal để dừng. Khi chạy local, ứng dụng chỉ lắng nghe `127.0.0.1`; bước gợi ý gửi text tag và mô tả Markdown tới OpenAI API.

Phần **Phạm vi công việc** luôn có sáu mục: mục tiêu chính của project, hình thức hợp đồng, bên cung cấp nội dung chuyên môn, hình thức nộp thầu, cách chấm điểm và đánh giá hồ sơ, và chi tiết cùng khối lượng công việc. Các mục dùng `gpt-6-luna` và chạy đồng thời. Riêng mục cách chấm điểm quét toàn bộ tài liệu theo các đợt nhỏ, kể cả chunk bị tag reject; từng quy tắc xét chọn phải có câu trích nguyên văn từ nguồn. Mục không có bằng chứng sẽ hiện “Hồ sơ không nêu rõ.” Khối lượng và tỷ trọng điểm không được tự suy đoán.

Phần **Các mốc** có một lượt đọc `gpt-6-luna` riêng chạy cùng lúc với các mục trên. Model nhận diện ngày gốc và quan hệ như “5 ngày trước hạn nộp”; ứng dụng tính ra ngày/tháng/năm bằng lịch nếu ngày gốc có đủ năm. Giờ và múi giờ của ngày ghi trực tiếp được giữ nguyên, không tự chuyển sang mốc tính toán. Với thời hạn “2 ngày sau khi nhận câu hỏi”, ngày suy ra từ hạn gửi câu hỏi được gắn nhãn **Theo điều kiện** và ghi rõ giả định nhận câu hỏi đúng ngày hạn gửi. Nếu thiếu ngày gốc, ứng dụng giữ nguyên thời hạn tương đối.

Trước phần **Tài liệu cần nộp**, **Câu hỏi nháp** hiện dưới dạng gạch đầu dòng khi thiếu bằng chứng về mục tiêu dự án, đối tượng xem/học/sử dụng, deadline hoàn thành dự án, cách nộp thầu hoặc phạm vi công việc. Mục đã có thông tin sẽ không sinh câu hỏi.

Phần **Tài liệu cần nộp** có lượt đọc Luna riêng quét toàn bộ tài liệu đầu vào theo từng phần, gồm cả đoạn bị xếp tag `reject`, để tìm từng giấy tờ phải nộp trong đoạn văn và bảng. Chỉ có hai nhóm cố định: **Hồ sơ công ty** (pháp lý, năng lực công ty/nhân sự, CV, kinh nghiệm, sản phẩm và dịch vụ) và **Proposal** (đề xuất cho dự án, kế hoạch, timeline, báo giá). Sau khi lọc các mục không có câu nguồn nguyên văn, một lượt Luna rà soát tên tương đương, gộp mục trùng và phân loại lại; mục nào bị lượt rà soát bỏ sót vẫn được giữ. Các lượt đọc tài liệu chạy cùng lúc với các mục SOW và các mốc.

### Semantic chunking

Chế độ **chia theo ngữ nghĩa trong từng mục** được bật mặc định với ngưỡng `0.85`. Tùy chọn này được ẩn khỏi giao diện. Mô hình mặc định là [`intfloat/multilingual-e5-small`](https://huggingface.co/intfloat/multilingual-e5-small), hỗ trợ nhiều ngôn ngữ. Lần dùng đầu tiên cần Internet để tải mô hình khoảng vài trăm MB vào bộ nhớ đệm của máy; sau đó việc chia ngữ nghĩa và suy ra chủ đề đều tính local. Bước chia ngữ nghĩa và suy ra chủ đề chạy trên máy; các lượt gợi ý file và tổng hợp gửi văn bản cần thiết tới OpenAI API.

## Thử nhanh

1. Mở tab **Thư viện file**, thêm `samples/sample.pdf` (có thể chọn nhiều file cùng lúc). Ứng dụng tự tạo mô tả Markdown; mở mục **Mô tả Markdown** để xem hoặc sửa.
2. Quay lại màn hình **Tổng quan bid**, thả `samples/sample.docx` vào ô tải file (cũng có thể thả nhiều file đầu vào cùng lúc), rồi bấm **Phân tích tài liệu**. Đợi dòng trạng thái phân tích biến mất khi có kết quả.
3. Cấu hình `OPEN_AI_API_KEY` trên máy chủ. Thêm PDF/DOCX vào tab **Thư viện file** để tự chọn cho từng tài liệu cần nộp.
4. Xem **Tài liệu cần nộp** trên màn hình chính, mở từng yêu cầu để chọn file liên quan từ thư viện. Nhãn **Có rồi/Thiếu** cập nhật theo lựa chọn. Hai nút **Tạo lại** và **In / Lưu PDF** nằm ở cuối báo cáo. Chạy kiểm thử bằng `python -m unittest -v`.


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

Ứng dụng dùng embedding OpenAI API để so **tên tag** với mô tả về yêu cầu và thông tin nền. Điểm 0–1 tính từ chênh lệch độ giống (`clamp(0.5 + margin / 0.12, 0, 1)`). Đây là điểm heuristic, không phải xác suất.

- `approved`: từ `0.50` trở lên.
- `reject`: dưới `0.50`.

Cả hai nhóm đều được xét ở bước gợi ý file và tạo bản tổng hợp; không bắt buộc phải có tag `approved`.

Không cần duyệt thủ công. Dữ liệu duyệt tag cũ trong SQLite được giữ nguyên nhưng không còn ảnh hưởng điểm chấm.

## Thư viện file và gợi ý theo tag

Trong **Thư viện file**, có thể chọn nhiều PDF/DOCX trong một lần và bấm **Lưu file**; ứng dụng lưu từng file riêng cùng **tóm tắt Markdown** trích từ tiêu đề, câu và hàng bảng đại diện. Đây là bản tóm tắt trích lọc, không phải bản do LLM viết; có thể sửa trong mục **Tóm tắt nội dung tài liệu**. File và tóm tắt vẫn có ở lần mở ứng dụng sau. Trên Railway chúng nằm trong MySQL, còn bản local mặc định dùng SQLite. Bản ZIP không chứa database cá nhân.

Sau khi có tag và file trong thư viện, ứng dụng **tự đối chiếu file theo tag**. Ứng dụng gửi text của từng tag (tối đa 30.000 ký tự cho mỗi tag) và **một mô tả Markdown cho mỗi file** trong thư viện tới OpenAI API. Kết quả đối chiếu được dùng nội bộ khi tạo báo cáo; danh sách gợi ý theo từng tag không hiển thị trên giao diện. Người dùng có thể chỉnh file liên quan trực tiếp trong từng mục **Tài liệu cần nộp** của báo cáo và tải thêm PDF/DOCX trong tab thư viện.

Phần **Tài liệu cần nộp** quét cả các đoạn `reject` để không bỏ sót giấy tờ do bước phân loại tag. Danh sách hiển thị thành hai cột cố định; người dùng mở từng mục để xem nguồn và tự chọn file liên quan.

Để bật gợi ý trên máy cá nhân, mở `local_api_key.py` và dán key vào dòng `OPEN_AI_API_KEY = "..."`, sau đó tải lại trang. Nếu cài từ Git hoặc ZIP và chưa có file này, sao chép `local_api_key.example.py` thành `local_api_key.py` trước. File chứa key được Git bỏ qua và không nằm trong bản ZIP. Bạn cũng có thể đặt biến môi trường `OPEN_AI_API_KEY` trước khi chạy ứng dụng (tên `OPENAI_API_KEY` cũng được hỗ trợ); biến môi trường được ưu tiên. Key không xuất hiện trong giao diện, database hoặc JSON. Có thể đổi model bằng `OPENAI_MODEL` (mặc định `gpt-6-luna`). Các lượt gọi model gửi văn bản các đoạn tài liệu và mô tả Markdown, không gửi file nhị phân. Mỗi tag được gợi ý riêng; thời gian và chi phí phụ thuộc số tag và độ dài tài liệu.

Bản tổng hợp trên màn hình chính dùng LLM để đọc tài liệu đầu vào và trích các giấy tờ cần nộp. Ứng dụng tạm thời không đối chiếu tag với thư viện hoặc tự gợi ý file; người dùng chọn file cho từng mục. Các lựa chọn được lưu cùng bid; thư viện file và mô tả Markdown được lưu trong database đã cấu hình.

Trong lúc chạy, mục **Tiến độ xử lý** hiển thị bước đọc/chia/tag từng file và trạng thái các phần của báo cáo. Báo cáo chạy tối đa 4 lời gọi model đồng thời để giảm nguy cơ HTTP 429. Khi OpenAI trả 429, ứng dụng hiện mã lỗi cụ thể nếu API có trả về; lỗi giới hạn tốc độ và lỗi hạn mức thanh toán cần xử lý khác nhau.

## Thời gian và chi phí mỗi lần chạy

Thời gian từ lúc bấm **Phân tích** đến khi gợi ý file và bản tổng hợp hoàn tất, cùng chi phí API ước tính bằng USD, vẫn được tính nội bộ nhưng không hiển thị trên màn hình chính. Mỗi lần bấm **Tạo lại** cũng được ghi thành một lượt riêng. Số lượt gọi model, token vào/ra và các lượt trước được giữ trong phiên trang hiện tại và kèm trong JSON xuất ra. Chi phí embedding API chưa được cộng vào số tiền ước tính này.

Chi phí được tính từ trường `usage` của từng phản hồi OpenAI Responses API. Với `gpt-6-luna` Standard, ứng dụng dùng đơn giá [$0,10/1 triệu token đầu vào, $0,01/1 triệu token đầu vào được cache, $0,125/1 triệu token ghi cache và $0,50/1 triệu token đầu ra](https://developers.openai.com/api/docs/models/gpt-6-luna). Nếu đổi sang model khác hoặc API không trả đủ dữ liệu, giao diện báo **Chưa xác định** thay vì hiển thị $0. Đây là ước tính, không phải số tiền thanh toán cuối cùng.

## Dữ liệu xuất

JSON có `schema_version: 10`, `documents` chứa toàn bộ chunk, `next_step_tags` chứa mọi tag được xét tiếp, `file_suggestions` chứa gợi ý cùng file đã chọn theo tag, và `bid_report` chứa bản tổng hợp cùng các chỉnh sửa file/trạng thái của bạn. Mỗi chunk giữ `file`, `section_path`, `pages`, `blocks` và `labels.topics`. `requirement_score`/`requirement_tier` là điểm và mức được tính tự động.

## Giới hạn hiện tại

- PDF scan chỉ chứa ảnh cần OCR trước khi phân tích. PDF nhiều cột hoặc bảng không có đường kẻ có thể bị đọc sai thứ tự hoặc không nhận thành bảng.
- PDF không có cấu trúc Heading thực, nên việc nhận tiêu đề là heuristic và cần kiểm tra bằng mắt.
- Semantic chunking phụ thuộc vào ngưỡng, chất lượng mô hình và cách nhận ranh giới câu; cần xem lại các ranh giới trong JSON xuất ra. Văn bản dài được chia thành nhiều lượt gửi embedding và gộp vector theo số token. Ngưỡng tương đồng cũ cần được đánh giá lại với model mới.
- Chủ đề được trích từ cụm từ trong chunk, nên có thể chưa diễn đạt trọn ý hoặc chọn một ý phụ khi chunk chứa nhiều chủ đề. Có thể cần cải thiện cách trích chủ đề ở các phiên bản sau.
- DOCX không cung cấp số trang ổn định trước khi dàn trang; `pages` sẽ là `[]`, `page_start`/`page_end` là `null`.
- Mục chỉ có tiêu đề và không có nội dung sẽ không sinh chunk riêng.

## Giao diện

Bố cục dashboard và bảng màu tham khảo nằm trong [design.md](design.md).

## Chạy trên Railway

Khi bấm **Phân tích**, ứng dụng nhận file rồi xử lý trong nền; trang tự hỏi tiến độ và hiện chunk khi hoàn tất. Embedding được gửi theo lô tới OpenAI API. Nếu Railway thay phiên chạy giữa chừng, trang sẽ báo phiên phân tích đã mất và bạn có thể bấm **Phân tích** lại.

Embedding sử dụng OpenAI API với model `text-embedding-3-small` (đổi bằng biến `OPENAI_EMBEDDING_MODEL`). Cần cấu hình `OPEN_AI_API_KEY` trên máy chủ. Văn bản được gửi tới OpenAI để tạo embedding; việc này phát sinh chi phí API và ngưỡng chia đoạn cần được đánh giá lại với model mới.

Railway dùng `Procfile` để chạy `python app.py`. Ứng dụng tự nghe trên `0.0.0.0` và cổng từ biến môi trường `PORT`; khi chạy trên máy cá nhân vẫn dùng `127.0.0.1:8765`. Nếu Railway đã có Start Command riêng, đặt nó thành `python app.py` hoặc bỏ giá trị cũ để Railpack đọc `Procfile`.

GitHub Actions secret `OPEN_AI_API_KEY` không tự chuyển sang Railway. Trong Railway, mở service **Variables**, thêm biến `OPEN_AI_API_KEY` với cùng giá trị và deploy thay đổi. File `local_api_key.py` chỉ dùng cho bản chạy trên máy cá nhân; không commit hoặc tải file này lên server.

SQLite trong thư mục `data/` là dữ liệu cục bộ của container. Nếu muốn giữ thư viện file và tag qua các lần deploy, cần gắn volume bền vững vào thư mục `data/` của ứng dụng. Giao diện hiện chưa có đăng nhập; chỉ nhập API key và tải tài liệu nhạy cảm khi bạn đã hạn chế quyền truy cập vào service.
