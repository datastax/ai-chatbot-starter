import os

import concurrent
from urllib.parse import urlparse, urljoin
import requests
from bs4 import BeautifulSoup
import tqdm
from concurrent.futures import ThreadPoolExecutor


def is_valid(url):
    # checks whether `url` is a valid URL.
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except ValueError:
        return False


def get_all_website_links(url):
    # returns all URLs that is found on `url` in which it belongs to the same website
    urls = set()
    domain_name = urlparse(url).netloc
    response = requests.get(url)
    response.encoding = response.apparent_encoding  # Use chardet to guess the encoding
    soup = BeautifulSoup(response.text, "html.parser")

    for a_tag in soup.findAll("a"):
        href = a_tag.attrs.get("href")
        if href == "" or href is None:
            # href empty tag
            continue
        # join the URL if it's relative (not absolute link)
        href = urljoin(url, href)
        parsed_href = urlparse(href)
        # remove URL GET parameters, URL fragments, etc.
        href = parsed_href.scheme + "://" + parsed_href.netloc + parsed_href.path
        if not is_valid(href):
            # not a valid URL
            continue
        if href in urls:
            # already in the set
            continue
        if domain_name not in href:
            # external link
            continue
        urls.add(href)
    return urls


def clean_html(soup):
    # Remove unwanted HTML tags
    for unwanted_tag in soup(["script", "style", "header", "footer", "nav", "aside"]):
        unwanted_tag.decompose()

    # Remove divs with class 'toolbar'
    for div in soup.find_all("div", {"class": "toolbar"}):
        div.decompose()

    return soup


def fetch_url(url):
    response = requests.get(url)
    response.encoding = response.apparent_encoding  # Use chardet to guess the encoding
    soup = BeautifulSoup(response.text, "html.parser")

    body = soup.find("main")
    if body is not None:
        body = clean_html(body)

    return "Following page's URL link: ~~" + str(url) + "~~\n" + body.get_text()


def crawl_website_parallel(url, output_file: str):
    urls = get_all_website_links(url)
    raw_texts = []

    # Use ThreadPoolExecutor to parallelize the fetch_url function
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_url, url) for url in urls}

    for future in tqdm.tqdm(concurrent.futures.as_completed(futures), total=len(urls)):
        try:
            data = future.result()
        except Exception as exc:
            print(f"An exception occurred: {exc}")
        else:
            raw_texts.append(data)

    # Make directories for file if necessary
    if "/" in output_file:
        os.makedirs(
            output_file[: output_file.rfind("/")],
            exist_ok=True,
        )

    # After all the threads are done, write all the data to the file
    with open(output_file, "w", encoding="utf-8") as f_out:
        for text in raw_texts:
            f_out.write(text)
