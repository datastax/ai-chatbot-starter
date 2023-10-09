import re
import validators
import regex


class UrlUtility:
    # Extract the URL from the text
    @staticmethod
    def __extract_url(text):
        # Regular expression pattern to match URLs
        pattern = re.compile(r"(https?://\S+)")

        # Find all matches of URLs in the text
        matches = re.findall(pattern, text)

        # Return the first match if found, or None if no match
        return matches if matches else None

    @staticmethod
    def replace_broken_urls(text, replaced):
        # Regular expression to match URLs
        url_pattern = regex.compile(r"https?://[^ ]+?(?<!\.)")

        def replacer(match):
            url = match.group(0)
            is_valid = UrlUtility.__is_valid_url(url)
            print("URL: " + url, is_valid)
            if is_valid:
                return f"[here]({url})"
            else:
                print("Replacing broken URL: " + url)
                return replaced

        # Use re.sub to remove all URLs from the text
        no_url_text = regex.sub(url_pattern, replacer, text)
        # [[ artifacts can be left behind, this just cleans them up
        no_url_text = no_url_text.replace("[[", "[").replace("))", ")")
        return no_url_text

    @staticmethod
    def replace_doc_urls(text):
        url_pattern = r"~~.*?~~"
        text = re.sub(url_pattern, "", text)
        url_pattern = r"(Previous document was from URL link:\s*)https?://[^\s]+"
        text = re.sub(url_pattern, "", text)
        return text

    @staticmethod
    def __is_valid_url(url):
        return validators.url(url)

    @staticmethod
    def contains_invalid_url(text):
        # Extract the URL from the text
        urls = UrlUtility.__extract_url(text)
        for url in urls:
            if not UrlUtility.__is_valid_url(url):
                return True
        return False

    @staticmethod
    def getInvalidUrls(text):
        # Extract the URL from the text
        urls = UrlUtility.__extract_url(text)
        invalid_urls = []
        if urls is None:
            return []
        for url in urls:
            if not UrlUtility.__is_valid_url(url):
                invalid_urls.append(url)
        return invalid_urls
