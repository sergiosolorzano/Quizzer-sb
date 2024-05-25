import azure.functions as func
import logging
import pandas as pd
from shared_code import manage_quiz_gen

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.route(route="http_trigger")
def http_trigger(req: func.HttpRequest) -> func.HttpResponse:
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
    logging.info(f"User entered Wiki: {wiki_page}")
    print(f"Received Wiki page: {wiki_page}")

    if wiki_page is None:
        wiki_page="Roy Lichtenstein"
        ##return func.HttpResponse(f"Could not find Wikipage for {wiki_page}. Add query param at end of url like &wiki=Roy Lichtenstein", mimetype="text/json")    

    q=manage_quiz_gen.Generate_Quiz()
    
    response = q.quiz_manager(wiki_page, examples_filename,max_model_tokens,chunk_size,num_qa_per_section,json_example_filename)
    return func.HttpResponse(response, mimetype="text/json")



@app.service_bus_queue_trigger(arg_name="azservicebus", queue_name="myqueue",
                               connection="SERVICEBUS_CONNECTION") 
def ServiceBusQueueTrigger(azservicebus: func.ServiceBusMessage):
    logging.info('Python ServiceBus Queue trigger processed a message: %s',
                azservicebus.get_body().decode('utf-8'))
