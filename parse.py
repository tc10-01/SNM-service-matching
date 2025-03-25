import time
import json
import openai
import os
from dotenv import load_dotenv

# Install: pip install selenium webdriver-manager openai python-dotenv
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

############################
# 1) CONFIG
############################

# Load environment variables
load_dotenv()
openai.api_key = os.getenv('OPENAI_API_KEY')

# List of URLs to scrape
URLS = [
    "https://211ontario.ca/service/70568694/canadian-centre-for-child-protection-canadian-centre-for-child-protection/?searchLocation=Toronto&topicPath=2&latitude=43.653226&longitude=-79.3831843&sd=25&ss=Distance",
    # ... add more
]

# The fields you want in the final JSON
FIELDS = [
    "name",
    "description",
    "location",
    "contact_phone",
    "service_hours",
    "eligibility_criteria",
    "fees",
    "languages_offered",
    "capacity"
]

############################
# 2) LLM Extraction Function
############################

def llm_extract_text_to_json(page_text: str) -> dict:
    """
    Sends 'page_text' to an LLM with a prompt that requests a JSON extraction.
    Returns a Python dict from the parsed JSON.
    """
    prompt = f"""
You are an expert information extraction assistant. 
Given the text below, extract these fields in valid JSON ONLY:

{FIELDS}

RULES:
- Output ONLY JSON, no extra text
- Use null for any field not found
- "languages_offered" can be an array if multiple
- "contact_phone" can be a single string or array if multiple

Text:
\"\"\"{page_text}\"\"\"
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or "gpt-4"
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )
        content = response["choices"][0]["message"]["content"]
        
        # Attempt to parse JSON from LLM output
        data = json.loads(content)
        return data
    
    except json.JSONDecodeError:
        print("LLM returned invalid JSON. Full content was:")
        print(content)
        return {}
    except Exception as e:
        print("Error calling LLM:", e)
        return {}

############################
# 3) Main Flow
############################

def main():
    # Setup Chrome in headless mode (invisible browser)
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    
    # Initialize the Chrome driver (automatically downloaded by webdriver_manager)
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    all_results = []

    for url in URLS:
        print(f"\nScraping URL: {url}")
        
        try:
            # 1) Go to the URL
            driver.get(url)
            
            # 2) Wait for page to load (increase if the site is slow)
            time.sleep(3)
            
            # (OPTIONAL) Insert any multi-step logic here:
            # e.g., fill a search box, click a subtopic, remove banners, etc.
            #
            # example:
            # location_box = driver.find_element(By.ID, "searchLocation")
            # location_box.clear()
            # location_box.send_keys("Toronto")
            # time.sleep(2)
            # location_box.send_keys(Keys.ENTER)
            # ...
            
            # 3) Now get the visible text from the page
            body_element = driver.find_element(By.TAG_NAME, "body")
            page_text = body_element.text
            
            # 4) Send the text to the LLM for structured extraction
            extracted = llm_extract_text_to_json(page_text)
            
            # 5) Store the result
            row = {"url": url}
            row.update(extracted)
            all_results.append(row)
            
            # Sleep a bit to avoid rate-limiting
            time.sleep(2)
            
        except Exception as e:
            print(f"Error scraping {url}: {e}")

    # Close the browser
    driver.quit()

    # Print out the final JSON
    print("\nALL EXTRACTED DATA:\n")
    print(json.dumps(all_results, indent=2))

if __name__ == "__main__":
    main()
