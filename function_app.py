import azure.functions as func
import logging
import pandas as pd
from shared_code import manage_quiz_gen
import requests
import asyncio
import json

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.service_bus_queue_trigger(arg_name="azservicebus", queue_name="myqueue",
                               connection="SERVICEBUS_CONNECTION") 
async def ServiceBusQueueTrigger(azservicebus: func.ServiceBusMessage):
    
    wiki_page = azservicebus.get_body().decode('utf-8')

    logging.info('Python ServiceBus Queue trigger processed a message:%s', wiki_page)
    print('Python ServiceBus Queue trigger processed a message: ', wiki_page)
    
    try:

        examples_filename = 'examples_qa.txt'
        json_example_filename = 'json_example_fn.txt'

        max_model_tokens=4000
        num_qa_per_section=2
        chunk_size=1000

        if wiki_page is None:
            wiki_page="Roy Lichtenstein"

        #create blob
        logging.info("**Before helper function")
        helpFunctions = manage_quiz_gen.HelperFunctions()
        #create concurrencyStatus.json
        helpFunctions.CreateconcurrencyStatus("azure-webjobs-hosts","concurrency/quiz-secd-funcapp/concurrencyStatus.json")

        logging.info("**Before manager create output file")
        helpFunctions.BlobCreationManager()

        #instance quiz manager
        q=manage_quiz_gen.Generate_Quiz()
        
        response = await asyncio.to_thread(
            q.quiz_manager, wiki_page, examples_filename,max_model_tokens,chunk_size,num_qa_per_section,json_example_filename
        )
        #response = "**Hello There!"

        #append quiz manager response
        helpFunctions.AppendDataToBlob(response)

        #read quiz manager output
        file_output=helpFunctions.ReadBlobData()

        if isinstance(file_output, str):
            logging.info(f"ServiceBusQueueTrigger response: {file_output}")
        elif isinstance(file_output, bytes):
            logging.info(f"ServiceBusQueueTrigger response: {file_output}")
        elif isinstance(file_output, dict):
            response_text = json.dumps(file_output)
            logging.info(f"ServiceBusQueueTrigger response: {response_text}")
        else:
            logging.error("Unexpected response type from quiz_manager")
    
        logging.info("Completed ServiceBus Queue")

    except Exception as e:
        logging.error(f"ServiceBusQueueTrigger: Error processing wikipage: {e}")