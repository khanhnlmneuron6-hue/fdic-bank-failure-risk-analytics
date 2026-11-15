# D8 — Số 0 nghĩa là gì? (v1 ở mục 1–5 là lịch sử; quy tắc đang dùng: §6, v2)

Ngày: 2026-11-09. Trạng thái: **đã duyệt R1–R9 (2026-11-09) và đã áp dụng ở notebook mục 10** vào lớp `data/processed/panel_d8/` (log `d8_null_log.parquet`). R7 (CBLR) chưa áp vì cần duyệt riêng việc tải thêm field. Dữ liệu nguồn, `panel_tech`, `panel_pit` giữ nguyên. Code audit nằm ở notebook mục 9; bảng số
liệu ở `reports/tables/d8_*.csv`.

Phạm vi dữ liệu:
* Chỉ báo cáo development (REPDTE ≤ 2011-09-30), bỏ các dòng 1985-06-30 đã mask ở mục 7.
* CET1 (từ 2015; với ngân hàng advanced approaches là 2014) và CBLR (từ 2020) **nằm ngoài development**. Quy tắc cho hai giai
  đoạn này chỉ dựa vào văn bản; tôi không mở dữ liệu gap/test.
* Nhãn failure **không** được dùng.

## 1. Các nghĩa có thể có của số 0

| Mã | Nghĩa | Ví dụ |
|---|---|---|
| `zero_true` / `zero_numerator_zero` | 0 thật, hoặc tỷ lệ có tử số = 0 với mẫu số > 0 | EQV khi EQ = 0 |
| `zero_not_applicable_regime` | chế độ báo cáo chưa có khái niệm này | IDT1CER trước 2015 |
| `zero_undefined_inputs` | tỷ lệ không xác định (mẫu số thiếu, bằng 0, âm, hoặc tử số thiếu), nhưng công thức FDIC trả 0 | RBC1AAJ khi RBCT1J thiếu |
| `zero_suspected_not_populated` | nghi là đầu vào không được điền với một nhóm đối tượng | IDT1RWAJR ở ngân hàng NC |
| `zero_unverified` | chưa đủ bằng chứng | phần còn lại |
| (làm tròn) | số tiền nhỏ hơn 0,5 nghìn USD bị làm tròn về 0 | **chưa kiểm tra**; không giả định |

## 2. Bằng chứng chính

1. **Metadata của FDIC** (`risview_properties.yaml`, trường `x-source-mapping`; R03):
   * 72 field lấy thẳng từ file RISVIEW;
   * 14 field do API tính bằng công thức `percentage` (tử số / mẫu số);
   * OTHBRF = TTL + OTHBOR + MTGLS. Điều này giải thích I15 (OTHBOR ≠ OTHBRF) bằng định nghĩa.
2. **Hành vi của công thức `percentage`** (đo trên development, ô 9.2): trả **0** khi mẫu số null, bằng 0 hoặc **âm**, và khi tử
   số null. Ví dụ: RBCRWAJ 403.932 dòng thiếu mẫu số → 0; RBC1AAJ 75.178 dòng thiếu tử số → 0.
   * Field lưu sẵn RBC1RWAJ thì là **null** khi thiếu mẫu số, và bằng đúng 100 × RBCT1J / RWAJT ở 100 % dòng có mẫu số dương.
3. **Mốc chế độ vốn:**
   * RWAJT null ở 100 % báo cáo trước 1990Q1. Quy tắc vốn theo rủi ro được ban hành năm 1989, với mức tối thiểu tạm thời cuối
     1990 và đầy đủ cuối 1992 (R51: **chỉ có trích đoạn**, chưa đọc văn bản gốc).
   * FFIEC Schedule RC-R bản 3/2015 có chỉ tiêu CET1 ratio (item 41); chuyển tiếp từ 1/1/2014 với advanced approaches và
     1/1/2015 với non-advanced (R50).
   * 12 CFR 324.12 (CBLR; 84 FR 61802, 13/11/2019): tổ chức đủ điều kiện **chọn** khung CBLR thì được coi là đạt yêu cầu vốn
     (R05). Ngày hiệu lực chưa đọc trong văn bản.
4. **BKCLASS NC** = ngân hàng hoặc công ty ủy thác không được bảo hiểm, không nhận tiền gửi (từ điển). Ở nhóm này, 6.664 dòng có
   IDT1RWAJR = 0 trong khi RBC1RWAJ ≠ 0.

## 3. Quy tắc đề xuất

Khi được duyệt, quy tắc sẽ áp vào một **lớp dẫn xuất mới**: giá trị gốc giữ nguyên, có log và cột lý do, giống cách làm ở mục 7.

