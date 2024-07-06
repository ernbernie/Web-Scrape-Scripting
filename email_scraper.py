import asyncio
import aiohttp
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin, urlparse
import chardet
from datetime import datetime
import os

# Set to keep track of visited URLs and avoid duplicates
visited_urls = set()
unique_emails = set()  # Set to keep track of unique email addresses
total_urls_scraped = 0  # Counter for total URLs scraped

# Regular expression pattern to find email addresses
email_pattern = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}')

async def fetch(session, url):
    """Fetch the content of the URL."""
    global total_urls_scraped
    try:
        async with session.get(url) as response:
            response.raise_for_status()  # Ensure we notice bad responses
            content_type = response.headers.get('Content-Type', '').lower()
            if 'text' in content_type or 'html' in content_type:
                try:
                    # Try to decode the response content as UTF-8 text
                    total_urls_scraped += 1
                    return await response.text()
                except UnicodeDecodeError:
                    # If that fails, detect the encoding and decode accordingly
                    raw_content = await response.read()
                    detected = chardet.detect(raw_content)
                    encoding = detected.get('encoding', 'utf-8')
                    total_urls_scraped += 1
                    return raw_content.decode(encoding, errors='ignore')
            else:
                return None
    except aiohttp.ClientError as e:
        # If there's an error (like a network problem), log it and return None
        print(f"Failed to fetch {url}: {e}")
        return None

def extract_emails(text):
    """Extract email addresses from the given text."""
    return email_pattern.findall(text)

def is_image_url(url):
    """Check if the URL is an image."""
    # This simple check looks at the file extension to decide if the URL is for an image
    return url.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg'))

async def find_emails(session, url, base_url, depth=2):
    """Recursively search for email addresses."""
    # Stop if we've gone too deep or have already visited this URL
    if depth < 0 or url in visited_urls:
        return None

    print(f"Scraping URL: {url}")
    visited_urls.add(url)  # Remember that we've visited this URL
    html = await fetch(session, url)  # Fetch the content of the page
    if html is None:
        return None

    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(html, 'html.parser')
    
    # Extract emails from the page text
    emails = extract_emails(soup.get_text())
    if emails:
        unique_emails.update(emails)  # Add emails to the set of unique emails
        print(f"Emails found on {url}: {emails}")

    # Look through all links on the page
    links = soup.find_all('a')

    for link in links:
        href = link.get('href', '')
        if 'mailto:' in href:
            # Extract email address from mailto links
            email = href.split(':')[1]
            if email:
                unique_emails.add(email)  # Add email to the set of unique emails
        
        full_url = urljoin(base_url, href)
        # If the link is within the same domain and not an image, follow it
        if urlparse(full_url).netloc == urlparse(base_url).netloc and not is_image_url(full_url):
            await find_emails(session, full_url, base_url, depth - 1)
    
    # Return None if no more links to follow
    return None

async def main():
    """Run the email search on multiple base URLs and save the results."""
    # List of base URLs to start the search from
    base_urls = [
        'https://www.examplewebsite.com' #Replace with actual website name, or names.
    ]

    async with aiohttp.ClientSession() as session:
        # Create a list of tasks for asyncio to run concurrently
        tasks = [find_emails(session, base_url, base_url) for base_url in base_urls]
        await asyncio.gather(*tasks)  # Wait for all tasks to complete
    
    # Use an absolute path for the output file
    emails_file = os.path.join(os.getcwd(), 'emails.txt')
    
    # Debugging print statements to check paths and results
    print(f"Current working directory: {os.getcwd()}")
    print(f"Emails file path: {emails_file}")

    # Ensure the emails file is created and cleared before writing
    with open(emails_file, 'w', encoding='utf-8') as f:
        f.write("")

    # Write all collected emails to a separate file
    try:
        with open(emails_file, 'w', encoding='utf-8') as f:
            f.write("Collected Emails:\n\n")
            for email in sorted(unique_emails):
                f.write(f"{email}\n")
            print(f"Emails saved to {emails_file}")
    except OSError as e:
        print(f"Error writing to file {emails_file}: {e}")

if __name__ == '__main__':
    asyncio.run(main())
