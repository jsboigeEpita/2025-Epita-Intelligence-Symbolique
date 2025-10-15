import pandas as pd
import torch
from sklearn.model_selection import train_test_split
from transformers import (
    CamembertTokenizer,
    CamembertForSequenceClassification,
    Trainer,
    TrainingArguments,
)
from torch.utils.data import Dataset
import json
from sklearn.metrics import f1_score, roc_auc_score, accuracy_score
import numpy as np

# 1. Load Data and Metadata
print("Loading data and metadata...")
train_df = pd.read_parquet("./data/french_train_data.parquet")
val_df = pd.read_parquet("./data/french_val_data.parquet")

with open("./data/french_metadata.json", "r") as f:
    metadata = json.load(f)

num_labels = metadata["num_classes"]
label_columns = metadata["fallacy_types"]


# 2. Define Custom Dataset
class FallacyDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = str(self.texts[idx])
        raw_labels = self.labels[idx]

        encoding = self.tokenizer.encode_plus(
            text,
            add_special_tokens=True,
            max_length=self.max_len,
            return_token_type_ids=False,
            padding="max_length",
            truncation=True,
            return_attention_mask=True,
            return_tensors="pt",
        )

        labels_list = []
        if isinstance(raw_labels, str):
            try:
                # Attempt to parse as a JSON list (e.g., "['label1', 'label2']")
                labels_list = json.loads(raw_labels.replace("'", '"'))
            except json.JSONDecodeError:
                # If not a JSON list, assume it's a single label string
                labels_list = [raw_labels]
        elif isinstance(raw_labels, (int, float, np.integer, np.floating)):
            # If it's a numerical label, convert it to its corresponding string label
            label_key = str(int(raw_labels))
            if label_key in metadata["label_mapping"]:
                labels_list = [metadata["label_mapping"][label_key]]
            else:
                labels_list = []
        elif isinstance(raw_labels, list):
            # If it's already a list, use it directly
            labels_list = raw_labels
        else:
            # Fallback for any other unexpected types, treat as empty list
            labels_list = []

        multi_hot_labels = [0] * num_labels
        for label in labels_list:
            if label in metadata["reverse_label_mapping"]:
                idx = metadata["reverse_label_mapping"][label]
                multi_hot_labels[idx] = 1

        return {
            "input_ids": encoding["input_ids"].flatten(),
            "attention_mask": encoding["attention_mask"].flatten(),
            "labels": torch.tensor(
                raw_labels, dtype=torch.long
            ),  # Change to long for single-label
        }


# 3. Initialize Tokenizer and Model
print("Initializing tokenizer and model...")
tokenizer = CamembertTokenizer.from_pretrained("camembert/camembert-large")
model = CamembertForSequenceClassification.from_pretrained(
    "camembert/camembert-large", num_labels=num_labels
)

# 4. Prepare Datasets
MAX_LEN = 128  # You might need to adjust this based on your data and GPU memory

train_dataset = FallacyDataset(
    texts=train_df["text"].values,
    labels=train_df["labels"].values,
    tokenizer=tokenizer,
    max_len=MAX_LEN,
)

val_dataset = FallacyDataset(
    texts=val_df["text"].values,
    labels=val_df["labels"].values,
    tokenizer=tokenizer,
    max_len=MAX_LEN,
)


# 5. Define Metrics
def compute_metrics(p):
    predictions = (
        p.predictions[0] if isinstance(p.predictions, tuple) else p.predictions
    )
    labels = p.label_ids

    y_pred = np.argmax(predictions, axis=1)
    y_true = labels

    f1_micro = f1_score(y_true=y_true, y_pred=y_pred, average="micro")
    f1_macro = f1_score(y_true=y_true, y_pred=y_pred, average="macro")
    accuracy = accuracy_score(y_true=y_true, y_pred=y_pred)

    return {
        "f1_micro": f1_micro,
        "f1_macro": f1_macro,
        "accuracy": accuracy,
    }


# 6. Configure Training Arguments
print("Configuring training arguments...")
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=40,
    per_device_train_batch_size=4,
    per_device_eval_batch_size=4,
    warmup_steps=500,
    weight_decay=0.01,
    logging_dir="./logs",
    logging_steps=10,
    eval_strategy="epoch",
    save_strategy="epoch",
    load_best_model_at_end=True,
    metric_for_best_model="f1_macro",
    greater_is_better=True,
    gradient_accumulation_steps=8,
)

# 7. Initialize Trainer and Start Training
print("Initializing Trainer and starting training...")
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=train_dataset,
    eval_dataset=val_dataset,
    compute_metrics=compute_metrics,
)

trainer.train()

# 8. Save the fine-tuned model
print("Saving fine-tuned model...")
model.save_pretrained("./fine_tuned_camembert")
tokenizer.save_pretrained("./fine_tuned_camembert")
print("Training complete and model saved to ./fine_tuned_camembert")
