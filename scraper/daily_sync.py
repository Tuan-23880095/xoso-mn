import os
import sys
import datetime
import subprocess
import logging
import argparse
import pandas as pd

SCRAPER_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_DIR = os.path.abspath(os.path.join(SCRAPER_DIR, ".."))
sys.path.append(SCRAPER_DIR)

import scraper_xsmn

LOGS_DIR = os.path.join(REPO_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)
sync_log_file = os.path.join(LOGS_DIR, "daily_sync.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(sync_log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

def get_latest_date():
    csv_path = scraper_xsmn.KETQUA_CSV
    if not os.path.exists(csv_path) or os.path.getsize(csv_path) == 0:
        return None
    try:
        df = pd.read_csv(csv_path, usecols=['ngay'], dtype=str)
        if df.empty:
            return None
        valid_dates = pd.to_datetime(df['ngay'], errors='coerce').dropna()
        if valid_dates.empty:
            return None
        return valid_dates.max().date()
    except Exception as e:
        logging.error(f"Loi khi doc ketqua.csv: {e}")
        return None

def get_target_date():
    now = datetime.datetime.now()
    # Ket qua XSMN xo vao khoang 16:15 - 16:40
    if now.hour > 16 or (now.hour == 16 and now.minute >= 40):
        return now.date()
    else:
        # Truoc 16:40 chua co ket qua hom nay -> muc tieu la hom qua
        return now.date() - datetime.timedelta(days=1)

def run_sync(max_days=None):
    latest_date = get_latest_date()
    target_date = get_target_date()
    
    logging.info("=== BAT DAU DONG BO XSMN ===")
    logging.info(f"Thoi diem hien tai: {datetime.datetime.now()}")
    logging.info(f"Ngay moi nhat trong CSV: {latest_date}")
    logging.info(f"Ngay dich can dong bo: {target_date}")
    
    if latest_date is None:
        start_date = datetime.date(2026, 10, 1)
    else:
        start_date = latest_date + datetime.timedelta(days=1)
        
    if start_date > target_date:
        logging.info("Du lieu da day du va moi nhat. Khong can cao them.")
        return False
        
    end_date = target_date
    if max_days and max_days > 0:
        calculated_end = start_date + datetime.timedelta(days=max_days - 1)
        if calculated_end < end_date:
            end_date = calculated_end
            
    logging.info(f"Khoang ngay can cao: {start_date} -> {end_date}")
    
    current_date = start_date
    delta = datetime.timedelta(days=1)
    scraped_any = False
    
    while current_date <= end_date:
        date_str_vn = current_date.strftime("%d-%m-%Y")
        thu_str = scraper_xsmn.THU_MAP.get(current_date.weekday(), "")
        logging.info(f"Dang xu ly ngay: {date_str_vn} ({thu_str})...")
        
        # Nguon chinh: xskt.com.vn
        try:
            html_xskt = scraper_xsmn.get_html_xskt(date_str_vn)
            results = scraper_xsmn.parse_xsmn(html_xskt, current_date) if html_xskt else []
        except Exception as e:
            logging.error(f"Loi khi cao xskt {date_str_vn}: {e}")
            results = []
            
        # Nguon doi chieu: xosodaiphat.com
        try:
            html_daiphat = scraper_xsmn.get_html_daiphat(date_str_vn)
            daiphat_map = scraper_xsmn.parse_daiphat(html_daiphat) if html_daiphat else {}
        except Exception as e:
            logging.error(f"Loi khi cao daiphat {date_str_vn}: {e}")
            daiphat_map = {}
            
        if not results:
            logging.warning(f"Chua co ket qua hoac trang loi cho ngay {date_str_vn}. Thoat em, khong ghi dong thieu.")
        else:
            scraper_xsmn.validate_and_save(results, daiphat_map, current_date)
            scraped_any = True
            logging.info(f"Da ghi va doi chieu xong ngay {date_str_vn} ({len(results)} ban ghi).")
            
        current_date += delta
        
    return scraped_any

def git_commit_and_push():
    try:
        # Kiem tra status trong data/ va logs/
        res = subprocess.run(
            ["git", "-C", REPO_DIR, "status", "--porcelain", "data/", "logs/"],
            capture_output=True, text=True, check=True
        )
        if not res.stdout.strip():
            logging.info("Git: Khong co thay doi trong data/ hoac logs/ de commit.")
            return True
            
        logging.info("Git: Phat hien du lieu moi trong data/ hoac logs/. Dang commit & push...")
        subprocess.run(["git", "-C", REPO_DIR, "add", "data/", "logs/"], check=True)
        
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        commit_msg = f"chore(data): cap nhat ket qua XSMN tu dong ({now_str})"
        subprocess.run(["git", "-C", REPO_DIR, "commit", "-m", commit_msg], check=True)
        
        # Push len nhanh main va local/scraper
        logging.info("Git: Push len origin main...")
        try:
            subprocess.run(["git", "-C", REPO_DIR, "push", "origin", "HEAD:main"], check=True)
            logging.info("Git: Push len origin main thanh cong!")
        except Exception as e:
            logging.error(f"Loi push main: {e}")
            
        try:
            subprocess.run(["git", "-C", REPO_DIR, "push", "origin", "HEAD:local/scraper"], check=True)
            logging.info("Git: Push len origin local/scraper thanh cong!")
        except Exception as e:
            logging.error(f"Loi push local/scraper: {e}")
            
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"Loi Git process: {e}")
        return False
    except Exception as e:
        logging.error(f"Loi khong xac dinh: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Tu dong cao bu va dong bo hang ngay XSMN")
    parser.add_argument("--max-days", type=int, default=None, help="Gioi han so ngay cao trong mot lan chay")
    parser.add_argument("--no-git", action="store_true", help="Bo qua buoc git push")
    args = parser.parse_args()
    
    has_changes = run_sync(max_days=args.max_days)
    if not args.no_git:
        git_commit_and_push()
    logging.info("=== KET THUC TIEN TRINH DONG BO ===")

if __name__ == "__main__":
    main()
