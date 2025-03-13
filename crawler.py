# import requests
# from bs4 import BeautifulSoup
# import re
# import time
# import logging
# import pickle
# import os
# import urllib.robotparser
# from urllib.parse import urljoin, urlparse
# from datetime import datetime
# import schedule

# # Configure logging
# logging.basicConfig(
#     level=logging.INFO,
#     format='%(asctime)s - %(levelname)s - %(message)s',
#     handlers=[
#         logging.FileHandler("crawler.log"),
#         logging.StreamHandler()
#     ]
# )
# logger = logging.getLogger("PurePortalCrawler")

# class PurePortalCrawler:
#     def __init__(self, start_url, data_dir="crawled_data"):
#         self.start_url = start_url
#         self.base_url = "{uri.scheme}://{uri.netloc}".format(uri=urlparse(start_url))
#         self.visited_urls = set()
#         self.publications = []
#         self.data_dir = data_dir
#         self.rp = urllib.robotparser.RobotFileParser()
#         self.rp.set_url(f"{self.base_url}/robots.txt")
#         self.rp.read()
        
#         # Create data directory if it doesn't exist
#         if not os.path.exists(data_dir):
#             os.makedirs(data_dir)
        
#         # Load previous data if exists
#         self.load_previous_data()
    
#     def load_previous_data(self):
#         """Load previously crawled data if it exists"""
#         try:
#             if os.path.exists(f"{self.data_dir}/visited_urls.pkl"):
#                 with open(f"{self.data_dir}/visited_urls.pkl", 'rb') as f:
#                     self.visited_urls = pickle.load(f)
#                 logger.info(f"Loaded {len(self.visited_urls)} previously visited URLs")
            
#             if os.path.exists(f"{self.data_dir}/publications.pkl"):
#                 with open(f"{self.data_dir}/publications.pkl", 'rb') as f:
#                     self.publications = pickle.load(f)
#                 logger.info(f"Loaded {len(self.publications)} previously crawled publications")
#         except Exception as e:
#             logger.error(f"Error loading previous data: {e}")
    
#     def save_data(self):
#         """Save crawled data to disk"""
#         try:
#             with open(f"{self.data_dir}/visited_urls.pkl", 'wb') as f:
#                 pickle.dump(self.visited_urls, f)
            
#             with open(f"{self.data_dir}/publications.pkl", 'wb') as f:
#                 pickle.dump(self.publications, f)
            
#             # Also save as JSON for easier inspection
#             import json
#             with open(f"{self.data_dir}/publications.json", 'w') as f:
#                 json.dump(self.publications, f, indent=2)
                
#             logger.info(f"Saved {len(self.publications)} publications to disk")
#         except Exception as e:
#             logger.error(f"Error saving data: {e}")
    
#     def is_allowed_url(self, url):
#         """Check if crawling this URL is allowed by robots.txt"""
#         return self.rp.can_fetch("*", url)
    
#     def is_publication_url(self, url):
#         """Check if URL is a publication page"""
#         return "/publication/" in url
    
#     def is_profile_url(self, url):
#         """Check if URL is a researcher profile page"""
#         return "/persons/" in url
    
#     def is_department_url(self, url):
#         """Check if URL is related to the Economics, Finance and Accounting department"""
#         return "/organisations/fbl-school-of-economics-finance-and-accounting" in url or \
#                "/en/organisations/fbl-school-of-economics-finance-and-accounting" in url
    
#     def get_page(self, url):
#         """Get page content with polite delay"""
#         if url in self.visited_urls:
#             return None
        
#         if not self.is_allowed_url(url):
#             logger.info(f"Skipping URL not allowed by robots.txt: {url}")
#             self.visited_urls.add(url)
#             return None
        
#         try:
#             logger.info(f"Fetching: {url}")
#             headers = {
#                 'User-Agent': 'PurePortalCrawler/1.0 (Academic Research Project; Contact: your.email@example.com)',
#             }
#             response = requests.get(url, headers=headers, timeout=10)
#             self.visited_urls.add(url)
            
#             if response.status_code == 200:
#                 # Polite crawling - delay between requests
#                 time.sleep(2)
#                 return response.text
#             else:
#                 logger.warning(f"Failed to fetch {url}: HTTP {response.status_code}")
#                 return None
#         except Exception as e:
#             logger.error(f"Error fetching {url}: {e}")
#             return None
    
#     def extract_publication_info(self, url, html_content):
#         """Extract publication information from a publication page"""
#         soup = BeautifulSoup(html_content, 'html.parser')
        
