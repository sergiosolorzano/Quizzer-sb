import azure.functions as func
import logging
import pandas as pd
from shared_code import manage_quiz_gen
import requests
import asyncio
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="http_trigger")
#def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
async def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
    try:

        logging.info('Python HTTP trigger function processed a request.')
        print('Python HTTP trigger function processed a request.')

        max_model_tokens=5000
        num_qa_per_section=2
        chunk_size=1000

        examples_filename = 'examples_qa.txt'
        json_example_filename = 'json_example_fn.txt'

        max_model_tokens=4000
        num_qa_per_section=2
        chunk_size=1000

        wiki_page = req.params.get("wiki")
        logging.info(f"HttpTrigger: User entered Wiki: {wiki_page}")
        print(f"HttpTrigger: Received Wiki page: {wiki_page}")

        if wiki_page is None:
            wiki_page="Roy Lichtenstein"
            ####return func.HttpResponse(f"Could not find Wikipage for {wiki_page}. Add query param at end of url like &wiki=Roy Lichtenstein", mimetype="text/json")    

        q=manage_quiz_gen.Generate_Quiz()
        
        response = await asyncio.to_thread(q.quiz_manager, wiki_page, examples_filename,max_model_tokens,chunk_size,num_qa_per_section,json_example_filename)
        #return func.HttpResponse(response, mimetype="text/json")

        if isinstance(response, str):
            return func.HttpResponse(response, mimetype="text/json")
        elif isinstance(response, dict):
            return func.HttpResponse(json.dumps(response), mimetype="application/json")
        else:
            return func.HttpResponse("Unexpected HttpTrigger - not exception - response type", status_code=500)
    
    except Exception as e:
        logging.error(f"HttpTrigger: Error processing HTTP trigger: {e}")
        return func.HttpResponse(f"HttpTrigger: Error processing request: {e}", status_code=500)


@app.service_bus_queue_trigger(arg_name="azservicebus", queue_name="myqueue",
                               connection="SERVICEBUS_CONNECTION") 
async def ServiceBusQueueTrigger(azservicebus: func.ServiceBusMessage):
    
    wiki_page = azservicebus.get_body().decode('utf-8')

    logging.info('Python ServiceBus Queue trigger processed a message: %s',
                wiki_page)
    
    req = func.HttpRequest(
        method='GET',
        url='/api/http_trigger',
        params={'wiki': wiki_page},
        headers={},
        body=b''  # Ensuring the body is an empty byte string
    )

    try:
        response = http_trigger(req)
        if response and response.status_code == 200:
            logging.info(f"HTTP trigger response: {response.get_body().decode('utf-8')}")
        else:
            logging.error(f"Failed to trigger HTTP function. Status code: {response.status_code if response else 'None'}, Response: {response.get_body().decode('utf-8') if response else 'None'}")
    except Exception as e:
        logging.error(f"ServiceBusQueueTrigger: Error triggering HTTP function: {e}")