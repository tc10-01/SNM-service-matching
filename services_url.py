import pandas as pd
import time
import json
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import os

# Configuration
DEEPSEEK_API_KEY = "your_api_key_here"  # Replace with your DeepSeek API key
BACKUP_DIR = "backups"
DELAY_BETWEEN_REQUESTS = 2  # Seconds between requests
MAX_RETRIES = 3  # Maximum number of retry attempts

# Ensure backup directory exists
os.makedirs(BACKUP_DIR, exist_ok=True)

class ServiceScraper:
    def __init__(self):
        self.setup_driver()
        self.session = requests.Session()
        
    def setup_driver(self):
        """Initialize the Chrome WebDriver with appropriate options"""
        options = Options()
        options.add_argument("--headless")  # Run in headless mode
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
    def get_website_content(self, url, max_retries=MAX_RETRIES):
        """Fetch and clean website content with retry mechanism"""
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove unwanted elements
                for element in soup(['script', 'style', 'nav', 'footer', 'iframe']):
                    element.decompose()
                
                # Get text content
                text = soup.get_text(separator='\n', strip=True)
                
                # Clean and normalize text
                lines = [line.strip() for line in text.splitlines() if line.strip()]
                cleaned_text = '\n'.join(lines)
                
                return cleaned_text[:15000]  # Limit content length for API
                
            except Exception as e:
                if attempt == max_retries - 1:
                    print(f"Failed to fetch content from {url} after {max_retries} attempts: {str(e)}")
                    return None
                time.sleep(DELAY_BETWEEN_REQUESTS)
                
        return None

    def analyze_with_deepseek(self, website_content, service_name):
        """Analyze website content using DeepSeek Chat API"""
        if not website_content:
            return None
            
        try:
            API_URL = "https://api.deepseek.com/v1/chat/completions"
            
            prompt = f"""
            Analyze this service provider's website content and extract detailed information.
            Service Provider: {service_name}

            Website Content:
            {website_content}

            Extract and provide the following information in a structured JSON format:
            {{
                "services": {{
                    "main_programs": [],
                    "description": "",
                    "special_services": []
                }},
                "eligibility": {{
                    "requirements": [],
                    "restrictions": [],
                    "documentation_needed": []
                }},
                "location": {{
                    "address": "",
                    "service_area": "",
                    "accessibility": ""
                }},
                "contact": {{
                    "phone": "",
                    "email": "",
                    "website": "",
                    "social_media": []
                }},
                "hours": {{
                    "regular_hours": "",
                    "special_hours": "",
                    "holidays": ""
                }},
                "costs": {{
                    "fee_structure": "",
                    "payment_methods": [],
                    "financial_assistance": ""
                }},
                "application": {{
                    "process": [],
                    "required_documents": [],
                    "waiting_period": ""
                }},
                "languages": {{
                    "service_languages": [],
                    "translation_available": ""
                }}
            }}

            Rules:
            1. Use "Not specified" for missing information
            2. Keep responses factual and based on the provided content
            3. Include all relevant details found in the text
            4. Maintain the exact JSON structure shown above
            """

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}"
            }

            response = self.session.post(
                API_URL,
                headers=headers,
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {"role": "system", "content": "You are an expert at analyzing social service websites and extracting structured information."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 2000
                }
            )

            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']

        except Exception as e:
            print(f"Error in DeepSeek analysis: {str(e)}")
            return None

    def extract_service_details(self, row):
        """Extract service details from 211 page and provider website"""
        try:
            # Get the 211 service page
            self.driver.get(row['service_url'])
            time.sleep(DELAY_BETWEEN_REQUESTS)
            
            # Extract provider website URL
            website_links = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".record-detail-content a[target='_blank']"))
            )
            provider_url = next((link.get_attribute('href') for link in website_links), None)
            
            if not provider_url:
                print(f"No provider URL found for service: {row['service_name']}")
                return None
                
            # Get and analyze website content
            website_content = self.get_website_content(provider_url)
            ai_analysis = self.analyze_with_deepseek(website_content, row['service_name'])
            
            return {
                'provider_url': provider_url,
                'ai_analysis': ai_analysis,
                'scrape_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error processing {row['service_url']}: {str(e)}")
            return None

    def save_progress(self, data, filename):
        """Save current progress to CSV with timestamp"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = os.path.join(BACKUP_DIR, f"{filename}_{timestamp}.csv")
        
        try:
            df = pd.DataFrame(data)
            df.to_csv(backup_file, index=False)
            print(f"Progress saved to {backup_file}")
        except Exception as e:
            print(f"Error saving progress: {str(e)}")

    def process_services(self, input_csv):
        """Main processing function"""
        try:
            # Read input CSV
            df = pd.read_csv(input_csv)
            print(f"Processing {len(df)} services...")
            
            all_results = []
            
            for index, row in df.iterrows():
                print(f"\nProcessing {index + 1}/{len(df)}: {row['service_name']}")
                
                # Extract service details
                details = self.extract_service_details(row)
                
                if details:
                    # Combine original data with new details
                    result = {
                        **row.to_dict(),
                        **details
                    }
                    all_results.append(result)
                    
                    # Save progress every 10 items
                    if (index + 1) % 10 == 0:
                        self.save_progress(all_results, "interim_results")
                
                # Add delay between processing
                time.sleep(DELAY_BETWEEN_REQUESTS)
            
            # Save final results
            final_df = pd.DataFrame(all_results)
            final_df.to_csv('services_with_ai_analysis.csv', index=False)
            print("\nProcessing complete! Results saved to services_with_ai_analysis.csv")
            
        except Exception as e:
            print(f"Error in main processing: {str(e)}")
            # Save whatever results we have
            if all_results:
                self.save_progress(all_results, "emergency_backup")
        
        finally:
            self.driver.quit()

def main():
    scraper = ServiceScraper()
    scraper.process_services('all_services_output.csv')

if __name__ == "__main__":
    main()