#         # Initialize data structure
#         publication = {
#             'url': url,
#             'title': None,
#             'authors': [],
#             'year': None,
#             'abstract': None,
#             'keywords': [],
#             'author_profiles': [],
#             'department_affiliation': [],
#             'crawled_date': datetime.now().isoformat()
#         }
        
#         try:
#             # Extract title
#             title_elem = soup.find('h1', {'class': 'title'})
#             if title_elem:
#                 publication['title'] = title_elem.text.strip()
            
#             # Extract authors and their profiles
#             author_section = soup.find('div', {'class': 'relations persons'})
#             if author_section:
#                 for author_elem in author_section.find_all('a', href=True):
#                     author_name = author_elem.text.strip()
#                     author_profile = urljoin(self.base_url, author_elem['href'])
#                     if author_name and author_profile:
#                         publication['authors'].append(author_name)
#                         publication['author_profiles'].append(author_profile)
            
#             # Extract publication year
#             year_pattern = re.compile(r'\b(19|20)\d{2}\b')
#             date_spans = soup.find_all('span', {'class': 'date'})
#             for span in date_spans:
#                 year_match = year_pattern.search(span.text)
#                 if year_match:
#                     publication['year'] = int(year_match.group())
#                     break
            
#             # Extract abstract
#             abstract_div = soup.find('div', {'class': 'textblock'})
#             if abstract_div:
#                 publication['abstract'] = abstract_div.text.strip()
            
#             # Extract keywords
#             keywords_section = soup.find('div', {'class': 'keywords'})
#             if keywords_section:
#                 keywords = [kw.text.strip() for kw in keywords_section.find_all('span', {'class': 'keyword'})]
#                 publication['keywords'] = keywords
            
#             # Extract department affiliation
#             dept_section = soup.find('div', {'class': 'organisations'})
#             if dept_section:
#                 for org in dept_section.find_all('a', href=True):
#                     if 'economics-finance-and-accounting' in org['href'].lower():
#                         publication['department_affiliation'].append(org.text.strip())
            
#         except Exception as e:
#             logger.error(f"Error extracting publication data from {url}: {e}")
        
#         return publication
    
#     def extract_links(self, url, html_content):
#         """Extract relevant links from a page"""
#         soup = BeautifulSoup(html_content, 'html.parser')
#         links = []
        
#         for a_tag in soup.find_all('a', href=True):
#             link = a_tag['href']
#             # Convert relative URLs to absolute
#             if not link.startswith(('http://', 'https://')):
#                 link = urljoin(url, link)
            
#             # Only add links from the same domain
#             if urlparse(link).netloc == urlparse(self.base_url).netloc:
#                 links.append(link)
        
#         return links
    
#     def crawl(self, max_pages=None):
#         """Main crawling method using BFS strategy"""
#         queue = [self.start_url]
#         page_count = 0
#         publications_found = 0
        
#         logger.info(f"Starting crawl from {self.start_url}")
        
#         while queue and (max_pages is None or page_count < max_pages):
#             current_url = queue.pop(0)
            
#             if current_url in self.visited_urls:
#                 continue
            
#             html_content = self.get_page(current_url)
#             if not html_content:
#                 continue
            
#             page_count += 1
#             logger.info(f"Processed {page_count} pages, found {publications_found} publications")
            
#             # If this is a publication page, extract publication info
#             if self.is_publication_url(current_url):
#                 pub_info = self.extract_publication_info(current_url, html_content)
#                 # Check if at least one author is from the department
#                 if pub_info['department_affiliation'] or any('economics-finance-and-accounting' in profile for profile in pub_info['author_profiles']):
#                     self.publications.append(pub_info)
#                     publications_found += 1
#                     logger.info(f"Found publication: {pub_info['title']}")
            
#             # Extract links for further crawling
#             links = self.extract_links(current_url, html_content)
#             for link in links:
#                 # Filter links to focus on relevant pages
#                 if (self.is_publication_url(link) or 
#                     self.is_profile_url(link) or 
#                     self.is_department_url(link)) and link not in self.visited_urls:
#                     queue.append(link)
            
#             # Save progress periodically
#             if page_count % 10 == 0:
#                 self.save_data()
        
#         # Save final results
#         self.save_data()
#         logger.info(f"Crawl completed: Processed {page_count} pages, found {publications_found} publications")

# def start_crawl():
#     """Function to start the crawling process - can be scheduled"""
#     logger.info("Starting scheduled crawl...")
#     start_url = "https://pureportal.coventry.ac.uk/en/organisations/fbl-school-of-economics-finance-and-accounting"
#     crawler = PurePortalCrawler(start_url)
#     crawler.crawl(max_pages=200)  # Limit for testing, remove or increase for production

