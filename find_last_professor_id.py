import requests
from bs4 import BeautifulSoup
import re
import time

def get_teacher_department(soup):
    tag = soup.find(class_=lambda c: c and 'TeacherDepartment' in c)
    return tag.get_text(strip=True) if tag else None

def get_name_title(soup):
    tag = soup.find(class_=lambda c: c and 'NameTitle' in c)
    return tag.get_text(strip=True) if tag else None

def clean_name_title(name_title):
    if not name_title:
        return name_title
    name_title = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name_title)
    name_title = re.sub(r'(department)', r' \1', name_title)
    name_title = re.sub(r'(at)', r' \1', name_title)
    name_title = re.sub(r'\s+', ' ', name_title).strip()
    return name_title

def professor_exists(professor_id, headers, max_retries=3, retry_delay=2):
    url = f"https://www.ratemyprofessors.com/professor/{professor_id}"
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return False
            soup = BeautifulSoup(response.text, "html.parser")
            name_title = clean_name_title(get_name_title(soup))
            teacher_department = get_teacher_department(soup)
            if name_title or teacher_department:
                return True
            return False
        except Exception as e:
            print(f"Error for professor {professor_id} (attempt {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                print(f"Giving up on professor {professor_id} after {max_retries} attempts.")
    return False

if __name__ == "__main__":
    start_id = 1657864
    # Pick a high upper bound; can increase if needed
    upper_bound = 2000000
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Connection": "keep-alive",
        "Referer": "https://www.google.com/",
        "DNT": "1",
    }

    # First, find an upper bound where the professor does NOT exist
    low = start_id
    high = upper_bound
    while professor_exists(high, headers):
        print(f"Professor {high} exists, increasing upper bound...")
        low = high
        high *= 2
        if high > 10000000:
            print("Upper bound too high, stopping at 10,000,000.")
            high = 10000000
            break

    print(f"Binary search between {low} and {high}")
    # Binary search for the last valid professor ID
    result = low
    while low <= high:
        mid = (low + high) // 2
        if professor_exists(mid, headers):
            result = mid
            low = mid + 1
        else:
            high = mid - 1
    print(f"Highest valid professor ID: {result}")
