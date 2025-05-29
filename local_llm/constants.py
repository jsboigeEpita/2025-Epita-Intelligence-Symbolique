from enum import Enum

MODEL_FOLDER_PATH = "models"

class ModelEnum(Enum):
    Llama2_7B_Q4 = 0
    Llama3_8B_Q6 = 1
    Qwen3_8B_Q8 = 2
    Qwen3_32B_Q4 = 3
    GemmasutraSmall_4B_Q8 = 4

MODEL_PATHS = {
    ModelEnum.Llama2_7B_Q4.name: f"{MODEL_FOLDER_PATH}/{ModelEnum.Llama2_7B_Q4.name}/model.gguf",
    ModelEnum.Llama3_8B_Q6.name: f"{MODEL_FOLDER_PATH}/{ModelEnum.Llama3_8B_Q6.name}/model.gguf",
    ModelEnum.Qwen3_8B_Q8.name: f"{MODEL_FOLDER_PATH}/{ModelEnum.Qwen3_8B_Q8.name}/model.gguf",
    ModelEnum.Qwen3_32B_Q4.name: f"{MODEL_FOLDER_PATH}/{ModelEnum.Qwen3_32B_Q4.name}/model.gguf",
    ModelEnum.GemmasutraSmall_4B_Q8.name: f"{MODEL_FOLDER_PATH}/{ModelEnum.GemmasutraSmall_4B_Q8.name}/model.gguf",
}