# if __name__ == "__main__":
#     # Run immediately
#     start_crawl()
    
#     # Schedule weekly runs
#     schedule.every().monday.at("01:00").do(start_crawl)
    
#     # Keep the script running for scheduled tasks
#     logger.info("Crawler initialized and scheduled for weekly runs...")
#     while True:
#         schedule.run_pending()
#         time.sleep(60)


from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import pickle
import os

# Initialize WebDriver
driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))

url = "https://pureportal.coventry.ac.uk/en/organisations/fbl-school-of-economics-finance-and-accounting"
driver.get(url)

def accept_cookies():
    try:
        time.sleep(5)
        accept_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-accept-btn-handler']"))
        )
        accept_button.click()
        print("Cookies accepted!")
    except Exception as e:
        print(f"Error accepting cookies: {e}")

accept_cookies()

def extract_department_members():
    members = set()
    try:
        people_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//i[@class="icon icon-persons"]'))
        )
        people_link.click()
        time.sleep(2)

        while True:
        
            member_elements = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h3.title a'))
            )
            for member in member_elements:
                members.add((member.text.strip(), member.get_attribute('href')))
            print(f"Extracted {len(members)} members")
            try:
                next_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "nextLink"))
                )
                if "disabled" in next_button.get_attribute("class"):
                    break
                driver.execute_script("arguments[0].click();", next_button)
                time.sleep(3)
            except:
                break
            
    except Exception as e:
        print(f"Error extracting department members: {e}")
    return members

def extract_publication_details():
    publications = []
    count = 0
    try:
        publication_elements = WebDriverWait(driver, 10).until(
            EC.presence_of_all_elements_located((By.CLASS_NAME, "result-container"))
        )
        for publication in publication_elements:
            try:
                title_element = publication.find_element(By.CLASS_NAME, "title")
                author_elements = publication.find_elements(By.CLASS_NAME, 'link.person')
                year_element = publication.find_element(By.CLASS_NAME, "date")
                link_element = publication.find_element(By.CLASS_NAME, 'link')
                
                title = title_element.text if title_element else ""
                authors = [author.text.strip() for author in author_elements]
                author_profiles = [author.get_attribute("href") for author in author_elements]
                year = year_element.text if year_element else ""
                link = link_element.get_attribute("href") if link_element else ""
                
                publications.append({
                    "Title": title,
                    "Authors": authors,
                    "Year": year,
                    "Publication Link": link,
                    "Author Profile Links": author_profiles
                })
                count += 1
                print(f"{count}. Title: {title}")
            except Exception as e:
                print(f"Error extracting data from a publication: {e}")
    except Exception as e:
        print(f"Error extracting publications: {e}")
    return publications

def crawl_all_publications():
    all_data = []
    while True:
        publications = extract_publication_details()
        if not publications:
            break
        all_data.extend(publications)
        try:
            next_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.CLASS_NAME, "nextLink"))
            )
            if "disabled" in next_button.get_attribute("class"):
                break
            driver.execute_script("arguments[0].click();", next_button)
            time.sleep(3)
        except Exception as e:
            print(f"No more pages or Error navigating to next page: {e}")
            break
    return all_data

def save_department_members(members, filename="department_members.pkl"):
    if not members:
        return
    with open(filename, "wb") as file:
        pickle.dump(members, file)
    print("Department members saved!")

def save_department_members_to_txt(members, filename="department_members.txt"):
    if not members:
        return
    with open(filename, "w", encoding="utf-8") as file:
            for name, link in members:
                file.write(f"{name}: {link}\n")
    print("Department members saved to text file!")

def save_to_csv(data, filename="all_publications.csv"):
    if not data:
        return
    keys = data[0].keys()
    with open(filename, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=keys)
        writer.writeheader()
        writer.writerows(data)
    print("Publication data saved!")

def save_publications_to_pkl(data, filename="publications.pkl"):
    if not data:
        return
    with open(filename, "wb") as file:
        pickle.dump(data, file)
    print("Publications saved to .pkl file!")

department_members = extract_department_members()
save_department_members(department_members)
save_department_members_to_txt(department_members)

def go_to_publications():
    try:
        publications_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, '//a[contains(@href, "fbl-school-of-economics-finance-and-accounting/publications")]'))
        )
        driver.execute_script("arguments[0].click();", publications_tab)
        time.sleep(3)
    except Exception as e:
        print(f"Error navigating to publications: {e}")

go_to_publications()

all_publications = crawl_all_publications()
save_to_csv(all_publications)
save_publications_to_pkl(all_publications)
driver.quit()
