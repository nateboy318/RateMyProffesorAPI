import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

DATASET_PATH = "professors_dataset.jsonl"

def get_teacher_tags(soup):
    tags_container = None
    for tag in soup.find_all(True, class_=True):
        if any('TeacherTags' in c for c in tag.get('class', [])):
            tags_container = tag
            break
    if tags_container:
        return [tag.get_text(strip=True) for tag in tags_container.find_all('span')]
    return []

def get_feedback_numbers(soup):
    numbers = []
    for tag in soup.find_all(True, class_=True):
        if any('FeedbackNumber' in c for c in tag.get('class', [])):
            numbers.append(tag.get_text(strip=True))
    return numbers

def get_teacher_department(soup):
    tag = soup.find(class_=lambda c: c and 'TeacherDepartment' in c)
    return tag.get_text(strip=True) if tag else None

def get_name_title(soup):
    tag = soup.find(class_=lambda c: c and 'NameTitle' in c)
    return tag.get_text(strip=True) if tag else None

def get_rating_value_numerator(soup):
    tag = soup.find(class_=lambda c: c and 'RatingValue__Numerator' in c)
    return tag.get_text(strip=True) if tag else None

def get_num_ratings(soup):
    tag = soup.find(class_=lambda c: c and 'NumRatings' in c)
    return tag.get_text(strip=True) if tag else None

def get_all_rating_bodies(soup):
    bodies = []
    for rating_body in soup.find_all(class_=lambda c: c and 'Rating__RatingBody' in c):
        card_nums = rating_body.find_all(class_=lambda c: c and 'CardNumRating__CardNumRatingNumber' in c)
        quality = card_nums[0].get_text(strip=True) if len(card_nums) > 0 else None
        difficulty = card_nums[1].get_text(strip=True) if len(card_nums) > 1 else None
        for_credit = None
        attendance = None
        for meta in rating_body.find_all(class_='MetaItem__StyledMetaItem-y0ixml-0'):
            text = meta.get_text(strip=True)
            if text.startswith('For Credit'):
                for_credit = meta.find('span').get_text(strip=True)
            elif text.startswith('Attendance'):
                attendance = meta.find('span').get_text(strip=True)
        comment_tag = rating_body.find(class_=lambda c: c and 'Comments__StyledComments' in c)
        comment = comment_tag.get_text(strip=True) if comment_tag else None
        tags = []
        tags_container = rating_body.find(class_=lambda c: c and 'RatingTags__StyledTags' in c)
        if tags_container:
            tags = [tag.get_text(strip=True) for tag in tags_container.find_all('span')]
        bodies.append({
            'quality': quality,
            'difficulty': difficulty,
            'for_credit': for_credit,
            'attendance': attendance,
            'comment': comment,
            'tags': tags
        })
    return bodies

def clean_name_title(name_title):
    if not name_title:
        return name_title
    name_title = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name_title)
    name_title = re.sub(r'(department)', r' \1', name_title)
    name_title = re.sub(r'(at)', r' \1', name_title)
    name_title = re.sub(r'\s+', ' ', name_title).strip()
    return name_title

def clean_num_ratings(num_ratings):
    if not num_ratings:
        return num_ratings
    num_ratings = re.sub(r'(?<=[a-zA-Z])(?=\d)', ' ', num_ratings)
    num_ratings = re.sub(r'(?<=\d)(?=[a-zA-Z])', ' ', num_ratings)
    num_ratings = re.sub(r'\s+', ' ', num_ratings).strip()
    return num_ratings

def fetch_professor_data(professor_id, max_retries=3, retry_delay=2):
    url = f"https://www.ratemyprofessors.com/professor/{professor_id}"
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
    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code != 200:
                return None
            soup = BeautifulSoup(response.text, "html.parser")
            tags = get_teacher_tags(soup)
            feedback_numbers = get_feedback_numbers(soup)
            teacher_department = get_teacher_department(soup)
            name_title = clean_name_title(get_name_title(soup))
            rating_value_numerator = get_rating_value_numerator(soup)
            num_ratings = clean_num_ratings(get_num_ratings(soup))
            all_ratings = get_all_rating_bodies(soup)
            would_take_again = feedback_numbers[0] if len(feedback_numbers) > 0 else None
            level_of_difficulty = feedback_numbers[1] if len(feedback_numbers) > 1 else None
            professor_data = {
                "professor_id": professor_id,
                "name_title": name_title,
                "department": teacher_department,
                "main_rating": rating_value_numerator,
                "num_ratings": num_ratings,
                "tags": tags,
                "would_take_again": would_take_again,
                "level_of_difficulty": level_of_difficulty,
                "ratings": all_ratings
            }
            if name_title or teacher_department:
                print(f"Fetched professor {professor_id}")
                return professor_data
            return None
        except Exception as e:
            print(f"Error for professor {professor_id} (attempt {attempt}): {e}")
            if attempt < max_retries:
                time.sleep(retry_delay)
            else:
                print(f"Giving up on professor {professor_id} after {max_retries} attempts.")
    return None

def save_professor_jsonl(professor_data, filename=DATASET_PATH, lock=None):
    line = json.dumps(professor_data, ensure_ascii=False) + "\n"
    try:
        print(f"Saving professor {professor_data.get('professor_id')} to {filename}")
        if lock:
            with lock:
                with open(filename, "a", encoding="utf-8") as f:
                    f.write(line)
        else:
            with open(filename, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception as e:
        print(f"Error writing to {filename}: {e}")

def get_last_professor_id(filename):
    last_id = 0
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    obj = json.loads(line)
                    pid = int(obj.get("professor_id", 0))
                    if pid > last_id:
                        last_id = pid
                except Exception:
                    continue
    return last_id

if __name__ == "__main__":
    filename = DATASET_PATH
    dataset_lock = threading.Lock()
    max_workers = 500  # Number of threads
    start_id = 1
    end_id = 100000000
    # Resume logic
    if os.path.exists(filename):
        print(f"Resuming from existing file: {filename}")
        last_id = get_last_professor_id(filename)
        if last_id >= start_id:
            start_id = last_id + 1
        print(f"Resuming from professor_id {start_id}")
    else:
        print(f"Starting fresh. Output file: {filename}")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(fetch_professor_data, pid): pid for pid in range(start_id, end_id)}
        for future in as_completed(futures):
            result = future.result()
            if result:
                save_professor_jsonl(result, filename, lock=dataset_lock) 