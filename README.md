# Steam Comments Fetcher

Easily fetch all comments from a Steam Workshop item and export them into a neatly formatted HTML file. 

No more Ctrl+F'ing on dozens of pages to see if you're the first person with an issue using a mod!

![image](https://github.com/user-attachments/assets/a81c26e8-804b-44b6-95ee-5ae43f3ba927)


## Features
- Fetches all comments from any given Steam Workshop item.
- Exports all comments to a single HTML file styled to match Steam’s appearance. (kinda)

## Requirements
- Python 3.7 or higher
- Dependencies: `requests` and `beautifulsoup4`

## Installation
Clone this repository:

```
git clone https://github.com/thisaccountname/Steamy-Comments.git
cd Steamy-Comments
```
Install the required dependencies:
```
pip install -r requirements.txt
```
## Usage

1. Open a terminal and navigate to the src directory.
2. Run the script with a Steam Workshop URL:
```
python steamy_comments.py "https://steamcommunity.com/sharedfiles/filedetails/?id=3118990099"
```

The script will generate an HTML file named after the Workshop item title, followed by the current date and time.

## Example

```
python steam_comments_fetcher.py "https://steamcommunity.com/sharedfiles/filedetails/?id=3118990099"
```

Output: `True Music Jukebox - All Comments - 20241108 16_46.html`

![image](https://github.com/user-attachments/assets/a23a5b79-e11a-433e-b2a7-909fe085b00f)


## Notes

- The owner_id is automatically extracted from the Workshop page, so you don’t need to worry about providing it.
- The generated HTML file is styled similarly to Steam’s comment section for a familiar look. (not perfect)

## Contributing

Feel free to open issues or submit pull requests to improve the script!

## License

MIT License
