import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import json
import os
from urllib.parse import urljoin, urlparse
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Enhanced bot detection avoidance measures
class StealthScraper:
    def __init__(self):
        self.session = requests.Session()
        self.progress_file = 'scraping_progress.json'
        self.load_progress()
        
    def get_random_headers(self):
        """Return randomized headers to avoid bot detection"""
        user_agents = [
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0',
            'Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0'
        ]
        
        languages = [
            'en-US,en;q=0.9',
            'en-GB,en;q=0.9',
            'en-US,en;q=0.8,es;q=0.7',
            'en-US,en;q=0.9,fr;q=0.8',
            'en-US,en;q=0.9,de;q=0.8'
        ]
        
        return {
            'User-Agent': random.choice(user_agents),
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': random.choice(languages),
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin' if random.random() > 0.5 else 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Linux"'
        }
    
    def smart_delay(self, min_delay=3, max_delay=8):
        """Implement human-like delays with randomization"""
        delay = random.uniform(min_delay, max_delay)
        logger.info(f"Waiting {delay:.2f} seconds...")
        time.sleep(delay)
    
    def long_delay(self, min_delay=10, max_delay=20):
        """Longer delays between teams"""
        delay = random.uniform(min_delay, max_delay)
        logger.info(f"Long delay between teams: {delay:.2f} seconds...")
        time.sleep(delay)
    
    def load_progress(self):
        """Load existing progress from file"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    self.progress = json.load(f)
                logger.info(f"Loaded progress: {len(self.progress.get('processed_teams', []))} teams processed")
            except:
                self.progress = {'processed_teams': [], 'all_player_data': []}
        else:
            self.progress = {'processed_teams': [], 'all_player_data': []}
    
    def save_progress(self):
        """Save current progress to file"""
        with open(self.progress_file, 'w') as f:
            json.dump(self.progress, f, indent=2)
        logger.info("Progress saved")
    
    def make_request(self, url, retries=3):
        """Make a request with retry logic and stealth measures"""
        for attempt in range(retries):
            try:
                # Update headers for each request
                self.session.headers.update(self.get_random_headers())
                
                # Add referer for non-first requests
                if hasattr(self, 'last_url') and self.last_url:
                    self.session.headers['Referer'] = self.last_url
                
                logger.info(f"Making request to: {url}")
                response = self.session.get(url, timeout=15)
                
                if response.status_code == 403:
                    logger.warning(f"403 Forbidden. Attempt {attempt + 1}/{retries}")
                    if attempt < retries - 1:
                        # Exponential backoff for 403 errors
                        delay = (2 ** attempt) * 10 + random.uniform(5, 15)
                        logger.info(f"Backing off for {delay:.2f} seconds...")
                        time.sleep(delay)
                        continue
                
                response.raise_for_status()
                self.last_url = url
                return response
                
            except requests.RequestException as e:
                logger.error(f"Request failed (attempt {attempt + 1}/{retries}): {e}")
                if attempt < retries - 1:
                    delay = (2 ** attempt) * 5 + random.uniform(3, 8)
                    logger.info(f"Retrying in {delay:.2f} seconds...")
                    time.sleep(delay)
                else:
                    raise
        
        return None
    
    def warm_up_session(self):
        """Establish session by visiting main pages first"""
        base_urls = [
            "https://play.fiba3x3.com",
            "https://play.fiba3x3.com/events",
        ]
        
        for url in base_urls:
            try:
                logger.info(f"Warming up session with: {url}")
                response = self.make_request(url)
                if response:
                    logger.info(f"Successfully warmed up with {url}")
                self.smart_delay(2, 5)
            except Exception as e:
                logger.warning(f"Failed to warm up with {url}: {e}")
    
    def get_main_page(self, url):
        """Get team URLs from main page with enhanced stealth"""
        # Warm up the session first
        self.warm_up_session()
        
        response = self.make_request(url)
        if not response:
            return []
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Find all anchor tags with the specific classes that contain team URLs
        team_links = soup.find_all("a", class_="dark-50 link fw6")
        
        team_urls = []
        base_url = "https://play.fiba3x3.com"
        
        for link in team_links:
            href = link.get('href')
            if href and '/teams/' in href:
                full_url = urljoin(base_url, href)
                if full_url not in self.progress['processed_teams']:
                    team_urls.append(full_url)
                    logger.info(f"Found new team URL: {full_url}")
                else:
                    logger.info(f"Skipping already processed team: {full_url}")
        
        logger.info(f"Total new teams to process: {len(team_urls)}")
        return team_urls
    
    def visit_team_url_get_player_urls(self, url):
        """Visit team page and get player URLs with enhanced stealth"""
        # Skip if already processed
        if url in self.progress['processed_teams']:
            logger.info(f"Team already processed: {url}")
            return "Already Processed", []
        
        self.smart_delay(5, 10)  # Longer delay before team requests
        
        response = self.make_request(url)
        if not response:
            return "Failed to fetch", []
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Get team name from the correct element
        team_name = "Unknown Team"
        
        # First try to find the CategoryTeam-Title element
        title_element = soup.find("h3", class_="CategoryTeam-Title")
        if title_element:
            # Extract just the team name, excluding the nationality part
            team_name_text = title_element.get_text(strip=True)
            
            # Remove the nationality part (e.g., "BIH" from "Texas autoBIH")
            nationality_element = title_element.find("small", class_="CategoryTeam-Nationality")
            if nationality_element:
                nationality_text = nationality_element.get_text(strip=True)
                # Remove the nationality from the full text
                team_name = team_name_text.replace(nationality_text, "").strip()
                # Also remove common artifacts like "auto" that might appear
                team_name = team_name.replace("auto", "").strip()
            else:
                team_name = team_name_text
        else:
            # Fallback to h1 if CategoryTeam-Title is not found
            h1_element = soup.find("h1")
            if h1_element:
                team_name = h1_element.text.strip()
        
        logger.info(f"Found team name: {team_name}")
        
        # Find the team roster section
        roster_section = soup.find("div", class_="CategoryTeam-Roster")
        
        if not roster_section:
            logger.warning("Team roster section not found.")
            return team_name, []
        
        # Find all anchor tags within the roster that link to players
        player_links = roster_section.find_all("a", href=True)
        
        player_data = []
        base_url = "https://play.fiba3x3.com"
        
        for link in player_links:
            href = link.get('href')
            if href and '/players/' in href:
                full_url = urljoin(base_url, href)
                
                # Get player name
                name_div = link.find("div", class_="EventPlayerItem-Name")
                player_name = name_div.text.strip() if name_div else "Unknown"
                
                player_data.append({
                    'name': player_name,
                    'url': full_url
                })
                logger.info(f"Found player: {player_name}")
        
        logger.info(f"Total players found: {len(player_data)}")
        return team_name, player_data
    
    def get_player_points(self, url):
        """Get player points with enhanced stealth"""
        self.smart_delay(3, 7)  # Random delay before each player request
        
        response = self.make_request(url)
        if not response:
            return 0.0
        
        soup = BeautifulSoup(response.text, "html.parser")
        
        ranking_label = soup.find("p", string="Ranking Points")
        if ranking_label:
            points_tag = ranking_label.find_next_sibling("p")
            if points_tag:
                points_text = points_tag.text.strip()
                try:
                    points = float(points_text.replace(',', ''))
                    logger.info(f"Found points: {points}")
                    return points
                except ValueError:
                    logger.warning(f"Could not convert points to number: {points_text}")
                    return 0.0
        
        logger.warning("Ranking Points not found")
        return 0.0
    
    def scrape_all_data(self):
        """Main scraping function with enhanced stealth and progress tracking"""
        main_url = "https://play.fiba3x3.com/events/f1acc405-6c91-4539-8ce9-f3987a8d191f/teams"
        
        logger.info("Starting enhanced stealth scraping...")
        logger.info("Getting team URLs from main page...")
        
        team_urls = self.get_main_page(main_url)
        
        if not team_urls:
            logger.info("No new team URLs found!")
            # Still process existing data if available
            if self.progress['all_player_data']:
                return self.process_existing_data()
            return None, None
        
        # Process each team
        for i, team_url in enumerate(team_urls, 1):
            logger.info(f"\n--- Processing Team {i}/{len(team_urls)} ---")
            logger.info(f"Team URL: {team_url}")
            
            try:
                # Get team name and player data
                team_name, player_data = self.visit_team_url_get_player_urls(team_url)
                
                if not player_data:
                    logger.warning(f"No players found for team: {team_name}")
                    # Mark as processed even if no players found
                    self.progress['processed_teams'].append(team_url)
                    self.save_progress()
                    continue
                
                # Process each player
                for j, player in enumerate(player_data, 1):
                    logger.info(f"  Processing Player {j}/{len(player_data)}: {player['name']}")
                    
                    # Get player points
                    points = self.get_player_points(player['url'])
                    
                    # Add to our dataset
                    player_record = {
                        'Team': team_name,
                        'Player': player['name'],
                        'Points': points,
                        'Player_URL': player['url'],
                        'Team_URL': team_url
                    }
                    
                    self.progress['all_player_data'].append(player_record)
                    
                    # Save progress after each player
                    self.save_progress()
                
                # Mark team as processed
                self.progress['processed_teams'].append(team_url)
                self.save_progress()
                
                # Long delay between teams
                if i < len(team_urls):  # Don't delay after the last team
                    self.long_delay(15, 30)
                
            except Exception as e:
                logger.error(f"Error processing team {team_url}: {e}")
                # Continue with next team
                continue
        
        return self.process_existing_data()
    
    def process_existing_data(self):
        """Process all collected data into final format"""
        if not self.progress['all_player_data']:
            logger.info("No player data collected!")
            return None, None
        
        # Create DataFrame
        df = pd.DataFrame(self.progress['all_player_data'])
        
        # Calculate team totals
        team_totals = df.groupby('Team')['Points'].sum().reset_index()
        team_totals.columns = ['Team', 'Team_Total']
        team_totals = team_totals.sort_values('Team_Total', ascending=False)
        
        # Merge team totals back to main dataframe
        df = df.merge(team_totals, on='Team')
        
        # Sort by team total (descending) then by individual points (descending)
        df = df.sort_values(['Team_Total', 'Points'], ascending=[False, False])
        
        # Display results
        logger.info("\n" + "="*80)
        logger.info("FINAL RESULTS - TEAMS RANKED BY TOTAL POINTS")
        logger.info("="*80)
        
        # Show team totals
        logger.info("\nTEAM TOTALS (Descending):")
        print(team_totals.to_string(index=False))
        
        logger.info("\n" + "="*80)
        logger.info("INDIVIDUAL PLAYER DATA:")
        logger.info("="*80)
        
        # Show individual player data
        display_df = df[['Team', 'Player', 'Points', 'Team_Total']].copy()
        print(display_df.to_string(index=False))
        
        # Save to CSV
        df.to_csv('fiba_team_rankings.csv', index=False)
        team_totals.to_csv('fiba_team_totals.csv', index=False)
        
        logger.info(f"\nData saved to:")
        logger.info(f"- fiba_team_rankings.csv (individual players)")
        logger.info(f"- fiba_team_totals.csv (team totals)")
        
        return df, team_totals

# Main execution
if __name__ == "__main__":
    scraper = StealthScraper()
    
    try:
        result = scraper.scrape_all_data()
        if result[0] is not None:
            df, team_totals = result
            logger.info("Scraping completed successfully!")
        else:
            logger.info("Scraping failed or no new data to process.")
    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user. Progress has been saved.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        logger.info("Progress has been saved. You can resume later.")