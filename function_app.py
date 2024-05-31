import azure.functions as func
import logging
import pandas as pd
from shared_code import manage_quiz_gen
import requests
import asyncio
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="http_trigger")
async def http_trigger(req: func.HttpRequest) -> func.HttpResponse:

    wiki_page = req.params.get("wiki")
    logging.info(f"HttpTrigger: User entered Wiki: {wiki_page}")
    print(f"HttpTrigger: Received Wiki page: {wiki_page}")

@app.service_bus_queue_trigger(arg_name="azservicebus", queue_name="myqueue",
                               connection="SERVICEBUS_CONNECTION") 
async def ServiceBusQueueTrigger(azservicebus: func.ServiceBusMessage):
    
    wiki_page = azservicebus.get_body().decode('utf-8')

    logging.info('Python ServiceBus Queue trigger processed a message: %s',wiki_page)
    print('Python ServiceBus Queue trigger processed a message: %s',wiki_page)
    
    try:

        max_model_tokens=5000
        num_qa_per_section=2
        chunk_size=1000

        examples_filename = 'examples_qa.txt'
        json_example_filename = 'json_example_fn.txt'

        max_model_tokens=4000
        num_qa_per_section=2
        chunk_size=1000

        if wiki_page is None:
            wiki_page="Roy Lichtenstein"

        q=manage_quiz_gen.Generate_Quiz()
        
        response = await asyncio.to_thread(q.quiz_manager, wiki_page, examples_filename,max_model_tokens,chunk_size,num_qa_per_section,json_example_filename)

        if isinstance(response, str):
            logging.info(f"ServiceBusQueueTrigger response: {response}")
        elif isinstance(response, dict):
            response_text = json.dumps(response)
            logging.info(f"ServiceBusQueueTrigger response: {response_text}")
        else:
            logging.error("Unexpected response type from quiz_manager")
    
    except Exception as e:
        logging.error(f"ServiceBusQueueTrigger: Error processing wikipage: {e}")