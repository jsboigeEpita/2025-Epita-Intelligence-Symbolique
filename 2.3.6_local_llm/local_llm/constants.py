"""
Update this file freely in order to add/remove the
models you downloaded so you can use them with
the local_llm package.

Instructions:
- Create your root folder and put it in "MODEL_FOLDER_PATH"
- Create a subfolder for your model and name it as you want, then add it
  in the enum "ModelEnum".
- Put your downloaded model in the subfolder and name the file "model.gguf".
"""

from enum import Enum, auto

#############
# TO MODIFY #
#############

MODEL_FOLDER_PATH = "models"


# pylint: disable=invalid-name
class ModelEnum(Enum):
    """
    Enum containing all the models you want to load.
    """

    TinyLlama1_1B_Q8 = 0
    Llama3_1B_Q8 = auto()
    Llama3_3B_Q6 = auto()
    Llama3_8B_Q6 = auto()
    Qwen2_7B_Q8 = auto()
    Qwen3_14B_Q5 = auto()
    MistralNemo_8B_Q8 = auto()
    Phi2_2B_Q8 = auto()
    Phi4_3B_Q4 = auto()


# pylint: enable=invalid-name

#############
#    END    #
#############

MODEL_PATHS = {
    entry.name: f"{MODEL_FOLDER_PATH}/{entry.name}/model.gguf" for entry in ModelEnum
}
