# Quy chuẩn báo cáo pdfLaTeX

Bản hiện hành được biên dịch bằng **pdfLaTeX + BibTeX**. Quy tắc nằm ở `reports/manuscript/fdicpaper.sty`; nội dung TeX đầy đủ ở `main.tex`; danh mục tài liệu ở `references.bib`. Bản ReportLab trước được lưu riêng trong `.local/latex_redesign_backup/`.

## Đối chiếu các bài trong thư mục Financial Big Data

Lượt này xem trang thân bài, bảng/hình và thông tin font trong PDF, thay vì chỉ nhìn trang đầu. Các số đo dưới đây lấy từ các trang được kiểm, không khẳng định mọi trang của bài đều dùng đúng một cỡ chữ.

| Bài và trang đã xem | Quan sát / số đo | Quyết định cho báo cáo |
|---|---|---|
| Failing Banks, Correia–Luck–Verner, bản 5/6/2025; trang PDF 1, 2, 8 | Thân URW Palladio khoảng 12 pt, tiêu đề mục đậm; đầu đoạn sau heading không thụt, đoạn sau thụt; giãn dòng thoáng | Giữ quy tắc đoạn văn; không trộn khoảng trống sau đoạn với thụt đầu dòng tùy ý |
| Cawley–Talbot, JMLR 2010; trang PDF 1, 2, 6 | Thân Times khoảng 10,9 pt; tiêu đề mục lớn hơn vừa phải; công thức và hình được LaTeX dàn tự nhiên | Chọn Times-like 11 pt và hệ cỡ chữ của article, không dựng nhiều cỡ lẻ thủ công |
| Petropoulos et al., IJF 2020; trang đầu và đoạn kết quả/bảng | Bản nhà xuất bản hai cột; chữ thân khoảng 8,3 pt do cột hẹp | Học caption, ký hiệu và tính nhất quán; không bê cỡ 8,3 pt sang bản một cột |
| Bốn ảnh thầy cung cấp | Bản một cột; title/author/abstract rõ; bảng panel, note và phương trình có số | Giữ cấu trúc học thuật gần mẫu; không khẳng định thầy dùng repo cụ thể |

Không sao chép nội dung bài, số liệu hay khẳng định nhân quả của thầy. Không đưa các PDF bài báo và ảnh lớp học vào gói public.

## Hệ quy tắc hiện hành

| Thành phần | Thiết lập nhất quán |
|---|---|
| Khổ / lề | A4; lề trái/phải 27 mm; trên/dưới 25 mm |
| Thân bài | TeX Gyre Termes, Times-like, 11 pt; giãn dòng 1,12 theo baseline của article |
| Title | Cùng họ chữ, đậm 18 pt, baseline 22 pt |
| Mục / tiểu mục | Section dùng large, khoảng 13,2 pt; subsection dùng normalsize đậm, khoảng 11 pt; một bộ khoảng cách chung |
| Đoạn | `parindent=1.5em`, `parskip=0`; đầu đoạn ngay sau heading không thụt theo quy tắc LaTeX; các đoạn tiếp thụt |
| Khoảng chữ | Giữ tracking mặc định của font; microtype xử lý protrusion/expansion tinh, không chèn khoảng trắng tay để căn dòng |
| Công thức | newtxmath, ký hiệu toán thật, số phương trình tự động |
| Bảng | booktabs, không tô màu/lưới dày; chữ small; số căn phải; caption trên; note footnotesize ngay dưới |
| Hình | Vector PDF, STIX General gần Times; navy `#1D3557`, teal `#287D8E`, xám `#7A8188`; ký hiệu, nét và hatch giúp phân biệt khi in xám |
| Trích dẫn | Natbib dạng số trong ngoặc vuông + BibTeX `unsrtnat`; References đánh số theo thứ tự xuất hiện, không đánh số nguồn thủ công |
| Ngắt trang | References bắt đầu ở trang riêng và phụ lục bắt đầu ở trang riêng; không ngắt trang sau mỗi mục khác; raggedbottom giữ nhịp dòng; số trang ở giữa chân trang |

Tên tác giả tiếng Việt dùng encoding T5 của cùng họ TeX Gyre Termes. Body dùng T1. Font được nhúng vào PDF; không thay tên tác giả thành bản không dấu.

## Mã template đã đọc

