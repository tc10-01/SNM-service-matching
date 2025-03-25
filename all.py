import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# ---------- Helper Functions ----------

def dismiss_cookie_banner(driver):
    """
    Removes cookie banner and interfering elements from the DOM so they don't block clicks.
    Adjust the element IDs/selectors as needed.
    """
    try:
        # Remove cookie banner elements
        driver.execute_script("var e = document.getElementById('cookie-banner'); if(e){e.remove();}")
        driver.execute_script("var e = document.getElementById('cookie-text'); if(e){e.remove();}")
        driver.execute_script("var e = document.getElementById('cookie-info'); if(e){e.remove();}")
        # Also remove site navigation that might intercept clicks
        driver.execute_script("var e = document.getElementById('site-nav-lt'); if(e){e.remove();}")
        print("[INFO] Cookie banner and interfering navigation dismissed.")
    except Exception as ex:
        print(f"[WARNING] Could not dismiss interfering elements: {ex}")
    time.sleep(1)

def open_search_page(driver, location="Toronto"):
    """
    Opens the main search page and sets the location.
    """
    driver.get("https://211ontario.ca/search/")
    time.sleep(3)
    dismiss_cookie_banner(driver)
    location_box = driver.find_element(By.ID, "searchLocation")
    location_box.clear()
    location_box.send_keys(location)
    time.sleep(2)

def get_all_topics(driver):
    """
    Collects all main topics available on the search page.
    Returns a list of tuples: (topic_name, topic_element)
    """
    time.sleep(3)
    topics = []
    # Adjust this XPath as needed; here we assume topics are <a> elements with a class that contains "topic"
    topic_elements = driver.find_elements(By.XPATH, "//a[contains(@class, 'topic')]")
    for elem in topic_elements:
        topic_name = elem.text.strip()
        if topic_name:
            topics.append((topic_name, elem))
    return topics

def click_topic(driver, topic_name="Abuse / Assault"):
    """
    Finds and clicks the main topic by its text.
    """
    time.sleep(3)
    dismiss_cookie_banner(driver)
    topic_element = driver.find_element(By.XPATH, f"//a[contains(text(), '{topic_name}')]")
    topic_element.click()
    time.sleep(3)

def get_subtopics(driver):
    """
    Returns a list of tuples: (subtopic_name, view_resources_button)
    from the currently loaded topic page.
    """
    time.sleep(3)
    dismiss_cookie_banner(driver)
    subtopics = []
    heading_elements = driver.find_elements(By.XPATH, "//div[@class='subtopic-heading']")
    for heading in heading_elements:
        subtopic_name = heading.text.strip()
        try:
            view_btn = heading.find_element(By.XPATH, "./following-sibling::a[@class='red-button']")
            subtopics.append((subtopic_name, view_btn))
        except Exception as e:
            print(f"[WARNING] Could not get View Resources for subtopic '{subtopic_name}': {e}")
    return subtopics

def click_subtopic(driver, subtopic_name="Child abuse services", attempts=3):
    """
    Attempts to click the subtopic's "View Resources" button.
    Retries up to 'attempts' times after dismissing interfering elements
    and scrolling the button into view.
    Returns True if successful, False otherwise.
    """
    for i in range(attempts):
        time.sleep(3)
        dismiss_cookie_banner(driver)
        try:
            # Re-locate the subtopic heading to avoid stale element errors
            heading_element = driver.find_element(
                By.XPATH, f"//div[@class='subtopic-heading' and contains(text(), '{subtopic_name}')]"
            )
            print(f"[INFO] Found subtopic heading: {subtopic_name}")
            view_resources = heading_element.find_element(
                By.XPATH, "./following-sibling::a[@class='red-button']"
            )
            # Scroll into view
            driver.execute_script("arguments[0].scrollIntoView(true);", view_resources)
            print(f"[INFO] Attempt {i+1}: Forcing click on 'View Resources' for '{subtopic_name}'...")
            driver.execute_script("arguments[0].click();", view_resources)
            time.sleep(5)
            return True
        except Exception as e:
            print(f"[ERROR] Attempt {i+1} to click subtopic '{subtopic_name}' failed: {e}")
    return False

