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
import os
from urllib.parse import urljoin, urlparse
import re

def create_prompt():
    """Create the prompt template for LLM analysis"""
    prompt = """Please analyze this service provider's information and provide a structured response in the following format:

{
    "services": [
        {
            "name": "Service Name",
            "description": "Brief description",
            "eligibility": "Who can access",
            "location": "Service areas",
            "contact": {
                "phone": "Main contact number",
                "email": "Contact email",
                "emergency": "Emergency contact if available"
            },
            "hours": "Operating hours if available",
            "costs": "Cost information if available",
            "application": "How to apply/access",
            "languages": ["Available languages"]
        }
    ]
}

Please ensure:
1. All information is factual and directly from the provided data
2. Use "Not specified" for any missing information
3. Include all core services and initiatives
4. Maintain the exact structure above
5. Focus on practical, actionable information

Here is the service provider's information:
"""
    return prompt

def save_for_llm(service_data, output_dir='service_data'):
    """Save the prompt and service data for LLM analysis"""
    # Create the prompt
    prompt = create_prompt()
    
    # Combine prompt and data
    full_prompt = prompt + json.dumps(service_data, indent=2)
    
    # Save to a new file
    with open(f'{output_dir}/llm_prompt.txt', 'w', encoding='utf-8') as f:
        f.write(full_prompt)
    
    print(f"LLM prompt saved to {output_dir}/llm_prompt.txt")

