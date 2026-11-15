# Biên tập văn viết của báo cáo

Phạm vi: viết lại abstract, toàn bộ phần thân, caption và notes, phần tái lập và phụ lục. Giữ bộ style pdfLaTeX đã duyệt, các dự báo và ngưỡng. Không đánh giá tác giả bằng “AI score” và không dùng số lượng dấu câu để kết luận nguồn gốc văn bản.

## Các hướng dẫn đã đọc và áp dụng

- [SciWrite — Lorena A. Barba](https://github.com/labarba/sciwrite), dựa trên khóa Writing in the Sciences của Kristin Sainani. Đã đọc `skills/sciwrite/SKILL.md`, `references/section-guidance.md` và `references/summary-paragraph.md`. Áp dụng sự nhất quán thuật ngữ, logic đoạn văn, động từ rõ và đối soát số liệu. Các quy tắc abstract dành riêng cho Nature không được áp nguyên vào bài này.
- [blader/humanizer](https://github.com/blader/humanizer), `SKILL.md`. Áp dụng việc bỏ lời mở đầu dàn dựng, tương phản thiếu mục đích, kết đoạn nhắc lại và giọng tự bình luận. Giữ các khái niệm kỹ thuật cần thiết.
- [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing), `SKILL.md` và các mục liên quan trong `references/patterns.md` về false agency, thuật ngữ ổn định và hyphenation. Áp dụng điều kiện bảo toàn nghĩa trước khi đổi từ. Không sử dụng detector hoặc benchmark tự động của repo.

Các repo được xem như tài liệu biên tập. Cấu trúc đề bài BFT65B và yêu cầu của người dùng quyết định phạm vi công việc. Không cài skill vào hệ thống, không sao chép nguyên văn hướng dẫn và không coi mô tả trong tài liệu AI đính kèm là kết quả benchmark đã được kiểm chứng.

## Nội dung theo đề bài

| Phần báo cáo | Nội dung bắt buộc được trình bày |
|---|---|
| 1. Acquisition and storage | Nguồn, tải theo trang, kiểm completeness, raw/Parquet, đo dung lượng |
| 2. Data quality and panel construction | Các ngoại lệ báo cáo, zeros/missing/YTD, exits, nhãn, availability và đối soát cohort |
| 3. Scalable processing | So pandas/Polars, query plan, Spark parity, phạm vi đo và điều kiện cân nhắc cluster |
| 4. Feature construction and preprocessing | Động cơ kinh tế, nhóm biến, cách tạo đặc trưng và học preprocessing trong training |
| 5. Modelling and validation | Baselines, chia theo thời gian, metric, chọn model, ngưỡng chi phí, holdout, MLlib và giải thích model |
| 6. Conclusions and implications for Vietnam | Trả lời Q1–Q3, giới hạn và thay đổi cần cho Việt Nam |
| 7. Reproducibility | Vật liệu, nguồn gốc kết quả, đường tái lập và hỗ trợ AI |
| Appendix A | Các phép so selector/model bổ sung, tách kết quả dùng negative subsampling |

Đã thêm bảng các ngoại lệ dữ liệu từ file tổng hợp có sẵn để phần Data Quality có bằng chứng định lượng. Đây là sử dụng lại dữ liệu đã kiểm, không phải lượt xử lý hay đánh giá model mới.

## Cách xử lý góp ý reviewer

**Đã áp dụng:** bỏ các câu tự khen “honest”, “deliberately qualified”, “silently”; rút các đuôi phủ định lặp lại; bỏ ba câu hỏi song song và đoạn “Three contributions”; nối các câu methods thành đoạn có quan hệ rõ; chuyển hướng dẫn thao tác nộp bài ra tài liệu hỗ trợ. Chú thích giữ đơn vị, mẫu, định nghĩa cần thiết và nguồn. Tên template/microtype cùng mã commit được giữ trong attribution ngoài báo cáo, không còn trong danh mục nghiên cứu.

**Giữ hoặc sửa khác reviewer khi cần bảo toàn nghĩa:**

- Code hiện tại báo lỗi khi một feature thiếu hoàn toàn trong training. Văn bản mới viết “A fit was stopped …”; không đổi thành “features are excluded” vì code không thực hiện việc đó.
- Giới hạn dữ liệu lịch sử và giả định release lag vẫn có trong Methods/Conclusions. Chỉ rút cách nói phòng thủ lặp lại, không biến dữ liệu sửa đổi thành dữ liệu có đúng vintage.
- Việc baseline tốt hơn được giới hạn ở phép so trên holdout này. Không suy ra định luật rằng thêm biến hay tăng độ phức tạp luôn làm giảm khả năng tổng quát hóa.
- Kết quả local processing chứng minh khả năng chạy workload được đo. Không thêm nhận định “full panel fits in memory” như một số đo RAM chưa được báo cáo.
- Giữ “bank-quarter”, “non-interpolated AP” và các thuật ngữ cần thiết. Không cấm tuyệt đối dấu hai chấm, chấm phẩy hoặc câu có chủ ngữ là một phương pháp.
- “Mean annual AP” thay tên nội bộ AP-D7 trong diễn giải và hình. Công thức cùng tập năm được giữ nguyên. Các cột dữ liệu AP_D7 không bị đổi tên.
- B3 được định nghĩa trước khi xuất hiện ở kết quả. Các mã Y1, ContractCapperV4 và D43 chỉ xuất hiện kèm giải nghĩa để truy nguyên cách thực thi.
- URL repository chưa tồn tại. Trang đầu ghi tình trạng xuất bản ngắn gọn và hướng dẫn tạo repo ở tài liệu riêng. Không dựng URL giả hoặc xóa mục đề bài yêu cầu.

## Bibliography và attribution

Đã bỏ hai mục template/microtype khỏi bibliography của báo cáo. Các nguồn về dữ liệu, phương pháp và phần mềm khoa học vẫn được trích dẫn. Bỏ các trường `note` mang lời bình biên tập, chuyển locator hữu ích vào chỗ sử dụng như OCC (2011, p. 4), FDIC OIG (2019, p. 11) và FDIC OIG (2012, Table 3). Thông tin phiên bản cần cho tái lập vẫn có trong citation phần mềm và requirements.

Attribution template, giấy phép và quy tắc dàn trang ở `docs/REPORT_STYLE_GUIDE.md` cùng `references/layout-template/`. Hỗ trợ AI được công bố ở báo cáo và README. Nguồn của quy trình biên tập được ghi trong tài liệu này.

## Kiểm tra bảo toàn

Đối soát bảng tổng hợp, config model, cost policy, evaluation protocol, notebook và file style với bản trước khi sửa. Rà riêng các giá trị TP/FP/FN/TN, AP, event recall và số giờ review trong phần kết quả. Biên dịch pdfLaTeX/BibTeX và kiểm trang in để phát hiện ngắt mục hoặc bảng tràn.

Giới hạn chi phí thực tế trong SOURCE_AUDIT.md vẫn còn hiệu lực. Biên tập câu chữ không cung cấp thêm bằng chứng về đơn giá review, nhân sự hoặc hiệu quả can thiệp.

## Lượt rà bổ sung theo góp ý về wording

Đã đối chiếu hai tài liệu đính kèm với bản hiện hành. Các cụm như “once-authorized holdout”, “weak head selectivity”, “quality provenance” và “holdout … spent” thuộc bản cũ, đã được bỏ trước lượt này. Không đưa chúng trở lại chỉ để minh họa cách sửa.

Các nguồn bổ sung được đọc như tài liệu biên tập, không phải bằng chứng xác định tác giả:

- [clements23/ai-slop-library](https://github.com/clements23/ai-slop-library), snapshot `cf8e032d27ffd6426e6f3b743106ca7f5e285aff`: đọc `data/slop-words.json`, `data/slop-phrases.json` và phần nạp/matching của `scripts/slopcheck.py`. Dùng danh sách từ để tìm ứng viên, sau đó kiểm lại từng ngữ cảnh. Một kết quả “additionally” trong mô tả bước standardization của logistic regression được giữ vì nêu đúng một bước bổ sung.
- [FeedHive/ai-slop-detector](https://github.com/FeedHive/ai-slop-detector), snapshot `95d550706040191b0e75f1d89296a648bacb126e`: đọc `patterns.json` và `skills/ai-slop-detector/SKILL.md`, tập trung vào từ trừu tượng, cấu trúc đối lập dàn dựng, lặp nhịp câu và nhận định thiếu bằng chứng. Danh sách có 120 mẫu trong 9 nhóm; không dùng chúng như quy tắc cấm tuyệt đối cho văn bản khoa học.
- [ahmedak/defluff](https://github.com/ahmedak/defluff), snapshot `67c0ef388bf688194ab0667275d4898b4222e7d3`: đọc phần khởi tạo lexicon trong `src/defluff/lexicon.py` và logic matcher trong `src/defluff/patterns.py`. Mã phân biệt cấu trúc đối lập rõ với dạng “X, not Y” có nhiều false positives hơn. Không cài hoặc chạy nguyên gói và không tính điểm AI.

### Các thay đổi thực hiện

- Thay “data-quality ledger” và “quality ledgers” bằng record cụ thể về nguyên nhân thiếu và ngoại lệ báo cáo. Nói rõ record này không được đưa vào model dưới dạng predictor. Không đánh đồng nó với missingness indicators.
- Thay “training cover” bằng weighted number of training observations reaching each node. Đã đối chiếu `weighted_n_node_samples_` trong mã Tree SHAP; không đổi thành số dòng chưa có trọng số.
- Thay “as-of” trước khoảng thời gian trên trang đầu bằng prediction quarters, tránh nhầm ngày dự báo với quý của báo cáo tài chính gốc.
- Mô tả trực tiếp phép lọc 6.404 quan sát khỏi danh sách 280.267 để còn 273.863 quan sát đánh giá. Giữ nguyên việc kiểm tra dừng trước dự báo và các quy tắc model/ngưỡng không thay đổi.
- Rút câu trừu tượng về khả năng chuyển giao sang Việt Nam; giữ yêu cầu định nghĩa dữ liệu, publication dates và đo quy trình review tại địa phương.
- Viết rõ giới hạn do dữ liệu sửa đổi và quy tắc lịch sử được phát hiện hồi cứu. Không xóa các giới hạn này để câu văn nghe chắc chắn hơn.
- Đổi câu “panel was manageable” thành kết quả đã thực thi là acquisition và panel processing hoàn thành trên laptop. Không thêm khẳng định chưa đo rằng toàn bộ panel nằm trong RAM.

Giữ “reconcile” trong kiểm tra quan hệ giữa liabilities, assets và equity vì đây là đối soát kế toán có đối tượng rõ. Giữ thuật ngữ bank-quarter, non-interpolated AP, TTM và các định nghĩa thống kê. Không thay số liệu, model, cost policy hoặc notebook.

### Tiêu đề và tài liệu tham khảo

Theo yêu cầu bổ sung, tiêu đề hiện hành là “Bank-Failure Early Warning Using FDIC Data”, với phụ đề “Data Engineering, Temporal Validation and Review Costs”. References bắt đầu ở trang riêng, đánh số tự động bằng BibTeX `unsrtnat`; trích dẫn trong bài dùng số tương ứng. Đây là thay đổi có chủ đích đối với kiểu trích dẫn author–year của bản trước; font, cỡ chữ thân, lề và giãn dòng được giữ nguyên. Các repo biên tập chỉ ghi ở tài liệu hỗ trợ này, không thêm vào References khoa học.
