import requests

url = "https://magic-eraser-34780901980.asia-east1.run.app/api/index"
with open("test_input.png", "rb") as f:
    files = {"image": f}
    data = {
        "color_type": "both",
        "fill_method": "inpaint",
        "enhance": "false"
    }
    print("Sending request...")
    response = requests.post(url, files=files, data=data)
    print("Status:", response.status_code)
    if response.status_code != 200:
        print("Error:", response.text)
    else:
        print("Success! Image size:", len(response.content))
