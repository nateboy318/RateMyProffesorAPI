import requests
from bs4 import BeautifulSoup
import json
import re

def get_teacher_tags(soup):
    """Extracts professor tags from any element whose class contains 'TeacherTags'."""
    tags_container = None
    for tag in soup.find_all(True, class_=True):
        if any('TeacherTags' in c for c in tag.get('class', [])):
            tags_container = tag
            break
    if tags_container:
        return [tag.get_text(strip=True) for tag in tags_container.find_all('span')]
    return []

def get_feedback_numbers(soup):
    """Extracts feedback numbers from any element whose class contains 'FeedbackNumber'."""
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
        # Quality and Difficulty
        card_nums = rating_body.find_all(class_=lambda c: c and 'CardNumRating__CardNumRatingNumber' in c)
        quality = card_nums[0].get_text(strip=True) if len(card_nums) > 0 else None
        difficulty = card_nums[1].get_text(strip=True) if len(card_nums) > 1 else None
        # For Credit and Attendance
        for_credit = None
        attendance = None
        for meta in rating_body.find_all(class_='MetaItem__StyledMetaItem-y0ixml-0'):
            text = meta.get_text(strip=True)
            if text.startswith('For Credit'):
                for_credit = meta.find('span').get_text(strip=True)
            elif text.startswith('Attendance'):
                attendance = meta.find('span').get_text(strip=True)
        # Comments
        comment_tag = rating_body.find(class_=lambda c: c and 'Comments__StyledComments' in c)
        comment = comment_tag.get_text(strip=True) if comment_tag else None
        # Tags
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
    # Insert a space before capital letters that follow lowercase letters
    name_title = re.sub(r'(?<=[a-z])(?=[A-Z])', ' ', name_title)
    # Insert a space before 'department' and 'at' if they are stuck to previous words
    name_title = re.sub(r'(department)', r' \1', name_title)
    name_title = re.sub(r'(at)', r' \1', name_title)
    # Remove extra spaces
    name_title = re.sub(r'\s+', ' ', name_title).strip()
    return name_title

def clean_num_ratings(num_ratings):
    if not num_ratings:
        return num_ratings
    # Insert a space between letters and numbers
    num_ratings = re.sub(r'(?<=[a-zA-Z])(?=\d)', ' ', num_ratings)
    num_ratings = re.sub(r'(?<=\d)(?=[a-zA-Z])', ' ', num_ratings)
    # Remove extra spaces
    num_ratings = re.sub(r'\s+', ' ', num_ratings).strip()
    return num_ratings

professor_id = 1657862
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
    "DNT": "1",  # Do Not Track Request Header
}

response = requests.get(url, headers=headers)

if response.status_code == 200:
    print("Successfully fetched the page!")
    soup = BeautifulSoup(response.text, "html.parser")
    print(soup.title.text)
    tags = get_teacher_tags(soup)
    feedback_numbers = get_feedback_numbers(soup)
    teacher_department = get_teacher_department(soup)
    name_title = get_name_title(soup)
    name_title = clean_name_title(name_title)
    rating_value_numerator = get_rating_value_numerator(soup)
    num_ratings = get_num_ratings(soup)
    num_ratings = clean_num_ratings(num_ratings)
    all_ratings = get_all_rating_bodies(soup)
    # Map feedback numbers
    would_take_again = feedback_numbers[0] if len(feedback_numbers) > 0 else None
    level_of_difficulty = feedback_numbers[1] if len(feedback_numbers) > 1 else None
    # Build JSON object
    professor_data = {
        "name_title": name_title,
        "department": teacher_department,
        "main_rating": rating_value_numerator,
        "num_ratings": num_ratings,
        "tags": tags,
        "would_take_again": would_take_again,
        "level_of_difficulty": level_of_difficulty,
        "ratings": all_ratings
    }
    print("\nProfessor JSON Data:")
    print(json.dumps(professor_data, indent=2))
else:
    print(f"Failed to fetch the page. Status code: {response.status_code}")
