import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("API_KEY")

genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemma-3-12b-it')
response = model.generate_content("What is the capital of France?")

print(response.text)