"""
为解决不同AI模型参数不兼容的问题，添加一个适配器层
这个文件可以被包含在ai_manager.py中，或作为单独的模块
"""

def adapt_model_parameters(model_name, config):
    """
    根据不同模型调整参数，移除不支持的参数
    
    Args:
        model_name (str): 模型名称
        config (dict): 原始配置参数
        
    Returns:
        dict: 适配后的配置参数
    """
    # 深拷贝避免修改原始配置
    import copy
    adapted_config = copy.deepcopy(config)
    
    # OpenAI模型不支持top_k
    if "openai" in model_name:
        if "top_k" in adapted_config:
            adapted_config.pop("top_k")
    
    # Anthropic模型特定处理
    if "anthropic" in model_name:
        if "top_k" in adapted_config:
            adapted_config.pop("top_k")
        # 添加其他Anthropic特定适配...
    
    # DeepSeek模型特定处理
    if "deepseek" in model_name:
        if "top_k" in adapted_config:
            adapted_config.pop("top_k")
        # 添加其他DeepSeek特定适配...
    
    # Vertex AI可能需要特定处理
    if "vertex" in model_name:
        # 添加Vertex特定适配...
        pass
    
    return adapted_config