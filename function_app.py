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

        #create blob
        logging.info("**Before helper function")
        helpFunctions = manage_quiz_gen.HelperFunctions()
        logging.info("**Before blob_client creation function")
        blob_client = helpFunctions.BlobCreationManager()

        q=manage_quiz_gen.Generate_Quiz()
        
        # response = await asyncio.to_thread(
        #     q.quiz_manager, wiki_page, max_model_tokens=5000, num_qa_per_section=2, chunk_size=1000
        # )
        response = "**Hello There!"

        #append response
        helpFunctions.AppendDataToBlob(response)

        file_output=helpFunctions.ReadBlobData()

        if isinstance(file_output, str):
            logging.info(f"ServiceBusQueueTrigger response: {file_output}")
        elif isinstance(file_output, dict):
            response_text = json.dumps(file_output)
            logging.info(f"ServiceBusQueueTrigger response: {response_text}")
        else:
            logging.error("Unexpected response type from quiz_manager")
    
        #ensure that your function processes each message from the Service Bus queue only once
        #await azservicebus.complete()
        logging.info("Completed ServiceBus Queue")

    except Exception as e:
        logging.error(f"ServiceBusQueueTrigger: Error processing wikipage: {e}")