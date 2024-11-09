import sys
import requests
import re
from bs4 import BeautifulSoup
from datetime import datetime

def extract_workshop_details(url):
    # Fetch the Workshop page HTML
    response = requests.get(url)
    if response.status_code != 200:
        print("Failed to fetch the Workshop page. Please check the URL.")
        sys.exit(1)
    
    # Parse the HTML content to extract owner_id and title
    soup = BeautifulSoup(response.content, "html.parser")
    script_tags = soup.find_all("script")

    # Extract owner_id
    owner_id = None
    for script in script_tags:
        if script.string:
            match = re.search(r'"owner":\s*"(\d+)"', script.string)
            if match:
                owner_id = match.group(1)
                break

    if not owner_id:
        print("Failed to extract owner_id from the Workshop page.")
        sys.exit(1)

    # Extract title using the workshopItemTitle class
    title_tag = soup.find("div", class_="workshopItemTitle")
    if not title_tag:
        print("Failed to extract title from the Workshop page.")
        sys.exit(1)

    title = title_tag.text.strip()

    # Extract the workshop_id from the URL
    match = re.search(r"id=(\d+)", url)
    if not match:
        print("Invalid URL format. Make sure it includes 'id=' followed by the Workshop item ID.")
        sys.exit(1)
    
    workshop_id = match.group(1)
    return workshop_id, owner_id, title

def fetch_comments(workshop_id, owner_id):
    all_comments = []
    start = 0

    while True:
        # Construct the URL and POST data for fetching comments
        url = f"https://steamcommunity.com/comment/PublishedFile_Public/render/{owner_id}/{workshop_id}/"
        data = {
            "start": start,
            "totalcount": 0,
            "count": 100  # Fetch 100 comments at a time to minimize requests
        }
        response = requests.post(url, data=data)
        json_data = response.json()

        # Extract the HTML content of the comments
        comments_html = json_data.get("comments_html", "")
        if not comments_html:
            print("No more comments found. Exiting loop.")
            break

        all_comments.append(comments_html)
        start += 100  # Increment by 100 to fetch the next batch

    print(f"Total comments fetched: {len(all_comments)} batches.")
    return all_comments

def create_html_file(comments, title):
    # Format the current date and time
    current_time = datetime.now().strftime("%Y%m%d %H_%M")

    # Create the file name using the title and current date/time
    filename = f"{title} - All Comments - {current_time}.html".replace(":", "-")
    print(f"Creating HTML file: {filename}")

    # Updated CSS for side-by-side avatar layout
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Workshop Comments</title>
        <style>
            body {
                background-color: #1b2838;
                color: #c7d5e0;
                font-family: Arial, Helvetica, sans-serif;
                padding: 20px;
            }
            h1 {
                color: #66c0f4;
            }
            .commentthread_comment {
                display: flex;
                background-color: #2a475e;
                border: 1px solid #3c5a77;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 4px;
                align-items: flex-start;
            }
            .commentthread_comment_avatar {
                flex-shrink: 0;
                margin-right: 10px;
            }
            .commentthread_comment_avatar img {
                width: 50px;
                height: 50px;
                border-radius: 4px;  /* Square shape with rounded corners */
            }
            .comment_content {
                flex-grow: 1;
            }
            .commentthread_comment_author {
                font-weight: bold;
                color: #66c0f4;
            }
            .commentthread_comment_text {
                margin-top: 5px;
            }
        </style>
    </head>
    <body>
        <h1>All Comments</h1>
    """

    for comment_html in comments:
        html_content += comment_html

    html_content += "</body></html>"

    # Write the HTML content to the file
    with open(filename, "w", encoding="utf-8") as file:
        file.write(html_content)
    print(f"HTML file created successfully: {filename}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python steam_comments_fetcher.py <workshop_url>")
        sys.exit(1)

    workshop_url = sys.argv[1]
    workshop_id, owner_id, title = extract_workshop_details(workshop_url)
    
    print(f"Workshop ID: {workshop_id}, Owner ID: {owner_id}, Title: {title}")
    comments = fetch_comments(workshop_id, owner_id)
    create_html_file(comments, title)
