# AI Chatbot Starter

![AI Chatbot Starter](chatbot.png)

This AI Chatbot Starter is designed to help developers find the information they need to debug their issues.

It should answer customer questions about the products or services specified.

[![Open in Gitpod](https://gitpod.io/button/open-in-gitpod.svg)](https://gitpod.io/#https://github.com/datastax/ai-chatbot-starter)

## Getting Started

1. Clone the repository
2. Make sure you have Python 3.11 installed

Now follow the steps below to get the chatbot up and running.

### Configuring the ChatBot

Documentation (provided as a list of web urls in the `config.yml`) can be ingested into your Astra DB Collection. Follow these steps:

1. Obtain your OpenAI API Key from the OpenAI Settings page.
2. Create a `config.yml` file with the values required. Here you specify both the list of pages to scrape, as well as the list of rules for your chatbot to observe. For an example of how this can look, take a look at either `config.yml.example_datastax`, or `config.yml.example_pokemon`.
3. Create a `.env` file & add the required information. Add the OpenAI Key from Step 1 as the value of `OPENAI_API_KEY`. The Astra and OpenAI env variables are required, while the others are only needed if the respective integrations are enabled.
4. From the root of the repository, run `PYTHONPATH=. python data/scrape_site.py`. This will scrape the pages specified in the `config.yml` file into text files within the `output` folder of your ai-chatbot-starter` directory.
5. From the root of the repository, run `PYTHONPATH=. python data/compile_documents.py`. This will store the embeddings for the scraped text in your AstraDB instance.

### Running the ChatBot

#### Using Docker

If you have Docker installed, you can run the app using the following command:

1. Run `docker build -t docker_aibot --no-cache .`
2. Run `docker run -p 5555:5555 docker_aibot`
3. You can test an example query by running `python scripts/call_assistant.py "<your_query_here>"`

#### Local Run

Alternatively, you can run the app normally using the following steps:

1. Run `pip install -r requirements.txt` to install the required packages
2. Run `uvicorn app:app --host 0.0.0.0 --port 5555 --reload` to run the app
3. You can test an example query by running `python scripts/call_assistant.py "<your_query_here>"`
