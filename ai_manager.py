from dotenv import load_dotenv
import os
import logging
import litellm
from typing import Dict, Any, List
import json
from openai import OpenAI
import asyncio

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_manager")

# 加载环境变量
load_dotenv()

# 模型配置常量
DEFAULT_MODEL_CONFIG = {
    "temperature": 0.95,
    "max_tokens": 100,  # litellm使用max_tokens而非max_output_tokens
    "top_p": 0.9,
    "top_k": 40
}

DEFAULT_SYSTEM_PROMPT = "You are very 'brat' VTuber who interacts with your audience and provides rebellious and interesting responses. You can use Chinese, Japanese, and English. Limit your dialogue into 60 words or less."


class AIManager:

    def __init__(self):
        # 从环境变量设置API密钥
        self.api_keys = {
            "openai": os.getenv("OPENAI_API_KEY"),
            "anthropic": os.getenv("ANTHROPIC_API_KEY"),
            "gemini": os.getenv("GEMINI_API_KEY"),
            "vertex": os.getenv("VERTEX_API_KEY"),
            "deepseek": os.getenv("DEEPSEEK_API_KEY")
        }
        
        # DeepSeek的特殊配置
        self.deepseek_base_url = os.getenv("DEEPSEEK_BASE_URL", os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com"))
        
        # Vertex AI服务账号配置
        self.vertex_credentials_path = os.getenv("VERTEX_CREDENTIALS_PATH", os.getenv("VERTEX_CREDENTIALS_FILE"))
        self.vertex_credentials_json = os.getenv("VERTEX_CREDENTIALS_JSON")
        self.vertex_project = os.getenv("VERTEX_PROJECT", "")
        self.vertex_location = os.getenv("VERTEX_LOCATION", "us-central1")
        
        # 自定义客户端
        self.custom_clients = {}
        if self.api_keys["deepseek"]:
            self.custom_clients["deepseek"] = OpenAI(
                api_key=self.api_keys["deepseek"],
                base_url=self.deepseek_base_url
            )
        
        # 设置默认litellm模型
        self.default_model = os.getenv("DEFAULT_MODEL", "gemini/gemini-1.5-flash")
        
        # 配置litellm
        self._configure_litellm()
        
        # 设置模型映射(模型名称 -> litellm模型标识符)
        self.model_map = {
            # Google Gemini API (直接)
            "gemini": "gemini/gemini-1.5-flash",
            "gemini-pro": "gemini/gemini-pro",
            
            # OpenAI
            "gpt-4": "openai/gpt-4",
            "gpt-3.5-turbo": "openai/gpt-3.5-turbo",
            "openai": "openai/gpt-3.5-turbo",  # 为了支持直接使用"openai"作为模型名称
            
            # 更新 Anthropic 模型名称
            "claude-3-opus": "anthropic/claude-3-opus-20240229",
            "claude-3-sonnet": "anthropic/claude-3-sonnet-20240229",
            "claude-3-haiku": "anthropic/claude-3-haiku-20240307",
    
            # 可以额外添加这些别名
            "claude-3": "anthropic/claude-3-sonnet-20240229",  # 默认使用 sonnet
            "claude": "anthropic/claude-3-haiku-20240307",
            
            # Google Vertex AI Gemini
            "vertex-gemini-pro": "vertex_ai/gemini-pro",
            "vertex-gemini-1.5-pro": "vertex_ai/gemini-1.5-pro",
            "vertex-gemini-1.5-flash": "vertex_ai/gemini-1.5-flash",
            
            # DeepSeek
            "deepseek-chat": "deepseek/deepseek-chat",
            "deepseek-coder": "deepseek/deepseek-coder"
        }
        
        # 设置视觉模型映射
        self.vision_model_map = {
            # Google Gemini API (直接)
            "gemini": "gemini/gemini-1.5-flash",
            
            # OpenAI
            "gpt-4": "openai/gpt-4o",
            "openai": "openai/gpt-4o",  # 为了支持直接使用"openai"作为模型名称
            
            # Anthropic
            "claude-3-opus": "anthropic/claude-3-opus-20240229",
            "claude-3-sonnet": "anthropic/claude-3-sonnet-20240229",
            
            # Google Vertex AI Gemini
            "vertex-gemini-pro-vision": "vertex_ai/gemini-pro-vision",
            "vertex-gemini-1.5-pro": "vertex_ai/gemini-1.5-pro"
        }
        
        logger.info("AIManager初始化完成")

    def _configure_litellm(self):
        """配置litellm的API密钥和设置"""
        # 设置API密钥
        if self.api_keys["openai"]:
            os.environ["OPENAI_API_KEY"] = self.api_keys["openai"]
            
        if self.api_keys["anthropic"]:
            os.environ["ANTHROPIC_API_KEY"] = self.api_keys["anthropic"]
            
        if self.api_keys["gemini"]:
            os.environ["GEMINI_API_KEY"] = self.api_keys["gemini"]
        
        # 处理Vertex AI认证
        vertex_creds_available = False
        vertex_project_id = None
        
        # 检查是否有API密钥
        has_vertex_api_key = bool(self.api_keys["vertex"])
        
        # 检查是否提供了服务账号JSON文件
        has_credentials_file = self.vertex_credentials_path and os.path.exists(self.vertex_credentials_path)
        
        # 检查是否提供了服务账号JSON字符串
        has_credentials_json = bool(self.vertex_credentials_json)
        
        if has_vertex_api_key or has_credentials_file or has_credentials_json:
            # 1. 处理直接提供的JSON字符串
            if has_credentials_json:
                try:
                    # 解析JSON字符串
                    creds_data = json.loads(self.vertex_credentials_json)
                    
                    # 创建临时凭据文件
                    import tempfile
                    temp_creds_file = tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False)
                    json.dump(creds_data, temp_creds_file)
                    temp_creds_file.flush()
                    temp_creds_file.close()
                    
                    # 设置环境变量指向临时文件
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = temp_creds_file.name
                    vertex_creds_available = True
                    vertex_project_id = creds_data.get('project_id')
                    logger.info(f"已从环境变量VERTEX_CREDENTIALS_JSON读取凭据，项目ID: {vertex_project_id}")
                except json.JSONDecodeError:
                    logger.error("VERTEX_CREDENTIALS_JSON环境变量包含无效的JSON")
                except Exception as e:
                    logger.error(f"处理VERTEX_CREDENTIALS_JSON时出错: {str(e)}")
            
            # 2. 处理服务账号JSON文件
            elif has_credentials_file:
                try:
                    # 设置服务账号凭据环境变量
                    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.abspath(self.vertex_credentials_path)
                    
                    # 尝试从服务账号JSON提取项目ID
                    with open(self.vertex_credentials_path, 'r') as f:
                        creds_data = json.load(f)
                        vertex_project_id = creds_data.get('project_id')
                    
                    vertex_creds_available = True
                    logger.info(f"已使用凭据文件进行Vertex AI认证: {self.vertex_credentials_path}")
                except Exception as e:
                    logger.error(f"读取Vertex凭据文件失败: {str(e)}")
            
            # 3. 简单API密钥也算有效认证
            elif has_vertex_api_key:
                vertex_creds_available = True
                logger.info("已使用API密钥进行Vertex AI认证")
            
            # 如果有有效认证，继续配置Vertex AI
            if vertex_creds_available:
                # 设置项目ID - 优先使用从凭据中提取的
                if vertex_project_id:
                    litellm.vertex_project = vertex_project_id
                    self.vertex_project = vertex_project_id  # 更新实例变量
                else:
                    litellm.vertex_project = self.vertex_project
                
                # 设置位置
                litellm.vertex_location = self.vertex_location
                logger.info(f"Vertex AI配置完成 - 项目: {litellm.vertex_project}, 位置: {litellm.vertex_location}")
            else:
                logger.warning("Vertex AI未配置有效认证")
                
        # 配置DeepSeek（通过自定义OpenAI客户端）
        if self.api_keys["deepseek"]:
            # 这里移除 add_provider 调用，改为直接记录日志
            logger.info(f"已配置DeepSeek API (base_url: {self.deepseek_base_url})")
        
        # 其他litellm配置
        litellm.set_verbose = False  # 调试时设为True
        
        logger.info("LiteLLM配置完成")
        
        # 记录可用的提供商（不显示实际密钥）
        available_providers = [provider for provider, key in self.api_keys.items() if key]
        logger.info(f"可用的API提供商: {', '.join(available_providers)}")
        
        # API可用性检测
        print("\n=== API可用性检测 ===")
        for provider, key in self.api_keys.items():
            if key:
                print(f"✅ {provider.upper()} API密钥已配置")
            else:
                print(f"❌ {provider.upper()} API密钥未配置")
        
        # 特别检查Vertex AI
        if self.vertex_credentials_path and os.path.exists(self.vertex_credentials_path):
            print(f"✅ Vertex AI服务账号文件已配置: {self.vertex_credentials_path}")
            print(f"   项目: {self.vertex_project}")
            print(f"   位置: {self.vertex_location}")
        elif self.vertex_credentials_json:
            try:
                # 尝试解析JSON以验证其有效性
                json.loads(self.vertex_credentials_json)
                print(f"✅ Vertex AI服务账号JSON已配置")
                print(f"   项目: {self.vertex_project}")
                print(f"   位置: {self.vertex_location}")
            except json.JSONDecodeError:
                print(f"❌ Vertex AI服务账号JSON格式无效")
        else:
            print(f"❌ Vertex AI服务账号未配置")

    def get_available_models(self) -> Dict[str, List[str]]:
        """返回按提供商分组的可用模型字典"""
        available_models = {
            "text": [],
            "vision": []
        }
        
        # 根据API密钥检查哪些模型可用
        if self.api_keys["openai"]:
            available_models["text"].extend(["gpt-4", "gpt-3.5-turbo", "openai"])
            available_models["vision"].append("gpt-4")
            available_models["vision"].append("openai")
            
        if self.api_keys["anthropic"]:
            available_models["text"].extend(["claude-3-opus", "claude-3-sonnet", "claude-3-haiku"])
            available_models["vision"].extend(["claude-3-opus", "claude-3-sonnet"])
            
        if self.api_keys["gemini"]:
            available_models["text"].extend(["gemini", "gemini-pro"])
            available_models["vision"].append("gemini")
            
        # 检查Vertex AI认证
        vertex_available = self.api_keys["vertex"] or (self.vertex_credentials_path and os.path.exists(self.vertex_credentials_path)) or self.vertex_credentials_json
        if vertex_available:
            available_models["text"].extend([
                "vertex-gemini-pro",
                "vertex-gemini-1.5-pro",
                "vertex-gemini-1.5-flash"
            ])
            available_models["vision"].extend([
                "vertex-gemini-pro-vision",
                "vertex-gemini-1.5-pro"
            ])
            
        # 添加DeepSeek模型
        if self.api_keys["deepseek"]:
            available_models["text"].extend(["deepseek-chat", "deepseek-coder"])
            # DeepSeek目前没有视觉模型，所以不添加到vision列表
            
        return available_models

    async def generate_text_response(self,
                               user_input: str,
                               system_prompt: str=DEFAULT_SYSTEM_PROMPT,
                               model_name: str=None,
                               config: Dict[str, Any]=None) -> str:
        """使用指定模型生成文本响应"""
        try:
            # 如果未指定模型，使用默认模型
            if not model_name:
                model_name = self.default_model
            else:
                # 将友好名称转换为litellm格式
                model_name = self.model_map.get(model_name, model_name)
            
            # 如果未提供配置，使用默认配置
            if not config:
                config = DEFAULT_MODEL_CONFIG.copy()
                
            # 调整配置键以适应litellm
            litellm_config = config.copy()
            if "max_output_tokens" in litellm_config:
                litellm_config["max_tokens"] = litellm_config.pop("max_output_tokens")
            
            # 根据模型类型调整参数，移除不支持的参数
            if "openai" in model_name:
                # OpenAI不支持top_k参数
                if "top_k" in litellm_config:
                    litellm_config.pop("top_k")
                    
            if "anthropic" in model_name:
                # Anthropic不支持top_k参数
                if "top_k" in litellm_config:
                    litellm_config.pop("top_k")
            
            if "deepseek" in model_name and "top_k" in litellm_config:
                # DeepSeek不支持top_k参数
                litellm_config.pop("top_k")
                
            # 根据模型类型准备消息
            messages = []
            
            # 特殊处理DeepSeek模型（使用自定义OpenAI客户端）
            if "deepseek" in model_name and "deepseek" in self.custom_clients:
                logger.info(f"使用DeepSeek自定义客户端生成响应: {model_name}")
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
                
                # 提取DeepSeek的实际模型名称
                deepseek_model = model_name.split("/")[-1] if "/" in model_name else "deepseek-chat"
                
                # 确保移除DeepSeek不支持的参数
                deepseek_config = {k: v for k, v in litellm_config.items() 
                                if k in ["temperature", "max_tokens", "top_p"]}
                
                response = await asyncio.to_thread(
                    self.custom_clients["deepseek"].chat.completions.create,
                    model=deepseek_model,
                    messages=messages,
                    **deepseek_config
                )
                
                if response and hasattr(response, "choices") and len(response.choices) > 0:
                    return response.choices[0].message.content.strip()
                return "⚠️ DeepSeek 没有返回文本"
            
            # 正常处理其他模型
            # 根据模型类型准备消息
            if "anthropic" in model_name or "openai" in model_name:
                messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_input})
            elif "gemini" in model_name or "vertex" in model_name:
                # 对于Gemini，我们将系统提示和用户输入结合起来
                messages.append({"role": "user", "content": f"{system_prompt}\n\n{user_input}"})
            else:
                # 默认情况 
                messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_input})
            
            # 生成响应
            logger.info(f"使用模型生成响应: {model_name}")
            response = await litellm.acompletion(
                model=model_name,
                messages=messages,
                **litellm_config
            )
            
            # 从响应中提取文本
            if response and "choices" in response and len(response["choices"]) > 0:
                return response["choices"][0]["message"]["content"].strip()
            else:
                return "⚠️ AI 没有返回文本"
                
        except Exception as e:
            logger.error(f"生成文本响应时出错: {str(e)}")
            return f"⚠️ 生成响应时出错: {str(e)}"

    async def process_image(self,
                     image_data: str,
                     prompt: str="Describe what you see in this image",
                     model_name: str=None,
                     config: Dict[str, Any]=None) -> Dict[str, Any]:
        """使用视觉模型处理图像"""
        try:
            # 如果未指定视觉模型，使用默认的Gemini
            if not model_name:
                model_name = "gemini"  # 默认使用Gemini处理视觉
                
            # 将友好名称转换为litellm格式
            litellm_model = self.vision_model_map.get(model_name, self.vision_model_map["gemini"])
            
            # 如果未提供配置，使用默认配置
            if not config:
                config = DEFAULT_MODEL_CONFIG.copy()
                
            # 调整配置键以适应litellm
            litellm_config = config.copy()
            if "max_output_tokens" in litellm_config:
                litellm_config["max_tokens"] = litellm_config.pop("max_output_tokens")
            
            # 根据模型类型调整参数，移除不支持的参数
            if "openai" in litellm_model:
                # OpenAI不支持top_k参数
                if "top_k" in litellm_config:
                    litellm_config.pop("top_k")

            if "anthropic" in litellm_model:
                # Anthropic不支持top_k参数
                if "top_k" in litellm_config:
                    litellm_config.pop("top_k")
            
            # 确保图像数据格式正确
            if image_data.startswith('data:image'):
                # 如果包含数据URL前缀，提取base64数据
                image_base64 = image_data.split(',')[1]
            else:
                # 假设它已经是base64
                image_base64 = image_data
            
            # 根据模型提供商格式化图像内容
            if "openai" in litellm_model:
                # OpenAI格式
                image_content = {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{image_base64}"
                    }
                }
            elif "anthropic" in litellm_model:
                # Claude格式
                image_content = {
        "type": "image_url",
        "image_url": {
            "url": f"data:image/jpeg;base64,{image_base64}"
        }
                }
            else:
                # 默认格式(Gemini)
                image_content = {
                    "type": "image_url",
                    "image_url": f"data:image/jpeg;base64,{image_base64}"
                }
            
            # 准备带有图像的消息
            if "anthropic" in litellm_model:
                messages = [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        image_content
                    ]}
                ]
            elif "openai" in litellm_model:
                messages = [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        image_content
                    ]}
                ]
            else:
                # Gemini和其他
                messages = [
                    {"role": "user", "content": [
                        {"type": "text", "text": prompt},
                        image_content
                    ]}
                ]
            
            # 生成响应
            logger.info(f"使用模型处理图像: {litellm_model}")
            response = await litellm.acompletion(
                model=litellm_model,
                messages=messages,
                **litellm_config
            )
            
            # 从响应中提取文本
            if response and "choices" in response and len(response["choices"]) > 0:
                vision_text = response["choices"][0]["message"]["content"].strip()
                return {"vision_response": vision_text}
            else:
                return {"vision_response": "⚠️ 视觉模块无描述返回"}
                
        except Exception as e:
            logger.error(f"处理图像时出错: {str(e)}")
            return {"vision_response": f"⚠️ 处理图像时出错: {str(e)}"}


# 创建单例实例
ai_manager = AIManager()
