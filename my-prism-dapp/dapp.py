from os import environ
import logging
import requests
import json
import base64

logging.basicConfig(level="INFO")
logger = logging.getLogger(__name__)

rollup_server = environ["ROLLUP_HTTP_SERVER_URL"]
logger.info(f"HTTP rollup_server url is {rollup_server}")

# Stability AI API URL and API key
STABILITY_API_URL = "https://api.stability.ai/v2beta/stable-image/generate/sd3"
STABILITY_API_KEY = environ["STABILITY_API_KEY"]

# Ensure that both environment variables are set
if not rollup_server:
    raise EnvironmentError("ROLLUP_HTTP_SERVER_URL environment variable not set")
if not STABILITY_API_KEY:
    raise EnvironmentError("STABILITY_API_KEY environment variable not set")

def generate_image(prompt):
    response = requests.post(
        STABILITY_API_URL,
        headers={
            "authorization": f"Bearer {STABILITY_API_KEY}",
            "accept": "application/json"
        },
        files={"none": ''},
        data={
            "prompt": prompt,
        },
    )

    if response.status_code == 200:
        response_data = response.json()
        image_base64 = response_data.get("image")
        if image_base64:
            return image_base64
        else:
            logger.error("No image returned in the response")
            return None
    else:
        logger.error(f"Failed to generate image: {response.status_code}, {response.text}")
        return None

def handle_advance(data):
    logger.info(f"Received advance request data {data}")

    # Decode hex payload to string
    payload_hex = data["payload"]
    payload_bytes = bytes.fromhex(payload_hex[2:])  # Remove '0x' prefix and convert to bytes
    prompt = payload_bytes.decode('utf-8')
    logger.info(f"Decoded prompt: {prompt}")

    # Generate image
    image_base64 = generate_image(prompt)
    if image_base64:
        # image_path = "/opt/cartesi/dapp/generated_image.txt"
        # with open(image_path, "w") as file:
        #     file.write(image_base64)
        # logger.info(f"Image generated and saved at {image_path}")
        return "accept"
    else:
        return "reject"


def handle_inspect(data):
    logger.info(f"Received inspect request data {data}")
    return "accept"


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
