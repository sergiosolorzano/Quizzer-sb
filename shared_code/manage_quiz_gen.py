import os
import azure.functions as func
import logging
import json
import pandas as pd
import azure.identity
import json
from openai import AzureOpenAI
from azure.keyvault.secrets import SecretClient
from azure.identity import DefaultAzureCredential
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
import tiktoken
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

class Generate_Quiz_From_File:
    def __init__(self):
        self.json_example = None
        self.qa_generator = None
        self.file_content = None
        self.file_content_chunked_sections_list = []
        self.all_sections_qa_response_list=[]
        self.openai_k= None
        self.quiz_examples = None
        self.questions_to_date = []
        
    async def quiz_manager(self, file_content, quiz_examples_filename='examples_qa.txt',max_model_tokens=4000, chunk_size=2000,num_qa_per_section=2,json_example_filename="json_example_fn.txt"):
        
        self.assign_vars(file_content,json_example_filename,quiz_examples_filename)
        self.generate_chunks(chunk_size)

        counter=0
        if(len(self.file_content_chunked_sections_list)>0):
            for chunk in self.file_content_chunked_sections_list:
                if(counter<=1):
                    chunk_text=str(chunk).encode("utf-8")

                    #print(f"Generate Q&A for file Section Text:{chunk_text}")
                    #logging.info(f"Generate Q&A for file Section Text:{chunk_text}")
                    qa_section_response_list = self.generate_qa(chunk_text, num_qa_per_section,max_model_tokens)
                    for this_section_list in qa_section_response_list:
                        this_section_list.insert(0,chunk_text)
                    
                    #logging.info(f"Section Generated Q&A:{qa_section_response_list}")
                    self.all_sections_qa_response_list.append(qa_section_response_list)
        
        formatted_response = "\n\n"
        #print(f"\n\nNumber of sections: {self.all_sections_qa_response_list} that generate {num_qa_per_section} questions/answer:\n\n")
        #logging.info(f"\n\nNumber of sections: {self.all_sections_qa_response_list} that generate {num_qa_per_section} questions/answer:\n\n")
        for section_qa in self.all_sections_qa_response_list:
            for qa in section_qa:
                formatted_response += f"{qa[1]}\n"
                formatted_response += f"{qa[2]}\n\n"
        
        return formatted_response

    def assign_vars(self, file_content, json_example_filename, quiz_examples_filename):
        self.file_content = file_content

        with open(json_example_filename, 'r') as file:
                self.json_example = file.read()

        self.openai_k=os.environ["OPENAIKEY"]
       
        with open(quiz_examples_filename, 'r') as file:
                self.quiz_examples = file.read()
    
    def generate_chunks(self, chunk_size):
        file_full_content = "".join(self.file_content)
        chunked_text_list = self.split_text_into_chunks(file_full_content,chunk_size)
        for i, chunk in enumerate(chunked_text_list):
            ##print(f"Chunk {i + 1}:\n{chunk}\n")
            self.file_content_chunked_sections_list.append(chunk)

    def split_text_into_chunks(self,text, chunk_size=2000):
        tokenizer = tiktoken.get_encoding("cl100k_base")
        tokens = tokenizer.encode(text)
        #chunk tokens
        chunks = [tokens[i:i + chunk_size] for i in range(0, len(tokens), chunk_size)]
        #decode to txt
        chunked_text_list = [tokenizer.decode(chunk) for chunk in chunks]

        return chunked_text_list

    def generate_qa(self, chunk_text, num_questions,max_model_tokens):
        this_conversation = []
        response_list=[]

        model = "gpt-35-turbo"
        if(self.questions_to_date is not None):
            system_message = {"role": "system", "content": f"You generate Questions with the corresponding Answers SPECIFIC TO a text excerpt given to you in this query. YOU DO NOT generate these questions {self.questions_to_date}. You keep both Questions and Answers short. Your response is in JSON format following this format:{self.json_example}."}
            #append examples , request and json format example, exclude questions to date
            request_to_gpt=f"Give me {num_questions} questions with its corresponding answer, BUT NOT for these questions {self.questions_to_date}, relevant specifically for this text: {chunk_text}. Use this as an example if a text excerpt given BUT DO NOT INCLUDE THESE EXAMPLE QUESTIONS in your response because they are an example: {self.quiz_examples}.  Respond only with the Questions and the Answers SPECIFIC to the text excerpt given to you."
        else:
            system_message = {"role": "system", "content": f"You generate Questions with the corresponding Answers SPECIFIC TO a text excerpt given to you in this query. You keep both of these short. Your response is in JSON format following this format:{self.json_example}."}
            request_to_gpt=f"Give me {num_questions} questions with its corresponding answer SPECIFIC TO THIS text excerpt: {chunk_text}. Use this as an example if a text excerpt given BUT DO NOT INCLUDE THESE EXAMPLE QUESTIONS in your response because they are an example: {self.quiz_examples}. Respond only with the Questions and the Answers SPECIFIC to the text excerpt given to you."
        
        this_conversation.append(system_message)
        this_conversation.append({"role": "user", "content": request_to_gpt})

        try:

            client = AzureOpenAI(
                api_key = self.openai_k,
                api_version = "2023-09-15-preview", #"2024-02-01"
                azure_endpoint = os.environ["OPENAIENDPOINT"]
                )

            response = client.chat.completions.create(
                model=model,
                messages=this_conversation,
                temperature=0.0,
                max_tokens=max_model_tokens,
                response_format={ "type": "json_object" }
            )
        
        except Exception as e:
            #print(f"1;31m[WARNING]\033[0mAn OpenAI error occurred:\033[0m ", str(e))
            logging.info(f"1;31m[WARNING]\033[0mAn OpenAI error occurred:\033[0m ", str(e))

        try:
            i = 0
            message_content = response.choices[0].message.content# ['choices'][0]['message']['content']
            data = json.loads(message_content)

            # Iterate over questions and answers
            for _ in range(len(data["quiz"])):
                question = data["quiz"][i]["question"]
                answer = data["quiz"][i]["answer"]
                #print(f"\n\n\n***ROUND {i}: TEXT: {chunk_text} \nQUESTION: {question} \nANSWER {answer}")
                logging.info(f"\n\n\n***ROUND {i}: TEXT: {chunk_text} \n\nQUESTION: {question} \n\nANSWER {answer}")
                i += 1
                if question is None and question in self.questions_to_date:
                    continue
                else:
                    response_list.append([f"Question: " + question, f"Answer: " + answer])
                    self.questions_to_date.append(question)
           
        except Exception as e:
            #print(f"Error Iterating over OpenAI response", str(e))
            logging.info(f"Error Iterating over OpenAI response ", str(e))

        return response_list

