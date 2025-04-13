import requests
from bs4 import BeautifulSoup

BASE_URL = "https://catalog.ucsc.edu"
COURSES_URL = BASE_URL + "/en/Current/General-Catalog/Courses"

def fetch_all_ucsc_classes():
    """
    Returns a sorted list of all course codes found on the UCSC Catalog site.
    Example format: ["CSE 12", "CSE 107", "MATH 19A", "MATH 19B", ...]
    """
    all_classes = set()  # use a set to avoid duplicates

    # 1) Fetch the main "Courses" page
    resp = requests.get(COURSES_URL)
    if not resp.ok:
        print("Failed to fetch main courses page.")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    
    # 2) Find all <a> that link to departmental sub-pages
    #    They typically look like: <a href="/en/Current/General-Catalog/Courses/CSE-Computer-Science-and-Engineering">
    department_links = []
    for link in soup.select("li.toccatalog a"):
        href = link.get("href", "")
        # skip any external or anchor link
        if href.startswith("/en/Current/General-Catalog/Courses/") and "http" not in href:
            department_links.append(BASE_URL + href)

    # 3) For each department link, open and parse course codes
    for dlink in department_links:
        d_resp = requests.get(dlink)
        if not d_resp.ok:
            continue

        d_soup = BeautifulSoup(d_resp.text, "html.parser")
        # Typically courses are in <h3> or <h2> elements with text like "CSE 107"
        # or they might appear in <li> / <span>. We'll do a guess:
        possible_courses = d_soup.select("h2.course-title, h3.course-title, li.course")
        
        for ctitle in possible_courses:
            text = ctitle.get_text(strip=True)
            # text might be "CSE 107 Computer Networking" or "CSE 107"
            # We just want "CSE 107" part
            # We'll assume the course code is always the first 1-2 tokens
            # But let's do a quick parse if possible
            parts = text.split()
            if len(parts) >= 2:
                dept = parts[0]
                course_num = parts[1]
                # Combine them
                # (You might refine logic to handle "19A", "19B", etc.)
                # If the first token isn't uppercase or doesn't look like a dept, skip
                if dept.isalpha() and not dept.endswith(":"):
                    code = dept + " " + course_num
                    all_classes.add(code)

    return sorted(all_classes)