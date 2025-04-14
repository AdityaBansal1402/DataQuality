import json
import os
from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama.llms import OllamaLLM
from docx import Document
import pdfplumber
import pytesseract
from PIL import Image
import google.generativeai as genai
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
import logging

# genai.configure(api_key='')
genai.configure(api_key='')

class GemBot():

    model = genai.GenerativeModel("gemini-1.5-flash")
    
    def __init__(self):
        self.conversation = []

    def system(self, text):
        self.conversation = []
        self.conversation.append({'role': 'system', 'content': text})

    def sys_up(self):
        self.conversation.append(("human", "{user_input}"))

    def doc(self, path):
        try:
            ext = os.path.splitext(path)[1].lower()
            if ext == '.txt':
                with open(path, 'r') as f:
                    text = f.read()
            elif ext == '.json':
                with open(path, 'r') as f:
                    data = json.load(f)
                    text = json.dumps(data, indent=4)
            elif ext == '.docx':
                doc = Document(path)
                text = '\n'.join([para.text for para in doc.paragraphs])
            elif ext == '.pdf':
                doc = pdfplumber.open(path)
                text = ""
                for page in doc.pages:
                    text += page.extract_text()
            elif ext in ['.jpg', '.png', '.jpeg']:
                extracted_text = self.extract_text_from_image(path)
                print("Extracted Text:", extracted_text)
            else:
                print(f"Error: Unsupported file type '{ext}'")
                return
            self.conversation.append({'role': "system", 'content': f"This is the PCF statement that you need to review:\n{text}"})
            # self.sys_up()
        except FileNotFoundError:
            print(f"Error: The file '{path}' was not found.")
        except Exception as e:
            print(f"Error: {e}")

    def extract_text_from_image(self, image_path):
        # Open the image using PIL
        img = Image.open(image_path)
        text = pytesseract.image_to_string(img)
        print(text, '\n\n')
        self.conversation.append(("human", f"Here is the extracted text:\n{text}"))
        self.sys_up()
    
    def gen_out(self, text):
        self.conversation.append({'role': 'user', 'content': text})
        conv = self.build_conversation()
        response = self.model.generate_content(conv)
        output = response.text  # Adjust this based on Gemini's response structure
        # print(output, '\n')
        self.conversation.append({'role': 'assistant', 'content': output})
        # self.sys_up()
        return output

    def build_conversation(self):
        return "\n\n".join(f"{msg['role'].capitalize()}: {msg['content']}" for msg in self.conversation)


    def get_conv(self):
        for dialogue in self.conversation:
            print(dialogue)

    def load_schema(self, path):
        try:
            with open(path, 'r') as f:
                schema = f.read()
            
            self.conversation.append(("system", "You will now receive the database schema that you need to strictly follow."))
            self.conversation.append(("human", f"Here is the database schema:\n{schema}"))
            
            self.conversation.append(("human", "Based on the schema provided, please ensure to structure your outputs (like JSON) accordingly when I provide the PCF statements."))
            
            self.sys_up()
        except FileNotFoundError:
            print(f"Error: The schema file '{path}' was not found.")
        except Exception as e:
            print(f"Error: {e}")

cb1 = GemBot()

sys_text = '''
You are an AI assistant that will read through given datasets and suggest the user with any business rules that might apply the dataset. for eg:
"Valid Age": lambda row: 0 <= pd.to_numeric(row["Age"], errors="coerce") <= 120 if "Age" in row else True,
"Salary Non-negative": lambda row: pd.to_numeric(row["Salary"], errors="coerce") >= 0 if "Salary" in row else True,

You only need to output these rules in given format, do not provide any extra code or helper functions, just the rules.
'''

cb1.system(sys_text)

with open("synthetic_dirty_data.csv", "r", encoding="utf-8") as f:
    x = f.read()

print(cb1.gen_out(f"{x}. Read this file and generate appropriate business rules."))