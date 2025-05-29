from .constants import MODEL_PATHS, ModelEnum
from .utils import get_full_prompt, clean_output
from logging import Logger
from sys import stderr
from llama_cpp import Llama

class LocalLlm():
    __slots__ = "models"
    def __init__(self, models_to_load: list[ModelEnum], max_window_size: int = 512):
        self.models = {}
        for model in models_to_load:
            if model.name in MODEL_PATHS.keys():
                print(f"Loading model {model.name} from {MODEL_PATHS[model.name]}.")
                try:
                    self.models[model.name] = self._load_model(MODEL_PATHS[model.name], max_window_size)
                except Exception as e:
                    print(f"Couldn't load {model.name}:\n{e}", file=stderr)
            else:
                print(f"Invalid model name: {model.name}.", file=stderr)

    def _load_model(self, file_path: str, max_window_size: int):
        return Llama(model_path=file_path, n_ctx = max_window_size, n_threads=6, n_gpu_layers=100, verbose=False)
    
    def _prompt_model(self, model_name: str, prompt: str, max_tokens: int) -> str:
        full_prompt = get_full_prompt(prompt)
        model = self.models[model_name]
        output = model(full_prompt, max_tokens=max_tokens)
        text = output["choices"][0]["text"]
        return clean_output(text)
    
    def __call__(self, model: ModelEnum, prompt: str, max_tokens: int = 300) -> str:
        print(f"Prompting...")
        return self._prompt_model(model.name, prompt, max_tokens)
                 