import json
import re
import sys
from datetime import datetime
from pathlib import Path

import requests
from bs4 import BeautifulSoup


# Steam sometimes uses full SteamID64s and sometimes shorter account IDs.
# Subtracting this base converts SteamID64 -> account ID.
STEAM_ID64_BASE = 76561197960265728

COMMENTS_PER_REQUEST = 100
MAX_COMMENT_REQUESTS = 1000
REQUEST_TIMEOUT_SECONDS = 20

STEAM_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://steamcommunity.com",
    "X-Requested-With": "XMLHttpRequest",
}


HTML_STYLE = """
<style>
    body {
        background: #1b2838;
        color: #acb2b8;
        font-family: Arial, Helvetica, Verdana, sans-serif;
        font-size: 14px;
        margin: 0;
        padding: 18px 38px;
        text-align: left;
    }

    h1 {
        color: #66c0f4;
        font-size: 22px;
        font-weight: normal;
        margin: 0 0 22px 0;
    }

    .commentthread_comment {
        position: relative;
        background: transparent;
        border: none;
        padding: 6px 0 14px 0;
        margin-bottom: 10px;
        min-height: 58px;
        overflow: visible;
        text-align: left;
    }

    .commentthread_comment_content {
        width: 100%;
        text-align: left;
    }

    .commentthread_comment_author {
        display: flex;
        flex-direction: row;
        align-items: flex-start;
        text-align: left;
    }

    .commentthread_comment_avatar {
        position: relative;
        flex: 0 0 auto;
        width: 52px;
        height: 52px;
        margin-right: 22px;
        overflow: visible;
    }

    /* Actual avatar container */
    .commentthread_comment_avatar > a {
        display: block;
        position: relative;
        z-index: 1;
        width: 52px;
        height: 52px;
        overflow: hidden;
        border: 2px solid #316282;
        box-sizing: border-box;
    }

    /* Static avatars and animated avatars wrapped in <picture> */
    .commentthread_comment_avatar > a > img,
    .commentthread_comment_avatar > a > picture,
    .commentthread_comment_avatar > a > picture > img {
        display: block;
        width: 52px !important;
        height: 52px !important;
        max-width: 52px !important;
        max-height: 52px !important;
        object-fit: cover;
    }

    /* Steam avatar frame overlay */
    .commentthread_comment_avatar > .profile_avatar_frame {
        position: absolute;
        z-index: 2;
        pointer-events: none;
        width: 64px;
        height: 64px;
        left: -6px;
        top: -6px;
        overflow: visible;
    }

    .commentthread_comment_avatar > .profile_avatar_frame picture,
    .commentthread_comment_avatar > .profile_avatar_frame img {
        display: block;
        width: 64px !important;
        height: 64px !important;
        max-width: 64px !important;
        max-height: 64px !important;
        object-fit: contain;
    }

    .author_name_group {
        display: flex;
        flex-direction: column;
        min-width: 0;
    }

    .author_name_group .flex_row {
        display: flex;
        flex-direction: row;
        align-items: baseline;
        gap: 8px;
    }

    .commentthread_author_link {
        color: #c7d5e0;
        font-size: 18px;
        line-height: 1.15;
        font-weight: normal;
        text-decoration: none;
    }

    .commentthread_author_link:hover {
        color: #ffffff;
        text-decoration: none;
    }

    .commentthread_author_link bdi {
        font-weight: normal;
    }

    .local_author_badge,
    .commentthread_comment_authorbadge,
    .commentthread_authorbadge {
        color: #d6c84f;
        font-size: 17px;
        font-weight: normal;
        margin-left: 3px;
    }

    .commentthread_comment_timestamp {
        color: #8f98a0;
        font-size: 16px;
        line-height: 1.15;
        margin-top: 5px;
    }

    .commentthread_comment_text {
        color: #ffffff;
        font-size: 16px;
        line-height: 1.35;
        margin-top: 8px;
        margin-left: 76px;
        max-width: 1400px;
        white-space: normal;
        text-align: left;
    }

    .commentthread_comment_text a {
        color: #66c0f4;
        text-decoration: none;
    }

    .commentthread_comment_text a:hover {
        color: #ffffff;
        text-decoration: underline;
    }

    .commentthread_comment_actions,
    .comment_footer_ctn,
    .commentthread_footer,
    .commentthread_entry_quotebox {
        display: none;
    }
</style>
"""


def exit_with_error(message):
    print(message)
    sys.exit(1)


def safe_int(value, default=0):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def make_safe_filename(filename):
    filename = re.sub(r'[<>:"/\\|?*]', "-", filename)
    filename = re.sub(r"\s+", " ", filename).strip()
    return filename


def extract_workshop_id(url):
    match = re.search(r"id=(\d+)", url)

    if not match:
        exit_with_error(
            "Invalid URL format. Make sure it includes 'id=' followed by the Workshop item ID."
        )

    return match.group(1)


def extract_owner_id(soup):
    # Steam hides the owner ID in one of the page scripts.
    for script in soup.find_all("script"):
        if not script.string:
            continue

        match = re.search(r'"owner":\s*"(\d+)"', script.string)

        if match:
            return match.group(1)

    exit_with_error("Failed to extract owner_id from the Workshop page.")


