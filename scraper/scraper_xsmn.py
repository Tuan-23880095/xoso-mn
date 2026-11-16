import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import datetime
import csv
import logging
import argparse

# Setup Logging
log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs/scraper.log'))
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
HTML_CACHE_DIR = os.path.join(DATA_DIR, 'raw_html')
KETQUA_CSV = os.path.join(DATA_DIR, 'ketqua.csv')
BAT_THUONG_CSV = os.path.join(DATA_DIR, 'bat_thuong.csv')
SAI_LECH_CSV = os.path.join(DATA_DIR, 'sai_lech.csv')

# Điểm 6: User-Agent rõ ràng tự khai, không giả lập trình duyệt
USER_AGENT = 'Tuan-XSMN-Research-Bot/1.0 (+https://github.com/Tuan-23880095/xoso-mn; contact: dqtuanhcmus@gmail.com)'
HEADERS = {'User-Agent': USER_AGENT}

# Điểm 1: Bản đồ thứ trong tuần từ datetime
THU_MAP = {
    0: "Thứ 2",
    1: "Thứ 3",
    2: "Thứ 4",
    3: "Thứ 5",
    4: "Thứ 6",
    5: "Thứ 7",
    6: "Chủ Nhật"
}

# Điểm 2: Bảng mã đài cố định 21 đài XSMN (phân biệt Bến Tre: BTR vs Bình Thuận: BTH)
DAI_MA_MAP = {
    "Hồ Chí Minh": "HCM",
    "TP.HCM": "HCM",
    "TP. Hồ Chí Minh": "HCM",
    "Đồng Tháp": "DT",
    "Cà Mau": "CM",
    "Bến Tre": "BTR",
    "Vũng Tàu": "VT",
    "Bà Rịa - Vũng Tàu": "VT",
    "Bạc Liêu": "BL",
    "Đồng Nai": "DN",
    "Cần Thơ": "CT",
    "Sóc Trăng": "ST",
    "Tây Ninh": "TN",
    "An Giang": "AG",
    "Bình Thuận": "BTH",
    "Vĩnh Long": "VL",
    "Bình Dương": "BD",
    "Trà Vinh": "TV",
    "Long An": "LA",
    "Bình Phước": "BP",
    "Hậu Giang": "HG",
    "Tiền Giang": "TG",
    "Kiên Giang": "KG",
    "Đà Lạt": "DL",
    "Lâm Đồng": "DL",
}

def get_html_xskt(date_str):
    """Tải HTML từ xskt.com.vn có bộ đệm cache"""
    os.makedirs(HTML_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(HTML_CACHE_DIR, f"{date_str}.html")
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()

    # date_str dạng DD-MM-YYYY
    d, m, y = date_str.split('-')
    url = f"https://xskt.com.vn/xsmn/ngay-{int(d)}-{int(m)}-{y}"

    try:
        time.sleep(2)  # Rate limit: <= 1 req/2s
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        html = resp.text
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return html
    except Exception as e:
        logging.error(f"Error fetching xskt {url}: {e}")
        return None

def get_html_daiphat(date_str):
    """Điểm 3: Tải HTML đối chiếu từ xosodaiphat.com có bộ đệm cache"""
    os.makedirs(HTML_CACHE_DIR, exist_ok=True)
    cache_path = os.path.join(HTML_CACHE_DIR, f"daiphat_{date_str}.html")
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()

    # date_str dạng DD-MM-YYYY
    d, m, y = date_str.split('-')
    url = f"https://xosodaiphat.com/xsmn-{d.zfill(2)}-{m.zfill(2)}-{y}.html"

    try:
        time.sleep(2)  # Rate limit: <= 1 req/2s
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        html = resp.text
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return html
    except Exception as e:
        logging.error(f"Error fetching daiphat {url}: {e}")
        return None

def parse_xsmn(html, current_date):
    """Phân tích HTML từ xskt.com.vn"""
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='MN0')
    if not table:
        return []

    # Danh sách tên đài từ hàng tiêu đề
    header_tr = table.find('tr')
    th_elements = header_tr.find_all(['th', 'td'])[1:]  # Bỏ cột đầu 'Giải'
    dais = [th.text.strip() for th in th_elements]

    date_str_iso = current_date.strftime("%Y-%m-%d")
    thu_str = THU_MAP.get(current_date.weekday(), "")

    results = []
    rows = table.find_all('tr')[1:]  # Bỏ hàng header
    giai_map = {
        "ĐB": "DB", "G.1": "G1", "G.2": "G2", "G.3": "G3",
        "G.4": "G4", "G.5": "G5", "G.6": "G6", "G.7": "G7", "G.8": "G8"
    }

    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    for row in rows:
        giai_td = row.find(['th', 'td'])
        if not giai_td:
            continue
        giai_title = giai_td.text.strip()
        giai = giai_map.get(giai_title)
        if not giai:
            continue

        td_elements = row.find_all('td')
        # Nếu cột đầu là td (thay vì th), td_elements bao gồm cả cột giải
        if len(td_elements) > len(dais):
            td_elements = td_elements[1:]

        for i, td in enumerate(td_elements):
            if i >= len(dais):
                continue
            dai_ten = dais[i]
            # Điểm 2: Sử dụng bảng mã đài cố định 21 đài
            dai_ma = DAI_MA_MAP.get(dai_ten, ''.join([c for c in dai_ten if c.isupper()]))

            numbers_text = td.get_text(separator=' ').strip()
            if not numbers_text:
                continue

            numbers = numbers_text.split()
            for stt, num in enumerate(numbers, 1):
                results.append({
                    'ngay': date_str_iso,
                    'thu': thu_str,  # Điểm 1: Điền thứ từ ngay
                    'dai_ma': dai_ma,
                    'dai_ten': dai_ten,
                    'giai': giai,
                    'stt': stt,
                    'so': num,
                    'n_chu_so': len(num),
                    'nguon': 'xskt.com.vn',
                    'thoi_diem_cao': now_str
                })
    return results

