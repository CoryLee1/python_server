from google import genai
from google.genai import types
from PIL import Image
import io
import base64

class VisionModule:
    def __init__(self, api_key):
        self.client = genai.Client(api_key=api_key)

    def process_image(self, image_data):
        try:
            # 解码 Base64 图像数据为字节流
            image_bytes = base64.b64decode(image_data)
            # 使用 PIL 将字节流转为图像对象
            image = Image.open(io.BytesIO(image_bytes))

            custom_prompt = (
                "You are a male VTuber, Please provide your inner thoughts based on a detailed description of the image that fits the streaming atmosphere then your inner thoughts towards it, limited to 50 words.   "
                "Please provide a detailed description of the image that fits the streaming atmosphere and your inner thoughts towards it, limited to 50 words."
            )

            # 按官方示例，将文本和图像一起放进 contents 列表，并加入配置参数
            response = self.client.models.generate_content(
                model='gemini-2.0-flash',
                contents=[custom_prompt, image],
                ##generation_config=types.GenerationConfig(
                    #max_output_tokens=90,
                    #temperature=0.95,
                    #top_p=0.9,
                    #top_k=40,
                   # stop_sequences=['\n']
                #)
            )

            # 提取并返回描述文本
            description = response.text.strip() if response.text else "AI did not return a description"
            return {"vision_response": description}

        except Exception as e:
            return {"error": f"Error processing image: {str(e)}"}