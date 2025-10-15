"""
Whisper WebUI API Client Test Script
For the doc and test the UI: https://whisper-webui.myia.io/?view=api
"""

from gradio_client import Client, handle_file
from dotenv import load_dotenv
import os

# Load environment variables from ../.env
load_dotenv(os.path.join(os.path.dirname(__file__), "../.env"))

HUGGING_FACE_API_KEY = os.getenv("HUGGING_FACE_API_KEY")
USERNAME = os.getenv("WHISPER_USERNAME")
PASSWORD = os.getenv("WHISPER_PASSWORD")
print(USERNAME, PASSWORD, HUGGING_FACE_API_KEY)

client = Client("https://whisper-webui.myia.io/", auth=(USERNAME, PASSWORD))
result = client.predict(
    youtube_link="https://www.youtube.com/watch?v=n9Gj5QCSsBk",  # Example with Trump speech
    file_format="txt",
    add_timestamp=False,
    progress="large-v3-turbo",
    param_4="english",
    param_5=False,
    param_6=5,
    param_7=-1,
    param_8=0.6,
    param_9="float16",
    param_10=5,
    param_11=1,
    param_12=True,
    param_13=0.5,
    param_14="Hello!!",
    param_15=0,
    param_16=2.4,
    param_17=1,
    param_18=1,
    param_19=0,
    param_20="Hello!!",
    param_21=True,
    param_22="[-1]",
    param_23=1,
    param_24=False,
    param_25="'“¿([{-",
    param_26="'.。,，!！?？:：”)]}、",
    param_27=3,
    param_28=30,
    param_29=3,
    param_30="Hello!!",
    param_31=0.5,
    param_32=1,
    param_33=24,
    param_34=True,
    param_35=False,
    param_36=0.5,
    param_37=250,
    param_38=9999,
    param_39=1000,
    param_40=2000,
    param_41=False,
    param_42="cuda",
    param_43=HUGGING_FACE_API_KEY,
    param_44=True,
    param_45=False,
    param_46="UVR-MDX-NET-Inst_HQ_4",
    param_47="cuda",
    param_48=256,
    param_49=False,
    param_50=True,
    api_name="/transcribe_youtube",
)
print(result)
formatted_result = result[0].split("\n")
for line in formatted_result:
    print(line)