def parse_daiphat(html):
    """Điểm 3: Phân tích HTML từ xosodaiphat.com trả về map (dai_ma, giai, stt) -> so"""
    if not html:
        return {}
    try:
        soup = BeautifulSoup(html, 'lxml')
    except Exception:
        soup = BeautifulSoup(html, 'html.parser')

    table = soup.find('table', class_='table-xsmn')
    if not table:
        return {}

    thead = table.find('thead')
    if not thead:
        return {}
    dais = [a.text.strip() for a in thead.find_all('a')]

    giai_map = {
        "G.8": "G8", "G.7": "G7", "G.6": "G6", "G.5": "G5",
        "G.4": "G4", "G.3": "G3", "G.2": "G2", "G.1": "G1",
        "G.ĐB": "DB", "ĐB": "DB"
    }

    results = {}
    tbody = table.find('tbody')
    if not tbody:
        tbody = table

    for tr in tbody.find_all('tr'):
        tds = tr.find_all('td')
        if not tds:
            continue
        giai_title = tds[0].text.strip()
        giai = giai_map.get(giai_title)
        if not giai:
            continue

        for idx, td in enumerate(tds[1:]):
            if idx >= len(dais):
                continue
            dai_ten = dais[idx]
            dai_ma = DAI_MA_MAP.get(dai_ten, dai_ten)
            nums = [s.strip() for s in td.get_text(separator=' ').split() if s.strip()]
            for stt, num in enumerate(nums, 1):
                results[(dai_ma, giai, stt)] = num

    return results

