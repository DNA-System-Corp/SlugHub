# event_scraper.py
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://calendar.ucsc.edu/calendar/"

def scrape_ucsc_events(start_page=1, max_pages=5):
    events = []

    for page_num in range(start_page, start_page + max_pages):
        url = f"{BASE_URL}{page_num}"
        response = requests.get(url)
        if response.status_code != 200:
            break

        soup = BeautifulSoup(response.text, "html.parser")
        event_cards = soup.find_all("div", class_="em-card")
        if not event_cards:
            break

        for card in event_cards:
            try:
                title = card.find("h3", class_="em-card_title").get_text(strip=True)
                date = card.find_all("p", class_="em-card_event-text")[0].get_text(strip=True)

                location = "—"
                price = "—"

                texts = card.find_all("p", class_="em-card_event-text")
                if len(texts) > 1:
                    location = texts[1].get_text(strip=True)

                price_tag = card.find("span", class_="em-price")
                if price_tag:
                    price = price_tag.get_text(strip=True)

                events.append({
                    "title": title,
                    "date": date,
                    "location": location,
                    "price": price
                })
            except Exception as e:
                print("Skipping a card due to error:", e)
                continue

    return events