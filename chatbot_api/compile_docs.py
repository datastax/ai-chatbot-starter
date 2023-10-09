# Usage:
# process_directory("/path/to/source/directory", "/path/to/destination/directory")

import os
from typing import List
from llama_index import Document
from concurrent.futures import ThreadPoolExecutor

URL_INDICATOR_PREFIX = "Following page's URL link: ~~"
URL_INDICATOR_POSTFIX = "~~\n"


def find_first_url(content: str) -> str:
    """Finds the first URL present in 'content' assuming the format seen in scraped docs"""
    return content[: content.find(URL_INDICATOR_POSTFIX)]


def convert_scraped_files_to_documents(dir_path: str) -> List[Document]:
    """Convert the set of scraped documentation into LlamaIndex Documents

    NOTE: This splits the pages by URL, and treats each distinct URL as a document
    """
    all_docs = []

    def _process_file(filepath: str) -> None:
        # Each file contains many documents/URLs
        with open(filepath) as docs_file:
            contents = docs_file.read()

        docs = [
            Document(
                # Skip the URL and padding newlines
                text=content[
                    len(find_first_url(content) + URL_INDICATOR_POSTFIX) :
                ].strip(),
                metadata=dict(url=find_first_url(content)),
            )
            for content in contents.split(URL_INDICATOR_PREFIX)
            if len(content.strip()) > 0
        ]
        all_docs.extend(docs)

    with ThreadPoolExecutor() as executor:
        for dirpath, dirnames, filenames in os.walk(dir_path):
            for filename in filenames:
                if filename.endswith((".adoc", ".txt", ".csv", ".md")):
                    file_path = os.path.join(dirpath, filename)
                    executor.submit(_process_file, file_path)

    return all_docs
