# Đưa project lên GitHub để gắn vào CV

## File nào dùng để upload?

Dùng thư mục `fdic-risk-analytics-public` đã xuất riêng hoặc giải nén `fdic-risk-analytics-public.zip`. Không kéo thư mục làm việc có `data`, `models`, `.local` lên trình duyệt. File ZIP chỉ là gói vận chuyển: giải nén rồi upload các file/thư mục bên trong, không chỉ upload một file ZIP.

## Tạo repo và upload bằng trình duyệt

1. Đăng nhập GitHub. Mở https://github.com/new.
2. Đặt tên `fdic-bank-failure-risk-analytics`; mô tả: `Auditable FDIC financial-data pipeline, time-ordered bank-risk modelling and alert-workload analysis`.
3. Chọn **Public**. Có thể tạo README ban đầu để dễ mở giao diện upload; README của project sẽ thay nội dung này.
4. Tạo repository. Chọn **Add file → Upload files**.
5. Kéo nội dung bên trong bản public vào. Upload theo đợt nếu cần: trước hết file gốc, `src`, `scripts`, `tests`, `notebooks`, `docs`, `references`; sau đó `reports`. Giữ nguyên cấu trúc thư mục. GitHub cho tối đa 100 file mỗi lần upload.
6. Commit từng đợt với nội dung như `Add reproducible FDIC risk analytics portfolio`.
7. Mở notebook và PDF trên GitHub; kiểm tra biểu đồ, bảng và README hiện đủ. Mở URL repo trong cửa sổ chưa đăng nhập để kiểm tra Public.
8. Sao chép URL repo. Điền URL thật vào README và trang đầu PDF; có thể gửi URL lại trong chat để cập nhật bản tài liệu. Mã sinh viên và tên tác giả đã điền theo thông tin bạn cung cấp.
9. Trong CV đặt tên project và dẫn link GitHub. Không viết rằng đây là project của EY; đây là project học thuật liên quan tới vị trí FSO Data Analytics.

## Nếu dùng Git/GitHub Desktop

Chọn thư mục public làm repository local, xem danh sách file thay đổi, commit rồi publish với chế độ Public. Không chọn thư mục project nghiên cứu gốc. Project chưa được tự động commit/publish trong phiên làm việc này.

## Trước khi nộp đề bài

- Repo public, link dùng được.
- PDF tiếng Anh dưới 20 trang phần chính; bản học thuật hiện tại 14 trang chính + 1 trang phụ lục.
- Trang đầu có họ tên, mã sinh viên, URL repo thật, nguồn/ngày tải, số dòng và khoảng train/test.
- Notebook có output, requirements pinned, seed và hướng dẫn tái lập.
- Đề yêu cầu dẫn công cụ AI trong báo cáo và README. README vẫn có kê khai; đoạn kê khai trong báo cáo đã được bỏ theo yêu cầu, nên cần bổ sung hình thức trích dẫn phù hợp trước khi nộp.
- Không đưa dữ liệu ngân hàng lên repo. Bảng tổng hợp/biểu đồ phục vụ báo cáo được giữ.
- Đọc kỹ giới hạn: B3 không thắng core7+iRF trên AP test; chi phí và ngưỡng là kịch bản minh bạch, không phải chi phí FDIC đã được xác nhận.

Hướng dẫn chính thức: https://docs.github.com/en/repositories/creating-and-managing-repositories/quickstart-for-repositories và https://docs.github.com/en/repositories/working-with-files/managing-files/adding-a-file-to-a-repository.