Lựa chọn tham khảo chính: [pmichaillat/latex-paper](https://github.com/pmichaillat/latex-paper), commit `f8afa108da12b18f8b059b81b2ccba23bd4ee7aa`.

- Đọc `paper.sty`: typography, spacing, heading, booktabs, caption/note, bibliography và appendix.
- Đọc khai báo/trang đầu và các ví dụ bảng/hình nhiều panel trong `paper.tex`.
- Bản upstream `paper.sty` và MIT licence nằm ở `references/layout-template/` để tham khảo; báo cáo dùng **style cục bộ fdicpaper.sty**, không cần chạy upstream file.
- Đối chiếu `ElegantLaTeX/ElegantPaper/elegantpaper.cls`; trước đó đã đọc font, caption, abstract, maketitle và bibliography.
- Đã đọc phần cấu hình và title/front-matter của `causal-lab/AEA-Templates`. Không nhận là đã đọc toàn bộ AEA.cls.

Không dùng nguyên style của một tạp chí và không gắn nhãn đã được tạp chí chấp nhận. [microtype](https://ctan.org/pkg/microtype) hỗ trợ việc căn chữ của pdfTeX; cài package không tự bảo đảm một layout đẹp nên bản PDF vẫn phải được kiểm bằng mắt.

## Dựng lại bằng pdfLaTeX

Cần TeX Live, MacTeX hoặc TinyTeX có các package dùng trong `fdicpaper.sty`, đặc biệt `tex-gyre`, `newtx`, `oberdiek`, `vntex`, `microtype`, `babel-english`, `hyphen-english`, `threeparttable`, `titlesec`, `placeins`, `setspace`, `caption`, `natbib`, `bookmark`, `booktabs` và `geometry`.

```bash
python -m pip install -r requirements-report.txt
python scripts/build_report.py
```

Builder tạo `main.tex`, sau đó chạy pdfLaTeX → BibTeX → pdfLaTeX → pdfLaTeX, với shell escape tắt. Có thể đặt `PDFLATEX` thành đường dẫn engine nếu nó chưa nằm trong PATH. Bộ TeX riêng dùng cho lần này nằm trong `.local/`, không nằm trong gói GitHub.

Hoặc mở `reports/manuscript/main.tex` trong trình soạn LaTeX/Overleaf và chọn **pdfLaTeX**; cần giữ các hình PDF ở đúng đường dẫn tương đối `../figures/paper/`. Chạy BibTeX để giải trích dẫn. Không đưa `references/layout-template/paper.sty` vào thay cho style cục bộ.

- Sửa lâu dài: chỉnh văn bản trong `content.py`, style trong `fdicpaper.sty`, tài liệu trong `references.bib`, rồi chạy builder.
- Sửa trực tiếp `main.tex` cũng được; biên dịch trực tiếp sau đó. Builder sẽ tạo lại file này từ content source khi chạy tiếp.
- `python scripts/build_report.py --source-only` chỉ xuất TeX.
- `python scripts/build_paper_figures.py` vẽ lại hình từ aggregate CSV bằng môi trường khoa học. Không fit model hoặc mở test.

`reports/latex_build.json` ghi engine, các lượt biên dịch và cảnh báo. `reports/report_layout.json` ghi số trang/bảng/hình. Bản hiện hành có 14 trang chính (gồm trang đầu và tài liệu tham khảo) + 1 trang phụ lục.

Kiểm nguồn và các giả định chưa được xác định nằm ở [SOURCE_AUDIT.md](SOURCE_AUDIT.md). Giữ nguyên các dự báo, cấu hình model, ngưỡng và test contract; thay đổi tài liệu không phải là một vòng nghiên cứu model mới.

## Bộ nguồn độc lập

`python scripts/export_latex_source.py` tạo gói `fdic-report-latex-source.zip` bên cạnh project. Gói này chỉ gồm main.tex, style, BibTeX và sáu hình PDF theo đường dẫn tự chứa; không cần Python/data để biên dịch. Đã giải nén sang thư mục khác và kiểm tra pdfLaTeX/BibTeX tạo PDF có nội dung văn bản trùng bản chính. Trên Overleaf, upload gói này và chọn pdfLaTeX.

## Biên tập văn viết

Văn bản hiện hành theo thứ tự các phần của đề bài BFT65B. Quyết định biên tập và các điểm giữ khác với gợi ý reviewer nằm ở EDITORIAL_REVIEW.md. Các nguồn dàn trang được ghi nhận ở tài liệu hỗ trợ, còn References trong báo cáo dành cho dữ liệu và phương pháp nghiên cứu.
