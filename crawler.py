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
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("PurePortalCrawler")

class PurePortalCrawler:
    def __init__(self, start_url, data_dir="."):
        self.start_url = start_url
        self.data_dir = data_dir
        self.department_members = []
        self.publications = []
        
        # Create data directory if it doesn't exist
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            
        # Initialize WebDriver
        logger.info("Initializing WebDriver")
        self.driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()))
    
    def __del__(self):
        """Clean up resources when object is destroyed"""
        try:
            if hasattr(self, 'driver'):
                self.driver.quit()
                logger.info("WebDriver closed")
        except Exception as e:
            logger.error(f"Error closing WebDriver: {e}")
    
    def accept_cookies(self):
        """Accept cookies on the website"""
        try:
            time.sleep(5)
            accept_button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//button[@id='onetrust-accept-btn-handler']"))
            )
            accept_button.click()
            logger.info("Cookies accepted!")
        except Exception as e:
            logger.error(f"Error accepting cookies: {e}")
    
    def extract_department_members(self):
        """Extract department members from the people page"""
        members = set()
        try:
            logger.info("Extracting department members")
            people_link = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//i[@class="icon icon-persons"]'))
            )
            people_link.click()
            time.sleep(2)

            while True:
                member_elements = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'h3.title a'))
                )
                for member in member_elements:
                    members.add((member.text.strip(), member.get_attribute('href')))
                logger.info(f"Extracted {len(members)} members")
                try:
                    next_button = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CLASS_NAME, "nextLink"))
                    )
                    if "disabled" in next_button.get_attribute("class"):
                        break
                    self.driver.execute_script("arguments[0].click();", next_button)
                    time.sleep(3)
                except:
                    break
                
        except Exception as e:
            logger.error(f"Error extracting department members: {e}")
        
        self.department_members = list(members)
        return members
    
    def extract_publication_details(self):
        """Extract publication details from the current page"""
        publications = []
        count = 0
        try:
            publication_elements = WebDriverWait(self.driver, 10).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "result-container"))
            )
            for publication in publication_elements:
                try:
                    title_element = publication.find_element(By.CLASS_NAME, "title")
                    author_elements = publication.find_elements(By.CLASS_NAME, 'link.person')
                    year_element = publication.find_element(By.CLASS_NAME, "date")
                    link_element = publication.find_element(By.CLASS_NAME, 'link')
                    journal_element = None
                    abstract_element = None
                    keywords = []
                    
                    # Try to get journal info if available
                    try:
                        journal_element = publication.find_element(By.CLASS_NAME, 'journal')
                    except:
                        pass
                    
                    title = title_element.text if title_element else ""
                    authors = [author.text.strip() for author in author_elements]
                    author_profiles = [author.get_attribute("href") for author in author_elements]
                    year = year_element.text if year_element else ""
                    # Try to extract year as integer
                    try:
                        if year:
                            year = int(year)
                    except ValueError:
                        pass
                        
                    link = link_element.get_attribute("href") if link_element else ""
                    journal = journal_element.text if journal_element else ""
                    abstract = abstract_element.text if abstract_element else ""
                    
                    publications.append({
                        "Title": title,
                        "Authors": authors,
                        "Year": year,
                        "Publication Link": link,
                        "Author Profile Links": author_profiles,
                        "Journal": journal,
                        "Abstract": abstract,
                        "Keywords": keywords
                    })
                    count += 1
                    logger.info(f"{count}. Title: {title}")
                except Exception as e:
                    logger.error(f"Error extracting data from a publication: {e}")
        except Exception as e:
            logger.error(f"Error extracting publications: {e}")
        return publications
    
    def crawl_all_publications(self, max_pages=None):
        """Crawl all publications with optional page limit"""
        all_data = []
        page_count = 0
        
        while True:
            page_count += 1
            logger.info(f"Crawling page {page_count}")
            
            # Check max pages limit
            if max_pages and page_count > max_pages:
                logger.info(f"Reached max pages limit ({max_pages})")
                break
                
            publications = self.extract_publication_details()
            if not publications:
                logger.warning("No publications found on this page")
                break
                
            all_data.extend(publications)
            logger.info(f"Total publications collected: {len(all_data)}")
            
            try:
                next_button = WebDriverWait(self.driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "nextLink"))
                )
                if "disabled" in next_button.get_attribute("class"):
                    logger.info("No more pages available")
                    break
                self.driver.execute_script("arguments[0].click();", next_button)
                time.sleep(3)
            except Exception as e:
                logger.error(f"No more pages or Error navigating to next page: {e}")
                break
                
        self.publications = all_data
        return all_data
    
    def go_to_publications(self):
        """Navigate to the publications tab"""
        try:
            logger.info("Navigating to publications page")
            publications_tab = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, '//a[contains(@href, "fbl-school-of-economics-finance-and-accounting/publications")]'))
            )
            self.driver.execute_script("arguments[0].click();", publications_tab)
            time.sleep(3)
            logger.info("Successfully navigated to publications page")
        except Exception as e:
            logger.error(f"Error navigating to publications: {e}")
    
    def save_department_members(self, filename=None):
        """Save department members to pickle file"""
        if not self.department_members:
            logger.warning("No department members to save")
            return
            
        if filename is None:
            filename = os.path.join(self.data_dir, "department_members.pkl")
            
        try:
            with open(filename, "wb") as file:
                pickle.dump(self.department_members, file)
            logger.info(f"Department members saved to {filename}")
        except Exception as e:
            logger.error(f"Error saving department members: {e}")
    
    def save_department_members_to_txt(self, filename=None):
        """Save department members to text file"""
        if not self.department_members:
            logger.warning("No department members to save")
            return
            
        if filename is None:
            filename = os.path.join(self.data_dir, "department_members.txt")
            
        try:
            with open(filename, "w", encoding="utf-8") as file:
                for name, link in self.department_members:
                    file.write(f"{name}: {link}\n")
            logger.info(f"Department members saved to text file: {filename}")
        except Exception as e:
            logger.error(f"Error saving department members to text file: {e}")
    
    def save_publications_to_csv(self, filename=None):
        """Save publications to CSV file"""
        if not self.publications:
            logger.warning("No publications to save to CSV")
            return
            
        if filename is None:
            filename = os.path.join(self.data_dir, "publications.csv")
            
        try:
            keys = list(self.publications[0].keys())
            with open(filename, "w", newline="", encoding="utf-8") as file:
                writer = csv.DictWriter(file, fieldnames=keys)
                writer.writeheader()
                writer.writerows(self.publications)
            logger.info(f"Publications saved to CSV: {filename}")
        except Exception as e:
            logger.error(f"Error saving publications to CSV: {e}")
    
    def save_publications_to_pkl(self, filename=None):
        """Save publications to pickle file"""
        if not self.publications:
            logger.warning("No publications to save to pickle")
            return
            
        if filename is None:
            filename = os.path.join(self.data_dir, "publications.pkl")
            
        try:
            with open(filename, "wb") as file:
                pickle.dump(self.publications, file)
            logger.info(f"Publications saved to pickle: {filename}")
        except Exception as e:
            logger.error(f"Error saving publications to pickle: {e}")
    
    def crawl(self, max_pages=None):
        """Run the crawler to extract all data"""
        try:
            logger.info(f"Starting crawler with URL: {self.start_url}")
            self.driver.get(self.start_url)
            
            # Accept cookies
            self.accept_cookies()
            
            # Extract department members
            self.extract_department_members()
            self.save_department_members()
            self.save_department_members_to_txt()
            
            # Navigate to publications and extract them
            self.go_to_publications()
            self.crawl_all_publications(max_pages=max_pages)
            
            # Save the publications
            self.save_publications_to_csv()
            self.save_publications_to_pkl()
            
            logger.info(f"Crawler completed. Extracted {len(self.department_members)} members and {len(self.publications)} publications.")
            return True
        except Exception as e:
            logger.error(f"Error during crawling: {e}")
            return False
        finally:
            # Close the browser
            self.driver.quit()
            logger.info("WebDriver closed")

# Example usage
if __name__ == "__main__":
    start_url = ""
    crawler = PurePortalCrawler(start_url)
    crawler.crawl(max_pages=2)  # Limit to 2 pages for testing