| # | Field × thời kỳ × đối tượng | Đề xuất | Ô bị ảnh hưởng (dev) | Mức bằng chứng |
|---|---|---|---|---|
| R1 | IDT1CER, trước 2015 | 0 → null, lý do `not_applicable_regime` | 1.333.039 | xác minh (FFIEC RC-R 2015) |
| R2 | RBCRWAJ, IDT1RWAJR, trước 1990Q1 | 0 → null, `not_applicable_regime` | 401.561 + 401.561 | hỗ trợ mạnh (RWAJT không tồn tại + hành vi công thức); văn bản 1989 chỉ trích đoạn |
| R3a | RBC1AAJ, RBCT1J null | 0 → null, `undefined_inputs` | 75.178 (72.808 ở 1984–89, chủ yếu thrift CALLFORM 100) | hỗ trợ mạnh; RBCT1J là **xấp xỉ** của tử số RBCT1 |
| R3b | RBCRWAJ, IDT1RWAJR, RWAJT null/≤ 0 (từ 1990) | 0 → null, `undefined_inputs` | 2.492 mỗi field | xác minh (metadata + đo) |
| R3c | EQV, LNATRESR, LNLSDEPR, IDLNCORR: mẫu số null/≤ 0 hoặc tử số null | 0 → null, `undefined_inputs` | 3.116; 16.448; 8.763; 11.678 | xác minh (metadata + đo) |
| R4 | các tỷ lệ trên khi tử số = 0, mẫu số > 0 | **giữ 0** | EQV 22; LNATRESR 18.460; LNLSDEPR 5.181; IDLNCORR 3.460; RBC1AAJ 90; RBC1RWAJ 22 | xác minh |
| R5 | IDT1RWAJR = 0, BKCLASS NC, RBC1RWAJ ≠ 0 | giữ + cờ `suspected_not_populated`; chưa là đầu vào hợp lệ | 6.664 | giả thuyết |
| R6 | các tỷ lệ công thức không kiểm được đầu vào (NPERFV, NCLNLSR, LNRESNCR, ROA, ROAPTX, NIMY; RBCRWAJ/IDT1RWAJR khi RWAJT > 0) | giữ + cờ `zero_unverified`; ở bước feature ưu tiên **tự tính** tỷ lệ từ field gốc (I17) | RBCRWAJ 23; IDT1RWAJR 23; các field khác chưa đếm | chưa xác minh |
| R7 | CBLR (2020+, ngoài dev): RBCRWAJ, IDT1RWAJR, IDT1CER, RBC1RWAJ | chưa đặt quy tắc dữ liệu; để phân biệt "không báo cáo vì chọn CBLR" với 0 cần thêm field cờ CBLR ở Schedule RC-R → **đề xuất tải thêm, cần duyệt riêng**. Tên tử số `IDT1JNOCB`, `IDT1CNOCB` gợi ý "không gồm ngân hàng CBLR" — **chỉ là suy đoán từ tên** | không đo (ngoài dev) | văn bản |
| R8 | RBCT1J = 0 (90), RWAJT = 0 (111) | giữ + cờ `zero_unverified` | 201 | chưa xác minh |
| R9 | field tiền và field dòng khác (BRO, FREPP, OTHBOR, INTAN, ORE, LN*, P*…) | **giữ 0, ghi "chưa xác minh"**; không khẳng định "luôn là 0 thật" | — | quan sát |

Tổng số 0 sẽ thành null-có-lý-do nếu duyệt R1–R3: **2.256.328 ô** (development).

## 4. Điểm cần bạn audit

1. **R1/R2 ("chưa áp dụng" → null):** đồng ý dùng null với lý do, hay giữ 0 kèm cờ? Cả hai cách đều không lộ thông tin tương
   lai; null giúp model không hiểu nhầm 0 là "vốn = 0".
2. **R3a:** RBCT1J có phải xấp xỉ chấp nhận được cho tử số RBCT1 của RBC1AAJ không? Bằng chứng: chỉ 23 dòng trước 1990 có
   RBC1AAJ = 0 khi RBCT1J có giá trị.
3. **R5 (ngân hàng NC):** ngân hàng không nhận tiền gửi có nên nằm trong population dự báo failure không? Đây là câu hỏi cho D4
   — **đã quyết** (D4 duyệt 2026-11-09): NC ra khỏi population, nên 6.664 ô R5 không còn trong population.
4. **R7:** có cho phép tải thêm field cờ CBLR (và nếu cần, đầu vào của các tỷ lệ công thức) không? Việc này phải tải lại toàn bộ
   các quý.