def validate_and_save(all_results, daiphat_map, current_date):
    """Kiểm tra hợp lệ, đối chiếu 2 nguồn và lưu CSV có khử trùng khoá"""
    date_str_iso = current_date.strftime("%Y-%m-%d")
    expected_counts = {'G8': 1, 'G7': 1, 'G6': 3, 'G5': 1, 'G4': 7, 'G3': 2, 'G2': 1, 'G1': 1, 'DB': 1}
    expected_lengths = {'G8': 2, 'G7': 3, 'G6': 4, 'G5': 4, 'G4': 5, 'G3': 5, 'G2': 5, 'G1': 5, 'DB': 6}

    valid_rows = []
    bat_thuong_rows = []
    sai_lech_rows = []
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    df = pd.DataFrame(all_results)
    if df.empty:
        logging.warning(f"No data parsed for {date_str_iso}")
        return

    for dai in df['dai_ten'].unique():
        dai_df = df[df['dai_ten'] == dai]
        is_valid = True
        reasons = []

        # Kiểm tra tổng 18 số
        if len(dai_df) != 18:
            is_valid = False
            reasons.append(f"Tổng số không đủ 18 số (có {len(dai_df)} số)")

        for giai, count in expected_counts.items():
            giai_df = dai_df[dai_df['giai'] == giai]
            if len(giai_df) != count:
                is_valid = False
                reasons.append(f"Giải {giai} có {len(giai_df)} số (kỳ vọng {count})")
            for so in giai_df['so']:
                if len(so) != expected_lengths[giai]:
                    is_valid = False
                    reasons.append(f"Giải {giai} có số độ dài sai: '{so}' ({len(so)} chữ số, kỳ vọng {expected_lengths[giai]})")

        if is_valid:
            valid_rows.extend(dai_df.to_dict('records'))
        else:
            # Điểm 5: Ghi bat_thuong.csv đúng chuẩn cột và có ly_do
            ly_do_str = "; ".join(reasons)
            for r in dai_df.to_dict('records'):
                bat_thuong_rows.append({
                    'ngay': r['ngay'],
                    'thu': r['thu'],
                    'dai_ma': r['dai_ma'],
                    'dai_ten': r['dai_ten'],
                    'giai': r['giai'],
                    'stt': r['stt'],
                    'so': r['so'],
                    'n_chu_so': r['n_chu_so'],
                    'ly_do': ly_do_str,
                    'thoi_diem_phat_hien': now_str
                })
            logging.warning(f"Bất thường dữ liệu: {date_str_iso} - {dai}: {ly_do_str}")

    # Điểm 3: Đối chiếu nguồn 2 (xosodaiphat.com)
    if daiphat_map:
        for r in valid_rows:
            key = (r['dai_ma'], r['giai'], r['stt'])
            so_chinh = r['so']
            if key in daiphat_map:
                so_doi_chieu = daiphat_map[key]
                if so_chinh != so_doi_chieu:
                    sai_lech_rows.append({
                        'ngay': r['ngay'],
                        'dai_ma': r['dai_ma'],
                        'dai_ten': r['dai_ten'],
                        'giai': r['giai'],
                        'stt': r['stt'],
                        'so_chinh': so_chinh,
                        'nguon_chinh': 'xskt.com.vn',
                        'so_doi_chieu': so_doi_chieu,
                        'nguon_doi_chieu': 'xosodaiphat.com',
                        'thoi_diem_phat_hien': now_str
                    })

    # Điểm 4: Ghi ketqua.csv khử trùng theo khoá (ngay, dai_ma, giai, stt)
    if valid_rows:
        df_new = pd.DataFrame(valid_rows).astype(str)
        if os.path.exists(KETQUA_CSV) and os.path.getsize(KETQUA_CSV) > 0:
            df_old = pd.read_csv(KETQUA_CSV, dtype=str)
            # Khử trùng: gộp và giữ dòng đầu tiên nếu đã tồn tại để đảm bảo tính bất biến (idempotent)
            combined = pd.concat([df_old, df_new], ignore_index=True)
            combined.drop_duplicates(subset=['ngay', 'dai_ma', 'giai', 'stt'], keep='first', inplace=True)
        else:
            combined = df_new
        combined.to_csv(KETQUA_CSV, index=False, encoding='utf-8')

    # Điểm 5: Ghi bat_thuong.csv có khử trùng
    if bat_thuong_rows:
        df_bt_new = pd.DataFrame(bat_thuong_rows).astype(str)
        if os.path.exists(BAT_THUONG_CSV) and os.path.getsize(BAT_THUONG_CSV) > 0:
            df_bt_old = pd.read_csv(BAT_THUONG_CSV, dtype=str)
            combined_bt = pd.concat([df_bt_old, df_bt_new], ignore_index=True)
            combined_bt.drop_duplicates(subset=['ngay', 'dai_ma', 'giai', 'stt', 'ly_do'], keep='first', inplace=True)
        else:
            combined_bt = df_bt_new
        combined_bt.to_csv(BAT_THUONG_CSV, index=False, encoding='utf-8')

    # Điểm 3: Ghi sai_lech.csv có khử trùng
    if sai_lech_rows:
        df_sl_new = pd.DataFrame(sai_lech_rows).astype(str)
        if os.path.exists(SAI_LECH_CSV) and os.path.getsize(SAI_LECH_CSV) > 0:
            df_sl_old = pd.read_csv(SAI_LECH_CSV, dtype=str)
            combined_sl = pd.concat([df_sl_old, df_sl_new], ignore_index=True)
            combined_sl.drop_duplicates(subset=['ngay', 'dai_ma', 'giai', 'stt'], keep='first', inplace=True)
        else:
            combined_sl = df_sl_new
        combined_sl.to_csv(SAI_LECH_CSV, index=False, encoding='utf-8')

def parse_date_arg(date_str):
    """Hỗ trợ cả 2 định dạng YYYY-MM-DD và DD-MM-YYYY"""
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        return datetime.datetime.strptime(date_str, "%d-%m-%Y").date()

def main():
    # Điểm 6: Tham số --tu/--den qua CLI
    parser = argparse.ArgumentParser(description="Bộ cào kết quả XSMN (chuẩn hoá dữ liệu địa thống kê)")
    parser.add_argument("--tu", dest="tu_ngay", help="Từ ngày (YYYY-MM-DD hoặc DD-MM-YYYY), mặc định: 2026-10-01", default="2026-10-01")
    parser.add_argument("--den", dest="den_ngay", help="Đến ngày (YYYY-MM-DD hoặc DD-MM-YYYY), mặc định: 2026-10-08", default="2026-10-08")
    args = parser.parse_args()

    start_date = parse_date_arg(args.tu_ngay)
    end_date = parse_date_arg(args.den_ngay)

    print(f"Bắt đầu cào dữ liệu XSMN từ {start_date} đến {end_date}...")
    delta = datetime.timedelta(days=1)
    current_date = start_date

    while current_date <= end_date:
        date_str_vn = current_date.strftime("%d-%m-%Y")
        print(f"Đang xử lý ngày: {date_str_vn} ({THU_MAP.get(current_date.weekday())})")

        # Nguồn 1: xskt.com.vn
        html_xskt = get_html_xskt(date_str_vn)
        if html_xskt:
            results = parse_xsmn(html_xskt, current_date)
        else:
            results = []

        # Nguồn 2: xosodaiphat.com (đối chiếu)
        html_daiphat = get_html_daiphat(date_str_vn)
        daiphat_map = parse_daiphat(html_daiphat) if html_daiphat else {}

        validate_and_save(results, daiphat_map, current_date)
        current_date += delta

    print("Hoàn thành cào và kiểm định dữ liệu!")

if __name__ == "__main__":
    main()
