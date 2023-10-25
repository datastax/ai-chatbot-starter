# AI Chatbot Starter
![AI Chatbot Starter](chatbot.png)

This AI Chatbot Starter is designed to help developers find the information they need to debug their issues.

It should answer customer questions about the products or services specified.

## Getting Started

1. Make sure you have Python 3.10+ installed
2. `pip3 install -r requirements.txt` to install the required packages
3. Obtain your OpenAI API Key from the OpenAI Settings page
4. Create a `.env` file & add the required information. Add the OpenAI Key from Step 3 as the value of `OPENAI_API_KEY`. Note that there may be some entries missing ATM, so just pay attention to what each program requires.

### Running the full app
1. Ensure you're in the `ai-chatbot-starter` directory
2. Use `uvicorn app:app --host 0.0.0.0 --port 5010 --reload` to run the app

### Embedding documentation into a table
Documentation (provided as a list of web urls) can be ingested into a database using the following script `data/compile-documents.py`.