class BlobManager:
    def __init__(self):
        self.storage_connection_string = None
        self.blob_container_name = None
        self.blob_name = None
        self.blob_service_client = None
        self.container_client = None
        self.blob_client = None

    def BlobCreationManager(self):
        logging.info("**At top BlobCreationManager")
        self.GetVariableValues()
        self.CreateBlobServiceClient()
        self.CreateContainerClient()
        return self.CreateBlobClient()

    def GetVariableValues(self):
        self.storage_connection_string = os.environ["AzureWebJobsStorage"]
        self.blob_container_name = os.environ["BLOB_CONTAINER_NAME"]
        self.blob_name = os.environ["BLOB_NAME"]
        ##logging.info("**After creating all variables")

    def CreateBlobServiceClient(self):
        self.blob_service_client = BlobServiceClient.from_connection_string(self.storage_connection_string)
        ##logging.info("**After creating blob service client")

    def CreateContainerClient(self):
        self.container_client = self.blob_service_client.get_container_client(self.blob_container_name)
        if not self.container_client.exists():
            self.container_client.create_container()
        ##logging.info("**After creating container %s", self.blob_container_name)

    def CreateBlobClient(self):
        self.blob_client = self.container_client.get_blob_client(self.blob_name)
        if not self.blob_client.exists():
            self.blob_client.upload_blob("")
            logging.info("**Created blob")
        else:
            self.blob_client.upload_blob("", overwrite=True)
            logging.info("**Blob exists, overwriting")

        return self.blob_client
    
    def ReadBlobData(self):
        try:
            blob_data = self.blob_client.download_blob().readall()
            #logging.info("**Data read from blob: %s", blob_data)
            file_output = blob_data.decode('utf-8')
            #file_output = blob_data.decode('utf-8').strip('"')
            #return json.loads(file_output)
            return file_output
        except Exception as e:
            logging.error("**Failed to read data from blob: %s", str(e))
            return "ERROR: Failed to read data from blob"
        
    def AppendDataToBlob(self, data):
        try:
            self.blob_client.upload_blob(data, overwrite=True)
            logging.info("**Data appended to blob: %s", data)
        except Exception as e:
            logging.error("**Failed to append data to blob: %s", str(e))

    def CreateconcurrencyStatus(self, container_name, blob_name):
        #create blob_service_client
        logging.info("**Top CreateconcurrencyStatus")
        self.storage_connection_string = os.environ["AzureWebJobsStorage"]
        logging.info("**After self.storage_connection_string")
        self.CreateBlobServiceClient()
        logging.info("**After self.CreateBlobServiceClient")
        #create container
        logging.info("**Before container_client")
        container_client = self.blob_service_client.get_container_client(container_name)
        if not container_client.exists():
            container_client.create_container()
        #create blob_client
        logging.info("**Before blob_client")
        blob_client = container_client.get_blob_client(blob_name)
        try:
            if not blob_client.exists():
                blob_client.upload_blob("", overwrite=True)
                logging.info(f"**Created blob '{blob_name}' in container '{container_name}'.")
            else:
                logging.info(f"**Blob '{blob_name}' already exists in container '{container_name}'.")
        except Exception as e:
            logging.error(f"**Error checking/creating blob: {e}")
            return

        # List blobs in the specified directory
        logging.info("**Before list blobs")
        directory_path = 'concurrency/quiz-secd-funcapp'
        try:
            blobs = container_client.list_blobs(name_starts_with=directory_path)
            logging.info(f"**Blobs in directory '{directory_path}':")
            for blob in blobs:
                logging.info(f"**Blob: {blob.name}")
        except Exception as e:
            logging.error(f"**Error listing blobs: {e}")