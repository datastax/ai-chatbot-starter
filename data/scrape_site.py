import os
import sys

from urllib.parse import urlparse

sys.path.append("../")

from dotenv import load_dotenv

load_dotenv("../.env")


# The below line will be red in Pycharm, but it's fine
from chatbot_api.crawl_scrape_docs import crawl_website_parallel

# Astra docs
for website in os.getenv("DOCUMENTATION_PAGES").split(","):
    parsed_website = urlparse(website)
    basename_website = os.path.basename(parsed_website.path)

    crawl_website_parallel(website, f"docs/{basename_website}.txt")
