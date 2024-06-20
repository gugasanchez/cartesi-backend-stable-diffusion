from os import environ
import logging
import requests
import json
from PIL import Image
from io import BytesIO
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

# Retrieve the rollup server URL from environment variables
rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")

# Stability AI API key and URL
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY")
if not STABILITY_API_KEY:
    raise ValueError("No API key found. Please set the STABILITY_API_KEY environment variable.")
STABILITY_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"

def generate_image(prompt, model="sd3-large", output_format="jpeg"):
    """
    Generates an image using the Stability AI API.
    :param prompt: The text prompt to generate the image.
    :param model: The model to use for generation (default is "sd3-large").
    :param output_format: The format of the output image (default is "jpeg").
    :return: Path to the saved image if successful, None otherwise.
    """
    headers = {
        "authorization": f"Bearer {STABILITY_API_KEY}",
        "accept": "image/*"
    }
    data = {
        "prompt": prompt,
        "model": model,
        "output_format": output_format
    }
    response = requests.post(STABILITY_API_URL, headers=headers, data=data)

    if response.status_code == 200:
        # Open the image and save it to a file
        image = Image.open(BytesIO(response.content))
        image_path = "/opt/cartesi/dapp/generated_image.jpeg"
        image.save(image_path)
        return image_path
    else:
        logger.error(f"Failed to generate image: {response.status_code}, {response.text}")
        return None

def handle_advance(data):
    """
    Handles the 'advance_state' request. Generates an image based on the prompt provided in the data.
    :param data: JSON string containing the request data.
    :return: "accept" if the image is generated successfully, "reject" otherwise.
    """
    logger.info(f"Received advance request data {data}")
    try:
        input_data = json.loads(data)
        prompt = input_data.get("prompt")
        if prompt:
            image_path = generate_image(prompt)
            if image_path:
                logger.info(f"Image generated and saved at {image_path}")
                return "accept"
            else:
                return "reject"
        else:
            logger.error("No prompt provided")
            return "reject"
    except json.JSONDecodeError as e:
        logger.error(f"Failed to decode JSON: {str(e)}")
        return "reject"

def handle_inspect(data):
    """
    Handles the 'inspect_state' request. Currently, it simply logs the request data.
    :param data: JSON string containing the request data.
    :return: "accept" indicating that the request is handled.
    """
    logger.info(f"Received inspect request data {data}")
    return "accept"

# Map request types to their handlers
handlers = {
    "advance_state": handle_advance,
    "inspect_state": handle_inspect,
}

finish = {"status": "accept"}

while True:
    logger.info("Sending finish")
    response = requests.post(rollup_server + "/finish", json=finish)
    logger.info(f"Received finish status {response.status_code}")
    if response.status_code == 202:
        logger.info("No pending rollup request, trying again")
    else:
        rollup_request = response.json()
        data = rollup_request["data"]
        handler = handlers[rollup_request["request_type"]]
        finish["status"] = handler(rollup_request["data"])