5. **Ngưỡng trong mục 9.5** (chênh lệch tỷ lệ số 0 giữa các mẫu) là tiêu chí sàng lọc do tôi đặt, không phải quy định.

## 5. Backlog (không chặn bộ core)

* **Số 0 tập trung ở CALLFORM 100** (thrift trước 2012): LNCI 39,5 % so với 3,4 % ở mẫu khác; NTLNLS(Q) 30–39 %; P9* 46,5 %;
  NPERFV 43,9 %. Cần đọc mẫu TFR của OTS để biết đây là "không có khoản đó" hay "mẫu không tách khoản này".
* **CALLFORM 2/18** (rất ít dòng): nhiều field bằng 0 ở 100 % → có thể là mẫu rút gọn. Ý nghĩa mã chưa có tài liệu (I27).
* **Làm tròn về 0** ở field tiền của ngân hàng rất nhỏ: chưa kiểm tra.
* ROE/ROEQ: từ điển ghi NA khi lợi nhuận giữ lại âm. Số 0 của hai field này chưa phân tích.

## 6. D8 v2 — quy tắc đang dùng (notebook mục 10, duyệt 2026-11-09)

**Trạng thái:** người dùng duyệt hướng v2 ngày 2026-11-09, kèm hai chỉnh sửa. v2 là **phiên bản duy nhất được áp dụng**.
* Lớp `data/processed/panel_d8/` dựng lại từ `panel_pit`, có dấu `d8_rules_version.json` (`d8_v2_2026-11-09`).
* Các bước sau đọc qua `read_d8_layer()`.
* v1 (mục 3–5 ở trên, notebook mục 9) chỉ còn là audit lịch sử. Hàm v1 được đổi tên `d8_zero_status_v1`, không ghi dữ liệu.

Sửa so với v1:
* **Chỉ dùng đầu vào thật của công thức** (R53).
  * RBC1AAJ (RBCT1 / AVASSETJ) không còn bị null theo RBCT1J.
  * IDT1RWAJR (IDT1JNOCB / RWAJ) chỉ null khi RBCT1J null, vì theo script tử số khi đó = 0 ở mọi nhánh. Không dùng RWAJT thay RWAJ.
* **IDT1CER** (R54): trước 31/3/2014 → null; 2014 → giữ, chưa xác minh phạm vi; từ 2015 → giữ, chưa xác minh.
* **Mẫu số:** null hoặc = 0 → null. **Mẫu âm một mình không đổi giá trị**: giữ + `zero_unverified_den_negative`. Nếu ô đó có lý do
  độc lập đã xác minh (tử thật null) thì vẫn null theo lý do đó.
* **IDT1RWAJR với RBCT1J = 0:** giữ 0 + `zero_unverified_numerator_input_zero`. Không tính là 0 đã xác minh, vì RWAJ và điều kiện
  INSFDIC/CBLRIND/IBA chưa biết.
* **Đầu vào bị mask I01 không dùng để quyết định**: 23 ô IDLNCORR ở 1985-06-30 được giữ.
* **R6:** trạng thái cho NPERFV, NCLNLSR, LNRESNCR, ROA, ROAPTX, NIMY; giá trị giữ nguyên.

Số liệu development (không gồm 1985-06-30; trong ngoặc là khi gồm):
* null: 1.852.218 (1.891.207);
* giữ 0 đã xác minh: 27.145;
* giữ 0 chưa xác minh: 833.546 (858.804).

So với v1: khôi phục 404.111 ô (421.987); 1 null mới. Bảng: `reports/tables/d8_applied_dev.csv`, `d8_v2_zero_status_dev.csv`,
`d8_v2_vs_v1_dev.csv`, `d8_v2_formula_behaviour_dev.csv`.

**Còn chưa xác minh** (giữ 0 ≠ đầu vào model hợp lệ):
* IDT1RWAJR trước 1990: chưa có văn bản về mốc báo cáo RWA;
* IDT1RWAJR có RBCT1J = 0, và ở ngân hàng NC;
* RBC1AAJ: RBCT1 và AVASSETJ chưa tải;
* IDT1CER năm 2014 và từ 2015; CBLR từ 2020 (R7);
* mẫu âm: LNLSGR, COREDEP, RWAJT;
* sáu tỷ lệ R6.

Ngoài ra, hành vi của `percentage` chỉ được đo, không có trong tài liệu.

Mục 3, bảng R3b ghi "xác minh" cho IDT1RWAJR là **ghi quá mức**: đầu vào thật là RWAJ, không phải RWAJT.
