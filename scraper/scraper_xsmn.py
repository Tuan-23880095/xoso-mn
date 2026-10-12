import requests
from bs4 import BeautifulSoup
import pandas as pd
import os
import time
import datetime
import csv
import logging

# Setup Logging
log_file = os.path.abspath(os.path.join(os.path.dirname(__file__), '../logs/scraper.log'))
logging.basicConfig(filename=log_file, level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
HTML_CACHE_DIR = os.path.join(DATA_DIR, 'raw_html')
KETQUA_CSV = os.path.join(DATA_DIR, 'ketqua.csv')
BAT_THUONG_CSV = os.path.join(DATA_DIR, 'bat_thuong.csv')

HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36'}

def get_html(date_str):
    """Fetch HTML with caching"""
    cache_path = os.path.join(HTML_CACHE_DIR, f"{date_str}.html")
    if os.path.exists(cache_path):
        with open(cache_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    # Remove leading zeros for xskt.com.vn URL
    d, m, y = date_str.split('-')
    url = f"https://xskt.com.vn/xsmn/ngay-{int(d)}-{int(m)}-{y}"
    
    try:
        time.sleep(2) # Rate limit: <= 1 req/2s
        resp = requests.get(url, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        html = resp.text
        with open(cache_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return html
    except Exception as e:
        logging.error(f"Error fetching {url}: {e}")
        return None

def parse_xsmn(html, date_str):
    soup = BeautifulSoup(html, 'html.parser')
    table = soup.find('table', id='MN0')
    if not table:
        return []
        
    # Get Dai names
    header_tr = table.find('tr')
    th_elements = header_tr.find_all('th')[1:] # Skip first 'Giai' column
    dais = [th.text.strip() for th in th_elements]
    
    results = []
    
    rows = table.find_all('tr')[1:] # Skip header
    # Giai mappings on xskt.com.vn:
    giai_map = {"ĐB": "DB", "G.1": "G1", "G.2": "G2", "G.3": "G3", "G.4": "G4", "G.5": "G5", "G.6": "G6", "G.7": "G7", "G.8": "G8"}
    
    for row in rows:
        giai_td = row.find('td')
        if not giai_td: continue
        giai_title = giai_td.text.strip()
        giai = giai_map.get(giai_title)
        if not giai: continue
        
        td_elements = row.find_all('td')[1:]
        for i, td in enumerate(td_elements):
            dai_ten = dais[i]
            dai_ma = ''.join([c for c in dai_ten if c.isupper()]) # Basic Dai code
            
            # numbers could be separated by space
            numbers_text = td.get_text(separator=' ').strip()
            if not numbers_text: continue
            
            numbers = numbers_text.split()
            for stt, num in enumerate(numbers, 1):
                results.append({
                    'ngay': date_str,
                    'thu': '', # TBD
                    'dai_ma': dai_ma,
                    'dai_ten': dai_ten,
                    'giai': giai,
                    'stt': stt,
                    'so': num,
                    'n_chu_so': len(num),
                    'nguon': 'xskt.com.vn',
                    'thoi_diem_cao': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
    return results

def validate_and_save(all_results, date_str):
    expected_counts = {'G8':1, 'G7':1, 'G6':3, 'G5':1, 'G4':7, 'G3':2, 'G2':1, 'G1':1, 'DB':1}
    expected_lengths = {'G8':2, 'G7':3, 'G6':4, 'G5':4, 'G4':5, 'G3':5, 'G2':5, 'G1':5, 'DB':6}
    
    valid_rows = []
    bat_thuong_rows = []
    
    df = pd.DataFrame(all_results)
    if df.empty:
        logging.warning(f"No data parsed for {date_str}")
        return
        
    for dai in df['dai_ten'].unique():
        dai_df = df[df['dai_ten'] == dai]
        is_valid = True
        
        # Check rule 18 numbers
        if len(dai_df) != 18:
            is_valid = False
            
        for giai, count in expected_counts.items():
            giai_df = dai_df[dai_df['giai'] == giai]
            if len(giai_df) != count:
                is_valid = False
            for so in giai_df['so']:
                if len(so) != expected_lengths[giai]:
                    is_valid = False
                    
        if is_valid:
            valid_rows.extend(dai_df.to_dict('records'))
        else:
            bat_thuong_rows.extend(dai_df.to_dict('records'))
            logging.warning(f"Bất thường dữ liệu: {date_str} - {dai}")
            
    # Append to CSV
    write_header = not os.path.exists(KETQUA_CSV)
    if valid_rows:
        pd.DataFrame(valid_rows).to_csv(KETQUA_CSV, mode='a', header=write_header, index=False, encoding='utf-8')
    
    write_header_bt = not os.path.exists(BAT_THUONG_CSV)
    if bat_thuong_rows:
        pd.DataFrame(bat_thuong_rows).to_csv(BAT_THUONG_CSV, mode='a', header=write_header_bt, index=False, encoding='utf-8')

def main():
    print("Bắt đầu cào dữ liệu XSMN...")
    start_date = datetime.date(2026, 10, 1) # Test for just 1 week first
    end_date = datetime.date(2026, 10, 8)
    
    delta = datetime.timedelta(days=1)
    current_date = start_date
    
    while current_date <= end_date:
        date_str = current_date.strftime("%d-%m-%Y")
        print(f"Đang xử lý: {date_str}")
        html = get_html(date_str)
        if html:
            results = parse_xsmn(html, current_date.strftime("%Y-%m-%d"))
            validate_and_save(results, current_date.strftime("%Y-%m-%d"))
        current_date += delta
        
    print("Hoàn thành!")

if __name__ == "__main__":
    main()


