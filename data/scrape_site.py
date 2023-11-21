import os

from urllib.parse import urlparse

from dotenv import load_dotenv

from chatbot_api.crawl_scrape_docs import crawl_website_parallel
from pipeline.config import load_config

load_dotenv(".env")
config = load_config("config.yml")

# Astra docs
for website in config.doc_pages:
    parsed_website = urlparse(website)
    basename_website = os.path.basename(parsed_website.path)

    crawl_website_parallel(website, os.path.join("data", "docs", f"{basename_website}.txt"))
