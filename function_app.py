import azure.functions as func
import logging
import pandas as pd
from shared_code import manage_quiz_gen
import asyncio
import json

logging.basicConfig(level=logging.DEBUG)

app = func.FunctionApp(http_auth_level=func.AuthLevel.FUNCTION)

@app.service_bus_queue_trigger(arg_name="azservicebus", queue_name="myqueue",
                               connection="SERVICEBUS_CONNECTION") 
async def ServiceBusQueueTrigger(azservicebus: func.ServiceBusMessage):
    
    file_content = azservicebus.get_body().decode('utf-8')

    logging.info('Python ServiceBus Queue trigger processed a message:%s', file_content)
    #print('Python ServiceBus Queue trigger processed a message: ', file_content)
    
    try:

        examples_filename = 'examples_qa.txt'
        json_example_filename = 'json_example_fn.txt'

        max_model_tokens=4000
        num_qa_per_section=2
        chunk_size=1000

        if file_content is None:
            logging.error("No File provided or File is empty")

        #create blob
        helpFunctions = manage_quiz_gen.BlobManager()
        
        #create concurrencyStatus.json
        #helpFunctions.CreateconcurrencyStatus("azure-webjobs-hosts","concurrency/quiz-secd-funcapp/concurrencyStatus.json")

        #create output file
        helpFunctions.BlobCreationManager()

        #instance quiz manager
        q=manage_quiz_gen.Generate_Quiz_From_File()
        
        #Get Q&A
        response = await q.quiz_manager(file_content, examples_filename,max_model_tokens,chunk_size,num_qa_per_section,json_example_filename)
        #response = await coroutine
        logging.warning(response)
        # list into json
        response_json = json.dumps(response)
        logging.critical(response_json)

        #append quiz manager response
        # helpFunctions.AppendDataToBlob(response_json)

        # #read quiz manager output, returns json
        # file_output_json=helpFunctions.ReadBlobData()
        # logging.critical("###")
        # logging.critical(type(file_output_json))
        # logging.warning(file_output_json)

        # #check it's json before printing json output
        # try:
        #     #check output is json to print
        #     json.loads(file_output_json)
        #     logging.warning(file_output_json)
        # except json.JSONDecodeError:
        #     print("file_output_json is not valid JSON.")
    
        logging.info("**Completed ServiceBus Queue")

    except Exception as e:
        logging.error(f"**ServiceBusQueueTrigger: Error processing File: {e}")