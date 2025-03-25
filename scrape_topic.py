import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWaitoko
from selenium.webdriver.support import expected_conditions as EC

def open_search_page_and_set_location(driver, location="Toronto"):
    #Go to the main search page
    driver.get("https://211ontario.ca/search/")
    time.sleep(3)  # Wait for page to load

    #Find the location input
    location_box = driver.find_element(By.ID, "searchLocation")  
    location_box.clear()
    location_box.send_keys(location)
    time.sleep(1)
  

def click_main_topic(driver, topic_name="Abuse / Assault"):
    time.sleep(3)
    topic_element = driver.find_element(By.XPATH, f"//a[contains(text(), '{topic_name}')]")
    topic_element.click()
    time.sleep(3)

def click_subtopic(driver, subtopic_name="Child abuse services"):
    """
    Clicks on the subtopic and then clicks "View Resources" to load service listings.
    """
    time.sleep(3)
    try:
        # Find the subtopic heading by text
        heading_element = driver.find_element(
            By.XPATH, 
            f"//div[@class='subtopic-heading' and contains(text(), '{subtopic_name}')]"
        )
        print(f"[INFO] Found subtopic heading: {subtopic_name}")

        # Find the "View Resources" button associated with this heading
        view_resources = heading_element.find_element(
            By.XPATH, "./following-sibling::a[@class='red-button']"
        )
        print("[INFO] Clicking 'View Resources' button...")
        view_resources.click()

        time.sleep(5)
    except Exception as e:
        print(f"[ERROR] Could not click on subtopic '{subtopic_name}': {e}")

def extract_services(driver):
    """
    Scrapes service listings on the final page -- now with pagination support
    using the <span aria-label="Next Page"> element.
    We'll loop through pages until no "Next Page" link is found.
    """
    all_services = []
    page_count = 1

    while True:
        print(f"\n🔍 [INFO] Scraping page {page_count}...\n")
        time.sleep(3)  

        #Find all <div class="title"> elements
        title_elements = driver.find_elements(By.CLASS_NAME, "title")
        
        for title_elem in title_elements:
            try:
                service_name = title_elem.text.strip()
                link_elem = title_elem.find_elements(By.TAG_NAME, "a")
                service_url = link_elem[0].get_attribute("href") if link_elem else None

                # Ignore junk entries
                if not service_name or "SEARCHING FOR" in service_name.upper():
                    continue

                all_services.append({
                    "service_name": service_name,
                    "service_url": service_url
                })
            except Exception as e:
                print(f"[WARNING] Skipping a service due to error: {e}")

        #Check for a "Next Page" link by locating <span aria-label="Next Page">, then going to its parent <a>
        try:
            print("[INFO] Checking for 'Next Page' via <span aria-label='Next Page'>...")

            # Scroll down in case the link is off-screen
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)

            # Wait for <span aria-label="Next Page"> to be clickable, then go to its parent <a>
            next_span = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//span[@aria-label='Next Page']/parent::a"))
            )
            next_page_href = next_span.get_attribute("href")

            if next_page_href:
                print(f"[INFO] Found next page ({page_count + 1}): {next_page_href}")
                driver.get(next_page_href)
                page_count += 1
                time.sleep(5) 
            else:
                print("[INFO] No more pages found.")
                break

        except Exception as e:
            # No "Next Page" found, so we're done
            print(f"[ERROR] Could not find or click 'Next Page': {e}")
            break

    return all_services

def main():
    options = Options()
    options.add_argument("--headless") 
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
       
        open_search_page_and_set_location(driver, location="Toronto")

        
        click_main_topic(driver, topic_name="Abuse / Assault")

      
        click_subtopic(driver, subtopic_name="Child abuse services")

        
        services_data = extract_services(driver)
        if services_data:
            print(f"✅ Found {len(services_data)} services!")
            for s in services_data:
                print("Name:", s["service_name"])
                print("URL:", s["service_url"])
                print("---")
        else:
            print("❌ Found 0 services. Adjust your locators/HTML parsing.")

        

        df = pd.DataFrame(services_data)
        df.to_csv("services_output.csv", index=False)
        print("Saved to services_output.csv!")
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
