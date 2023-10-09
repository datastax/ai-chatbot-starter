# AI Chatbot
This AI Chatbot is designed to help developers find the information they need to debug their issues.

It should answer customer questions about the products or services specified.

## Getting Started

1. Make sure you have Python 3.10+ installed
2. `pip3 install -r requirements.txt` to install the required packages
3. Bring in your Google `*.json` file for the Google Cloud API. This is required for the NLP to work. You can find more information [here](https://cloud.google.com/natural-language/docs/setup#auth).
4. Create a `.env` file & add the required information. Note that there may be some entries missing ATM, so just pay attention to what each program requires.

### Running the full app

5. Ensure you're in the `ai-chatbot` directory
6. Use `uvicorn app:app --host 0.0.0.0 --port 5000 --reload` to run the app

### Embedding documentation into a table

Documentation (provided as a list of web urls) can be ingested into a database using the following script `data/compile-documents.py`.

### Intercom Apps
- [Intercom Dev App](https://app.intercom.com/a/apps/j838b4xj/developer-hub/app-packages/97809)
- [Intercom Prod App](https://app.intercom.com/a/apps/bpbxnnmr/developer-hub/app-packages/99817)
