import asyncio
import random
import time
import csv
import json
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page
from flask import current_app
from .twitter_service import TwitterService, AntiBot

logger = logging.getLogger(__name__)

class ScraperService:
    """Service for scraping Twitter/X data using Playwright for advanced scenarios"""
    
    def __init__(self):
        self.twitter_service = TwitterService()
        self.browser = None
        self.page = None
    
    async def init_browser(self) -> bool:
        """Initialize Playwright browser"""
        try:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-dev-shm-usage',
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
            
            # Create page with anti-detection measures
            self.page = await self.browser.new_page()
            
            # Set user agent
            await self.page.set_user_agent(AntiBot.get_random_user_agent())
            
            # Set viewport
            await self.page.set_viewport_size({"width": 1920, "height": 1080})
            
            # Block unnecessary resources to speed up
            await self.page.route("**/*.{png,jpg,jpeg,gif,svg,css,font,woff,woff2}", 
                                lambda route: route.abort())
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing browser: {str(e)}")
            return False
    
    async def close_browser(self):
        """Close browser and cleanup"""
        try:
            if self.page:
                await self.page.close()
            if self.browser:
                await self.browser.close()
            if hasattr(self, 'playwright'):
                await self.playwright.stop()
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
    
    async def scrape_followers_advanced(self, username: str, max_followers: int = 1000) -> List[Dict]:
        """
        Advanced follower scraping using Playwright (fallback when API limits are hit)
        This is for educational purposes - in production, prefer API methods
        """
        if not await self.init_browser():
            return []
        
        followers = []
        
        try:
            # Navigate to Twitter profile (no login required for public profiles)
            profile_url = f"https://twitter.com/{username}/followers"
            await self.page.goto(profile_url, wait_until='networkidle')
            
            # Wait for content to load
            await self.page.wait_for_timeout(3000)
            
            # Check if profile exists and is public
            if "This account doesn't exist" in await self.page.text_content('body'):
                logger.warning(f"Profile @{username} doesn't exist")
                return []
            
            if "These Tweets are protected" in await self.page.text_content('body'):
                logger.warning(f"Profile @{username} is private")
                return []
            
            # Scroll and collect followers
            last_height = 0
            scroll_attempts = 0
            max_scroll_attempts = max_followers // 20  # Approximately 20 followers per scroll
            
            while len(followers) < max_followers and scroll_attempts < max_scroll_attempts:
                # Find follower elements
                follower_elements = await self.page.query_selector_all('[data-testid="UserCell"]')
                
                for element in follower_elements[len(followers):]:
                    try:
                        # Extract follower information
                        follower_data = await self._extract_follower_data(element)
                        if follower_data and follower_data not in followers:
                            followers.append(follower_data)
                            
                            if len(followers) >= max_followers:
                                break
                    
                    except Exception as e:
                        logger.error(f"Error extracting follower data: {str(e)}")
                        continue
                
                # Scroll down
                await self.page.evaluate('window.scrollTo(0, document.body.scrollHeight)')
                
                # Wait with human-like delay
                await self.page.wait_for_timeout(random.randint(2000, 4000))
                
                # Check if new content loaded
                new_height = await self.page.evaluate('document.body.scrollHeight')
                if new_height == last_height:
                    scroll_attempts += 1
                    if scroll_attempts >= 3:  # No new content after 3 attempts
                        break
                else:
                    scroll_attempts = 0
                    last_height = new_height
                
                logger.info(f"Scraped {len(followers)} followers so far...")
            
        except Exception as e:
            logger.error(f"Error scraping followers: {str(e)}")
        
        finally:
            await self.close_browser()
        
        logger.info(f"Successfully scraped {len(followers)} followers for @{username}")
        return followers
    
    async def _extract_follower_data(self, element) -> Optional[Dict]:
        """Extract follower data from DOM element"""
        try:
            # Username
            username_elem = await element.query_selector('[data-testid="UserCell"] a[role="link"]')
            username = await username_elem.get_attribute('href') if username_elem else None
            if username:
                username = username.split('/')[-1]  # Extract username from URL
            
            # Display name
            name_elem = await element.query_selector('[data-testid="UserName"] span span')
            display_name = await name_elem.text_content() if name_elem else None
            
            # Bio
            bio_elem = await element.query_selector('[data-testid="UserDescription"]')
            bio = await bio_elem.text_content() if bio_elem else ""
            
            # Profile image
            img_elem = await element.query_selector('img')
            profile_image = await img_elem.get_attribute('src') if img_elem else None
            
            # Verification status
            verified_elem = await element.query_selector('[data-testid="verifiedBadge"]')
            is_verified = verified_elem is not None
            
            if not username:
                return None
            
            return {
                'username': username,
                'display_name': display_name or username,
                'bio': bio.strip() if bio else '',
                'profile_image_url': profile_image or '',
                'verified': is_verified,
                'scraped_at': datetime.utcnow().isoformat(),
                'source': 'playwright_scraper'
            }
            
        except Exception as e:
            logger.error(f"Error extracting follower data: {str(e)}")
            return None
    
    def scrape_followers_api(self, username: str, max_followers: int = 1000) -> Tuple[bool, List[Dict]]:
        """
        Scrape followers using Twitter API (preferred method)
        """
        followers = []
        next_token = None
        
        try:
            while len(followers) < max_followers:
                # Calculate how many to request in this batch
                batch_size = min(100, max_followers - len(followers))
                
                success, data = self.twitter_service.get_user_followers(
                    username=username,
                    max_results=batch_size,
                    pagination_token=next_token
                )
                
                if not success:
                    logger.error(f"Error fetching followers: {data}")
                    break
                
                batch_followers = data.get('followers', [])
                followers.extend(batch_followers)
                
                # Check if there are more pages
                next_token = data.get('next_token')
                if not next_token:
                    break
                
                # Rate limiting - wait between requests
                AntiBot.random_delay(2, 5)
                
                logger.info(f"Fetched {len(followers)} followers so far...")
            
            logger.info(f"Successfully fetched {len(followers)} followers for @{username}")
            return True, followers
            
        except Exception as e:
            logger.error(f"Error in API follower scraping: {str(e)}")
            return False, []
    
    def process_csv_upload(self, csv_content: str) -> Tuple[bool, List[Dict]]:
        """Process uploaded CSV file containing user list"""
        try:
            # Parse CSV content
            csv_reader = csv.DictReader(csv_content.splitlines())
            users = []
            
            for row in csv_reader:
                # Expected CSV columns: username, display_name, bio, followers_count, etc.
                user_data = {
                    'username': row.get('username', '').strip().lstrip('@'),
                    'display_name': row.get('display_name', row.get('name', '')).strip(),
                    'bio': row.get('bio', row.get('description', '')).strip(),
                    'followers_count': int(row.get('followers_count', 0) or 0),
                    'following_count': int(row.get('following_count', 0) or 0),
                    'verified': str(row.get('verified', False)).lower() == 'true',
                    'profile_image_url': row.get('profile_image_url', '').strip(),
                    'source': 'csv_upload',
                    'uploaded_at': datetime.utcnow().isoformat()
                }
                
                # Validate username
                if user_data['username']:
                    users.append(user_data)
            
            logger.info(f"Processed {len(users)} users from CSV upload")
            return True, users
            
        except Exception as e:
            logger.error(f"Error processing CSV upload: {str(e)}")
            return False, []
    
    def process_json_upload(self, json_content: str) -> Tuple[bool, List[Dict]]:
        """Process uploaded JSON file containing user list"""
        try:
            data = json.loads(json_content)
            users = []
            
            # Handle different JSON structures
            if isinstance(data, list):
                user_list = data
            elif isinstance(data, dict) and 'users' in data:
                user_list = data['users']
            else:
                return False, []
            
            for user_item in user_list:
                if isinstance(user_item, str):
                    # Simple list of usernames
                    user_data = {
                        'username': user_item.strip().lstrip('@'),
                        'display_name': user_item.strip().lstrip('@'),
                        'bio': '',
                        'followers_count': 0,
                        'following_count': 0,
                        'verified': False,
                        'profile_image_url': '',
                        'source': 'json_upload',
                        'uploaded_at': datetime.utcnow().isoformat()
                    }
                elif isinstance(user_item, dict):
                    # Detailed user objects
                    user_data = {
                        'username': user_item.get('username', '').strip().lstrip('@'),
                        'display_name': user_item.get('display_name', user_item.get('name', '')).strip(),
                        'bio': user_item.get('bio', user_item.get('description', '')).strip(),
                        'followers_count': int(user_item.get('followers_count', 0) or 0),
                        'following_count': int(user_item.get('following_count', 0) or 0),
                        'verified': user_item.get('verified', False),
                        'profile_image_url': user_item.get('profile_image_url', '').strip(),
                        'source': 'json_upload',
                        'uploaded_at': datetime.utcnow().isoformat()
                    }
                else:
                    continue
                
                # Validate username
                if user_data['username']:
                    users.append(user_data)
            
            logger.info(f"Processed {len(users)} users from JSON upload")
            return True, users
            
        except Exception as e:
            logger.error(f"Error processing JSON upload: {str(e)}")
            return False, []
    
    def enrich_user_profiles(self, users: List[Dict]) -> List[Dict]:
        """
        Enrich user profiles with additional data from Twitter API
        """
        enriched_users = []
        
        for user in users:
            try:
                # Get full profile data from API
                success, profile_data = self.twitter_service.get_user_profile(user['username'])
                
                if success:
                    # Merge uploaded data with API data
                    enriched_user = {
                        **user,  # Original data
                        **profile_data,  # API data (will override original if keys match)
                        'enriched_at': datetime.utcnow().isoformat()
                    }
                else:
                    # Keep original data if API fails
                    enriched_user = user
                
                enriched_users.append(enriched_user)
                
                # Rate limiting
                AntiBot.random_delay(1, 3)
                
            except Exception as e:
                logger.error(f"Error enriching profile for @{user['username']}: {str(e)}")
                enriched_users.append(user)  # Keep original data
        
        return enriched_users
    
    def filter_users(self, users: List[Dict], filters: Dict) -> List[Dict]:
        """
        Filter users based on criteria
        """
        filtered_users = []
        
        for user in users:
            # Apply filters
            if filters.get('min_followers') and user.get('followers_count', 0) < filters['min_followers']:
                continue
            
            if filters.get('max_followers') and user.get('followers_count', 0) > filters['max_followers']:
                continue
            
            if filters.get('verified_only') and not user.get('verified', False):
                continue
            
            if filters.get('exclude_verified') and user.get('verified', False):
                continue
            
            if filters.get('bio_keywords'):
                bio = user.get('bio', '').lower()
                keywords = [kw.lower() for kw in filters['bio_keywords']]
                if not any(keyword in bio for keyword in keywords):
                    continue
            
            if filters.get('exclude_bio_keywords'):
                bio = user.get('bio', '').lower()
                exclude_keywords = [kw.lower() for kw in filters['exclude_bio_keywords']]
                if any(keyword in bio for keyword in exclude_keywords):
                    continue
            
            filtered_users.append(user)
        
        logger.info(f"Filtered users: {len(users)} -> {len(filtered_users)}")
        return filtered_users
    
    def export_users_csv(self, users: List[Dict]) -> str:
        """Export users list to CSV format"""
        if not users:
            return ""
        
        # Get all possible field names
        fieldnames = set()
        for user in users:
            fieldnames.update(user.keys())
        fieldnames = sorted(list(fieldnames))
        
        # Generate CSV content
        import io
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        
        writer.writeheader()
        for user in users:
            writer.writerow(user)
        
        return output.getvalue()
    
    def get_scraping_status(self, task_id: str) -> Dict:
        """Get status of a scraping task (for async operations)"""
        # This would typically check a task queue (Redis/Celery)
        # For now, return a mock status
        return {
            'task_id': task_id,
            'status': 'completed',
            'progress': 100,
            'total_found': 0,
            'current_batch': 0,
            'estimated_time_remaining': 0
        }