class ServiceContentExtractor:
    def __init__(self):
        self.setup_driver()
        self.visited_urls = set()
        self.service_urls = {}  # Dictionary to store service name -> URL mapping
        self.connected_initiatives = {}  # Dictionary to store initiative details
        
    def setup_driver(self):
        """Initialize the Chrome WebDriver"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--enable-javascript")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        self.driver.set_page_load_timeout(30)

    def is_valid_url(self, url, base_domain):
        """Check if URL is valid and belongs to the organization"""
        if not url:
            return False
        try:
            # List of known related domains
            org_domains = [
                base_domain,
                "protectchildren.ca",
                "cybertip.ca",
                "needhelpnow.ca",
                "missingkids.ca"
                # Add more related domains as needed
            ]
            url_domain = urlparse(url).netloc
            return any(domain in url_domain for domain in org_domains)
        except:
            return False

    def find_initiative_links(self):
        """Find links to different initiatives/programs"""
        try:
            # Look for common program/initiative link patterns
            selectors = [
                "a[href*='programs']",
                "a[href*='initiatives']",
                "a[href*='services']",
                ".programs-menu a",
                "#programs-dropdown a",
                "nav a",  # General navigation links
                ".menu-item a"  # Common menu item class
            ]
            
            links = []
            for selector in selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for elem in elements:
                    try:
                        href = elem.get_attribute('href')
                        text = elem.text.strip()
                        if href and text:
                            links.append((text, href))
                    except:
                        continue
            return links
        except Exception as e:
            print(f"Error finding initiative links: {e}")
            return []

    def clean_html(self, text):
        """Remove HTML tags and clean up text"""
        if not text:
            return ""
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Clean up whitespace
        text = ' '.join(text.split())
        return text.strip()

    def clean_service_text(self, text):
        """Clean and validate service text"""
        text = text.strip()
        # Expanded list of terms to skip
        skip_terms = [
            # Navigation/Menu
            'contact us', 'about', 'privacy', 'terms', 'accessibility', 
            'connect with us', 'facebook', 'twitter', 'youtube', 'instagram',
            'donate', 'français', 'english', 'resources', 'press', 'media',
            'partners', 'how can we help', 'help us find', 'en bref',
            'conditions', 'politique', 'suivez-nous', 'zone médias',
            
            # Generic Actions
            'download pdf', 'learn more', 'read more', 'click here',
            'sign up', 'newsletter', 'make a', 'order', 'careers',
            
            # Common Headers
            'resources', 'initiatives', 'programs', 'services',
            'get involved', 'about us', 'contact', 'history',
            'leadership', 'policies', 'faq', 'donation'
        ]
        
        # Skip if any of these conditions are met
        if (len(text) < 5 or  # too short
            any(term in text.lower() for term in skip_terms) or  # contains skip terms
            '\n' in text or  # contains newlines
            text.isupper() or  # all uppercase (likely a header)
            len(text.split()) > 10 or  # too long to be a service name
            text.startswith('http') or  # URLs
            not any(c.isalpha() for c in text)):  # no letters
            return None
        
        return text

    def extract_initiative_details(self, url):
        """Extract focused details about a specific initiative"""
        try:
            self.driver.get(url)
            time.sleep(2)
            
            details = {
                'url': url,
                'title': '',
                'description': '',
                'key_services': [],
                'contact': {
                    'phone': '',
                    'email': '',
                    'emergency_contact': ''
                },
                'target_audience': [],
                'service_type': ''
            }
            
            # Get title from h1 or similar
            title_selectors = ['h1', '.title', '.header-title', '#main-title']
            for selector in title_selectors:
                try:
                    title = self.driver.find_element(By.CSS_SELECTOR, selector).text.strip()
                    if title:
                        details['title'] = title
                        break
                except:
                    continue
            
            # Better service extraction
            def clean_service_text(text):
                """Clean and validate service text"""
                text = text.strip()
                # Expanded list of terms to skip
                skip_terms = [
                    # Navigation/Menu
                    'contact us', 'about', 'privacy', 'terms', 'accessibility', 
                    'connect with us', 'facebook', 'twitter', 'youtube', 'instagram',
                    'donate', 'français', 'english', 'resources', 'press', 'media',
                    'partners', 'how can we help', 'help us find', 'en bref',
                    'conditions', 'politique', 'suivez-nous', 'zone médias',
                    
                    # Generic Actions
                    'download pdf', 'learn more', 'read more', 'click here',
                    'sign up', 'newsletter', 'make a', 'order', 'careers',
                    
                    # Common Headers
                    'resources', 'initiatives', 'programs', 'services',
                    'get involved', 'about us', 'contact', 'history',
                    'leadership', 'policies', 'faq', 'donation'
                ]
                
                # Skip if any of these conditions are met
                if (len(text) < 5 or  # too short
                    any(term in text.lower() for term in skip_terms) or  # contains skip terms
                    '\n' in text or  # contains newlines
                    text.isupper() or  # all uppercase (likely a header)
                    len(text.split()) > 10 or  # too long to be a service name
                    text.startswith('http') or  # URLs
                    not any(c.isalpha() for c in text)):  # no letters
                    return None
                
                return text

            # Extract key services from bullet points and lists
            service_selectors = [
                '.services li', '.programs li', '.initiatives li',
                'ul:not(.nav) li', '.content ul:not(.menu) li', 
                '.main-content ul:not(.navigation) li'
            ]
            seen_services = set()  # To prevent duplicates
            for selector in service_selectors:
                services = self.driver.find_elements(By.CSS_SELECTOR, selector)
                for service in services:
                    text = clean_service_text(service.text)
                    if text and text not in seen_services:
                        seen_services.add(text)
                        details['key_services'].append(text)
            
            # Extract target audience
            audience_keywords = ['children', 'families', 'parents', 'youth', 'survivors']
            page_text = self.driver.page_source.lower()
            details['target_audience'] = [kw for kw in audience_keywords if kw in page_text]
            
            # Determine service type
            service_types = {
                'emergency': ['crisis', 'emergency', '24/7', 'urgent'],
                'support': ['support', 'assistance', 'help'],
                'education': ['education', 'prevention', 'training'],
                'reporting': ['report', 'tipline', 'hotline']
            }
            for stype, keywords in service_types.items():
                if any(kw in page_text for kw in keywords):
                    details['service_type'] = stype
                    break
            
            # Get concise description (limit to first 2-3 paragraphs)
            desc_selectors = ['.description', '.content p', '#main-content p', 'article p']
            for selector in desc_selectors:
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)[:3]  # Limit to first 3 paragraphs
                description = ' '.join([e.text.strip() for e in elements if e.text.strip()])
                if description:
                    details['description'] = description
                    break
            
            # Better email extraction
            email_pattern = r'\b[A-Za-z0-9._%+-]+@(?:protectchildren|missingkids|cybertip|needhelpnow)\.ca\b'
            page_text = self.driver.page_source
            emails = re.findall(email_pattern, page_text)
            if emails:
                # Filter out hashed/obfuscated emails
                valid_emails = [e for e in emails if not re.match(r'^[a-f0-9]{32}@', e)]
                if valid_emails:
                    details['contact']['email'] = valid_emails[0]

            # Better phone extraction
            phone_patterns = [
                r'1-(?:\d{3}[-.)]\s*)+\d{4}',  # 1-800 style
                r'(?:\(\d{3}\)|\d{3})[-.\s]\d{3}[-.\s]\d{4}',  # (xxx) xxx-xxxx
                r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b'  # xxx-xxx-xxxx
            ]
            for pattern in phone_patterns:
                phones = re.findall(pattern, self.driver.page_source)
                if phones:
                    details['contact']['phone'] = phones[0]
                    break

            # Better emergency contact detection
            emergency_contexts = [
                (r'(?:24/7|emergency|crisis).*?(?:\d{3}[-.\s]\d{3}[-.\s]\d{4}|\(\d{3}\)[.\s]\d{3}[-.\s]\d{4}|1-\d{3}[-.\s]\d{3}[-.\s]\d{4})',
                 r'toll[- ]free.*?(?:\d{3}[-.\s]\d{3}[-.\s]\d{4}|\(\d{3}\)[.\s]\d{3}[-.\s]\d{4}|1-\d{3}[-.\s]\d{3}[-.\s]\d{4})')
            ]
            for patterns in emergency_contexts:
                for pattern in patterns:
                    matches = re.findall(pattern, self.driver.page_source, re.I | re.S)
                    if matches:
                        details['contact']['emergency_contact'] = matches[0].strip()
                        break
                if details['contact']['emergency_contact']:
                    break

            # Clean emergency contact
            if details['contact']['emergency_contact']:
                details['contact']['emergency_contact'] = self.clean_html(details['contact']['emergency_contact'])
            
            # Clean description
            if details['description']:
                details['description'] = self.clean_html(details['description'])
            
            # Clean and deduplicate key services
            seen_services = set()
            cleaned_services = []
            for service in details['key_services']:
                cleaned = self.clean_service_text(service)
                if cleaned and cleaned not in seen_services:
                    seen_services.add(cleaned)
                    cleaned_services.append(cleaned)
            
            details['key_services'] = cleaned_services
            
            return details
            
        except Exception as e:
            print(f"Error extracting initiative details from {url}: {e}")
            return None

    def process_single_service(self, input_csv):
        """Process service with focused information gathering"""
        try:
            # Read the first row from CSV
            df = pd.read_csv(input_csv, nrows=1)
            if df.empty:
                print("No services found in CSV")
                return
            
            row = df.iloc[0]
            print(f"\nProcessing main service: {row['service_name']}")
            
            # Get the main service page
            self.driver.get(row['service_url'])
            time.sleep(2)
            
            # Get the provider website
            website_links = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, ".record-detail-content a[target='_blank']"))
            )
            provider_url = next((link.get_attribute('href') for link in website_links), None)
            
            if not provider_url:
                print("No provider URL found")
                return
                
            print(f"\nFound provider URL: {provider_url}")
            base_domain = urlparse(provider_url).netloc
            
            # Visit provider website
            self.driver.get(provider_url)
            time.sleep(2)
            
            # Create directory for output
            os.makedirs('service_data', exist_ok=True)
            
            # Add service categorization
            def categorize_service(name, description):
                """Categorize service based on name and description"""
                categories = set()  # Use set to avoid duplicates
                category_keywords = {
                    'Missing Children Services': [
                        'missing', 'amber alert', 'search', 'locate', 'find', 'lost child',
                        'missingkids', 'enfants disparus'
                    ],
                    'Child Protection': [
                        'protect', 'safety', 'prevention', 'safeguard', 'secure', 
                        'protection de l\'enfance', 'cybertip'
                    ],
                    'Prevention and Education': [
                        'education', 'training', 'prevention', 'workshop', 'awareness',
                        'learn', 'teach', 'program', 'resource'
                    ],
                    'Family Support Services': [
                        'family', 'support', 'assistance', 'help', 'guidance',
                        'counseling', 'aide', 'soutien'
                    ],
                    'Emergency Response': [
                        'emergency', 'crisis', '24/7', 'hotline', 'urgent', 'immediate',
                        'urgence', 'crisis'
                    ],
                    'Crisis Intervention': [
                        'crisis', 'intervention', 'urgent', 'emergency', 'immediate',
                        'support', 'help'
                    ],
                    'Child Safety Resources': [
                        'safety', 'resources', 'materials', 'guide', 'toolkit',
                        'information', 'tips'
                    ],
                    'Public Awareness': [
                        'awareness', 'public', 'community', 'campaign', 'outreach',
                        'education', 'inform'
                    ],
                    'Law Enforcement Collaboration': [
                        'police', 'law enforcement', 'investigation', 'report',
                        'legal', 'justice'
                    ]
                }
                
                # Combine name and description, convert to lowercase for matching
                combined_text = (name + ' ' + description).lower()
                
                # Check each category's keywords
                for category, keywords in category_keywords.items():
                    if any(keyword.lower() in combined_text for keyword in keywords):
                        categories.add(category)
                
                # Always include these categories for this specific service
                default_categories = {
                    'Child Protection',
                    'Missing Children Services'
                }
                categories.update(default_categories)
                
                return list(categories)

            # Update service data creation with better description extraction
            description = ""
            description_selectors = [
                '.description', 
                '.record-detail-content',  # Common in 211 listings
                '.service-description',
                'main p',  # General paragraphs in main content
                '.content p',  # Common content paragraphs
                '#main-content p'  # Another common content area
            ]
            
            for selector in description_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        description = ' '.join(elem.text.strip() for elem in elements[:3])  # Get first 3 paragraphs
                        if description:
                            break
                except:
                    continue
            
            # If still no description, try getting it from meta tags
            if not description:
                try:
                    meta_desc = self.driver.find_element(By.CSS_SELECTOR, 'meta[name="description"]')
                    description = meta_desc.get_attribute('content')
                except:
                    description = "Service description not available"

            service_data = {
                'main_service': {
                    'name': row['service_name'],
                    'url': row['service_url'],
                    'provider_url': provider_url,
                    'primary_focus': 'Child Protection and Missing Children Services',
                    'service_categories': categorize_service(row['service_name'], description)
                },
                'core_initiatives': {},
                'key_urls': set(),
                'service_areas': {'Canada', 'Quebec'}
            }
            
            # Find and process main initiatives
            initiative_links = self.find_initiative_links()
            
            for initiative_name, initiative_url in initiative_links:
                if (self.is_valid_url(initiative_url, base_domain) and 
                    initiative_url not in self.visited_urls and
                    not any(x in initiative_url.lower() for x in ['privacy', 'terms', 'accessibility'])):
                    
                    print(f"\nProcessing initiative: {initiative_name}")
                    self.visited_urls.add(initiative_url)
                    
                    details = self.extract_initiative_details(initiative_url)
                    if details:
                        service_data['core_initiatives'][initiative_name] = details
                        service_data['key_urls'].add(initiative_url)
                        
                        # Look for additional core service links
                        additional_links = self.find_initiative_links()
                        for add_name, add_url in additional_links:
                            if (self.is_valid_url(add_url, base_domain) and 
                                add_url not in self.visited_urls and
                                'program' in add_url.lower() or 'service' in add_url.lower()):
                                service_data['key_urls'].add(add_url)
            
            # Convert sets to lists for JSON serialization
            service_data['key_urls'] = list(service_data['key_urls'])
            service_data['service_areas'] = list(service_data['service_areas'])
            
            # Save the focused service data
            with open('service_data/service_analysis.json', 'w', encoding='utf-8') as f:
                json.dump(service_data, f, indent=2, ensure_ascii=False)
            
            print("\nProcessing complete! Results saved to service_data/service_analysis.json")
            
            # Save the LLM prompt
            save_for_llm(service_data)
            
        except Exception as e:
            print(f"Error in main processing: {e}")
            import traceback
            traceback.print_exc()  # Print full traceback for better debugging
        
        finally:
            self.driver.quit()

def main():
    extractor = ServiceContentExtractor()
    extractor.process_single_service('all_services_output.csv')

if __name__ == "__main__":
    main()