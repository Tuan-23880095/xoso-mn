# Bộ cào kết quả Xổ số miền Nam (XSMN)

## Giới thiệu
Mô-đun cào và chuẩn hoá dữ liệu kết quả Xổ số Kiến thiết Miền Nam (XSMN) phục vụ phân tích thống kê và địa thống kê (variogram, kriging, kiểm định ngẫu nhiên).

## Nguồn dữ liệu
- **Nguồn chính**: `https://xskt.com.vn/xsmn/ngay-D-M-YYYY` (tôn trọng robots.txt, tốc độ ≤ 1 request/2s).
- **Nguồn đối chiếu**: `https://xosodaiphat.com/xsmn-DD-MM-YYYY.html`.
- **Dự phòng**: `https://www.minhngoc.net.vn/ket-qua-xo-so/mien-nam/DD-MM-YYYY.html`.

## Cấu trúc dữ liệu
- `data/ketqua.csv`: Dữ liệu chuẩn hoá dạng dài (long format). Mỗi dòng là một số trúng.
  - Các cột: `ngay`, `thu`, `dai_ma`, `dai_ten`, `giai`, `stt`, `so`, `n_chu_so`, `nguon`, `thoi_diem_cao`.
- `data/sai_lech.csv`: Ghi nhận sai lệch giữa nguồn chính và nguồn đối chiếu.
- `data/bat_thuong.csv`: Ghi nhận các kỳ/đài có số lượng số hoặc độ dài số lệch quy chuẩn (18 số/đài).
- `data/raw_html/`: Bộ đệm HTML thô tải về để tránh tải lại (nằm trong .gitignore).
- `logs/`: Nhật ký tiến trình cào dữ liệu (`scraper.log`).

## Quy chuẩn kiểm tra (18 số/đài)
- Giải ĐB: 1 số, 6 chữ số
- Giải Nhất (G1): 1 số, 5 chữ số
- Giải Nhì (G2): 1 số, 5 chữ số
- Giải Ba (G3): 2 số, 5 chữ số
- Giải Tư (G4): 7 số, 5 chữ số
- Giải Năm (G5): 1 số, 4 chữ số
- Giải Sáu (G6): 3 số, 4 chữ số
- Giải Bảy (G7): 1 số, 3 chữ số
- Giải Tám (G8): 1 số, 2 chữ số

## Cài đặt & Sử dụng
```bash
pip install -r requirements.txt
# Chạy mặc định (01-10-2026 đến 08-10-2026)
python scraper_xsmn.py

# Tuỳ chọn khoảng ngày linh hoạt
python scraper_xsmn.py --tu 2026-10-01 --den 2026-10-08
```

## Các điểm kỹ thuật chuẩn hoá (Cập nhật QA)
1. **Cột `thu`**: Tự động tính toán từ trường `ngay`.
2. **Mã đài `dai_ma`**: Sử dụng bảng mã cố định 21 đài XSMN (phân biệt rõ `BTR` - Bến Tre và `BTH` - Bình Thuận).
3. **Đối chiếu nguồn 2**: Đọc và đối chiếu số liệu với `xosodaiphat.com`, ghi nhận sai lệch vào `data/sai_lech.csv`.
4. **Khử trùng dữ liệu (Idempotent)**: Lọc trùng theo khoá kết hợp `(ngay, dai_ma, giai, stt)` trước khi ghi `ketqua.csv`, đảm bảo chạy nhiều lần cho kết quả nhất quán.
5. **Cảnh báo bất thường**: `data/bat_thuong.csv` chuẩn hoá đầy đủ cột và ghi rõ `ly_do`.
6. **User-Agent tự khai**: Định danh rõ ràng nghiên cứu, tôn trọng giới hạn tốc độ cào (≥ 2s/request).

## Lịch tự động hằng ngày (Windows Task Scheduler)
Hệ thống được thiết lập tác vụ tự động `xoso-mn-daily` chạy lúc **17:15 mỗi ngày** (sau giờ có kết quả XSMN ~16:40).
- **Cơ chế tự bù ngày**: Đọc ngày lớn nhất hiện có trong `data/ketqua.csv` và tự động cào nối tiếp từ ngày đó đến ngày hiện tại. Nếu máy tính bị tắt 1–3 ngày, tác vụ có cờ `StartWhenAvailable` sẽ tự bù đủ dữ liệu ngay khi khởi động lại máy.
- **Thoát an toàn**: Nếu mạng lỗi hoặc trang chưa có kết quả (trước 16:40), script ghi log và thoát êm, không ghi bản ghi rỗng/thiếu.
- **Tự động đẩy Git**: Tự động `git add data/ logs/`, `commit` và `push` thẳng lên nhánh `main` và `local/scraper`.

### Quản lý / Bật / Tắt / Gỡ lịch
Dùng PowerShell (hoặc Command Prompt):
- **Kiểm tra trạng thái**:
  ```powershell
  Get-ScheduledTask -TaskName "xoso-mn-daily"
  ```
- **Tạm tắt lịch**:
  ```powershell
  Disable-ScheduledTask -TaskName "xoso-mn-daily"
  ```
- **Bật lại lịch**:
  ```powershell
  Enable-ScheduledTask -TaskName "xoso-mn-daily"
  ```
- **Gỡ bỏ lịch hoàn toàn**:
  ```powershell
  Unregister-ScheduledTask -TaskName "xoso-mn-daily" -Confirm:$false
  ```
- **Chạy thử bằng tay**:
  ```powershell
  powershell -File "D:\GPU-work\xoso-mn\scraper\run_daily.ps1"
  ```