def extract_workshop_title(soup):
    title_tag = soup.find("div", class_="workshopItemTitle")

    if not title_tag:
        exit_with_error("Failed to extract title from the Workshop page.")

    return title_tag.text.strip()


def extract_workshop_details(url):
    try:
        response = requests.get(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
    except requests.RequestException as error:
        exit_with_error(f"Failed to fetch the Workshop page: {error}")

    soup = BeautifulSoup(response.content, "html.parser")

    workshop_id = extract_workshop_id(url)
    owner_id = extract_owner_id(soup)
    title = extract_workshop_title(soup)

    return workshop_id, owner_id, title


def fetch_comments(workshop_id, owner_id):
    all_comments = []

    session = requests.Session()
    session.headers.update(STEAM_HEADERS)
    session.headers.update(
        {
            "Referer": f"https://steamcommunity.com/sharedfiles/filedetails/?id={workshop_id}",
        }
    )

    comments_url = (
        f"https://steamcommunity.com/comment/PublishedFile_Public/render/"
        f"{owner_id}/{workshop_id}/"
    )

    start = 0

    for request_number in range(1, MAX_COMMENT_REQUESTS + 1):
        print(
            f"Fetching comment batch {request_number}: "
            f"start={start}, count={COMMENTS_PER_REQUEST}"
        )

        data = {
            "start": start,
            "totalcount": 0,
            "count": COMMENTS_PER_REQUEST,
            "sessionid": "",
            "feature2": -1,
        }

        try:
            response = session.post(
                comments_url,
                data=data,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except requests.RequestException as error:
            print(f"Request failed at start={start}: {error}")
            break

        try:
            # Steam sometimes returns JSON with a UTF-8 BOM. utf-8-sig strips it.
            json_data = json.loads(response.content.decode("utf-8-sig"))
        except json.JSONDecodeError:
            print("Failed to parse JSON.")
            print("Response preview:")
            print(response.text[:500])
            break

        comments_html = json_data.get("comments_html", "")

        # Seen as total_count in practice, but this keeps us flexible.
        total_count = safe_int(
            json_data.get("total_count") or json_data.get("totalcount")
        )

        print(
            f"Response: success={json_data.get('success')}, "
            f"html_length={len(comments_html)}, "
            f"total_count={total_count}"
        )

        if not comments_html.strip():
            print("No more comments found.")
            break

        all_comments.append(comments_html)
        start += COMMENTS_PER_REQUEST

        if total_count and start >= total_count:
            print("Reached reported total comment count.")
            break
    else:
        print(
            f"Stopped after {MAX_COMMENT_REQUESTS} comment batches. "
            "Possible infinite pagination issue."
        )

    print(f"Total comment batches fetched: {len(all_comments)}")
    return all_comments


def add_missing_author_badges(comment_html, owner_id):
    soup = BeautifulSoup(comment_html, "html.parser")

    try:
        owner_account_id = str(int(owner_id) - STEAM_ID64_BASE)
    except ValueError:
        owner_account_id = None

    for comment in soup.select(".commentthread_comment"):
        author_link = comment.select_one("a.commentthread_author_link")

        if not author_link:
            continue

        href = author_link.get("href", "")
        data_miniprofile = author_link.get("data-miniprofile", "")

        is_owner = (
            owner_id in href
            or (owner_account_id and data_miniprofile == owner_account_id)
        )

        if not is_owner:
            continue

        flex_row = comment.select_one(".author_name_group .flex_row")

        if not flex_row:
            continue

        already_has_author_badge = "[author]" in flex_row.get_text(
            " ",
            strip=True,
        ).lower()

        if already_has_author_badge:
            continue

        badge = soup.new_tag("span")
        badge["class"] = "local_author_badge"
        badge.string = "[author]"

        flex_row.append(badge)

    return str(soup)


def build_html_document(comments, owner_id):
    comments_html = "\n".join(
        add_missing_author_badges(comment_html, owner_id)
        for comment_html in comments
    )

    return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Workshop Comments</title>
    {HTML_STYLE}
</head>
<body>
    <h1>All Comments</h1>
    {comments_html}
</body>
</html>
"""


def create_html_file(comments, title, owner_id):
    current_time = datetime.now().strftime("%Y%m%d %H_%M")
    filename = make_safe_filename(f"{title} - All Comments - {current_time}.html")

    print(f"Creating HTML file: {filename}")

    html_content = build_html_document(comments, owner_id)

    output_path = Path(filename)
    output_path.write_text(html_content, encoding="utf-8")

    print(f"HTML file created successfully: {output_path}")


def main():
    if len(sys.argv) < 2:
        exit_with_error("Usage: python steam_comments_fetcher.py <workshop_url>")

    workshop_url = sys.argv[1]

    workshop_id, owner_id, title = extract_workshop_details(workshop_url)

    print(f"Workshop ID: {workshop_id}, Owner ID: {owner_id}, Title: {title}")

    comments = fetch_comments(workshop_id, owner_id)
    create_html_file(comments, title, owner_id)


if __name__ == "__main__":
    main()
