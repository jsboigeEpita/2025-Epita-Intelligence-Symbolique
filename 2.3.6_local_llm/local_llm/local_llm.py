"""
This file contains the core code of the local_llm package.
"""

from sys import stderr
from tqdm import tqdm
from llama_cpp import Llama
from .constants import MODEL_PATHS, ModelEnum
from .utils import get_full_prompt, clean_output


class LocalLlm:
    """
    Wrapper over the Llama class for managing and using multiple models concurrently.
    """

    __slots__ = ("models",)

    def __init__(self, models_to_load: list[ModelEnum], max_window_size: int = 512):
        self.models = {}
        for model in tqdm(models_to_load):
            if model.name in MODEL_PATHS.keys():
                print(f"Loading model {model.name} from {MODEL_PATHS[model.name]}.")
                try:
                    self.models[model.name] = self._load_model(
                        MODEL_PATHS[model.name], max_window_size
                    )
                except (KeyError, ValueError) as e:
                    print(f"Couldn't load {model.name}:\n{e}", file=stderr)
            else:
                print(f"Invalid model name: {model.name}.", file=stderr)

    def _load_model(self, file_path: str, max_window_size: int):
        return Llama(
            model_path=file_path,
            n_ctx=max_window_size,
            n_threads=6,
            n_gpu_layers=100,
            verbose=False,
        )

    def _prompt_model(
        self, model_name: str, prompt: str, max_tokens: int, use_internal_prompt: bool
    ) -> str:
        full_prompt = prompt
        if use_internal_prompt:
            full_prompt = get_full_prompt(prompt)
        model = self.models[model_name]
        output = model(full_prompt, max_tokens=max_tokens)
        text = output["choices"][0]["text"]
        return clean_output(text)

    def __call__(
        self,
        model: ModelEnum,
        prompt: str,
        max_tokens: int = 300,
        use_internal_prompt: bool = True,
    ) -> str:
        if model.name not in self.models:
            print(
                f"The requested model has not been loaded: {model.name}.", file=stderr
            )
        else:
            print("Prompting...")
            return self._prompt_model(
                model.name, prompt, max_tokens, use_internal_prompt
            )
        return None