def extract_services(driver):
    """
    Scrapes service listings on the current subtopic page and handles pagination.
    Returns a list of dictionaries with keys: 'service_name' and 'service_url'.
    """
    all_services = []
    page_count = 1

    while True:
        print(f"\n🔍 [INFO] Scraping page {page_count}...\n")
        time.sleep(3)
        dismiss_cookie_banner(driver)

        # Find all service containers (assumed to be in <div class="title">)
        title_elements = driver.find_elements(By.CLASS_NAME, "title")
        for title_elem in title_elements:
            try:
                service_name = title_elem.text.strip()
                link_elem = title_elem.find_elements(By.TAG_NAME, "a")
                service_url = link_elem[0].get_attribute("href") if link_elem else None

                # Skip unwanted entries
                if not service_name or "SEARCHING FOR" in service_name.upper():
                    continue

                all_services.append({
                    "service_name": service_name,
                    "service_url": service_url
                })
            except Exception as e:
                print(f"[WARNING] Skipping a service due to error: {e}")

        # Pagination: locate the Next Page link via the <span aria-label='Next Page'> and then its parent <a>
        try:
            print("[INFO] Checking for 'Next Page' link via <span aria-label='Next Page'>...")
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            next_page_element = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@aria-label='Next Page']/parent::a"))
            )
            next_page_href = next_page_element.get_attribute("href")
            if next_page_href:
                print(f"[INFO] Found next page: {next_page_href}")
                driver.get(next_page_href)
                page_count += 1
                time.sleep(5)
            else:
                print("[INFO] No more pages found.")
                break
        except Exception as e:
            print(f"[INFO] No 'Next Page' link found or could not click it: {e}")
            break

    print(f"✅ [INFO] Scraping complete. Total services found: {len(all_services)}")
    return all_services

# ---------- Main Function ----------

def main():
    options = Options()
    options.add_argument("--headless")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    all_results = []
    try:
        open_search_page(driver, location="Toronto")
        topics = get_all_topics(driver)
        print(f"[INFO] Found {len(topics)} topics.")

        for topic_name, _ in topics:
            print(f"\n===== Scraping Topic: {topic_name} =====\n")
            # Reload the search page for each topic
            open_search_page(driver, location="Toronto")
            try:
                click_topic(driver, topic_name)
            except Exception as e:
                print(f"[ERROR] Could not click topic '{topic_name}': {e}")
                continue

            subtopics = get_subtopics(driver)
            print(f"[INFO] Found {len(subtopics)} subtopics under {topic_name}.")

            # Loop through each subtopic (re-read the list each time)
            for i in range(len(subtopics)):
                subtopics = get_subtopics(driver)
                if i >= len(subtopics):
                    break
                subtopic_name, _ = subtopics[i]
                print(f"\n--> Scraping Subtopic: {subtopic_name}")
                if not click_subtopic(driver, subtopic_name):
                    print(f"[ERROR] Failed to click subtopic '{subtopic_name}'. Skipping...")
                    continue

                services = extract_services(driver)
                for s in services:
                    s["Topic"] = topic_name
                    s["Subtopic"] = subtopic_name
                    all_results.append(s)

                # After scraping a subtopic, return to the topic page for the next subtopic
                open_search_page(driver, location="Toronto")
                try:
                    click_topic(driver, topic_name)
                except Exception as e:
                    print(f"[ERROR] Could not re-click topic '{topic_name}': {e}")
                    break
                time.sleep(2)

        df = pd.DataFrame(all_results)
        df.to_csv("all_services_output.csv", index=False)
        print(f"\n🎯 SUCCESS: Scraped {len(all_results)} services across all topics and subtopics.")
        print("📁 Saved to all_services_output.csv!")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
