import pandas as pd
import torch
from transformers import CamembertTokenizer, CamembertForSequenceClassification, Trainer
from torch.utils.data import Dataset
import json
from sklearn.metrics import f1_score, accuracy_score
import numpy as np

# 1. Load Data and Metadata
print("Loading data and metadata...")
test_df = pd.read_parquet('./data/french_test_data.parquet')

with open('./data/french_metadata.json', 'r') as f:
    metadata = json.load(f)

num_labels = metadata['num_classes']
label_columns = metadata['fallacy_types']

# 2. Define Custom Dataset (re-using the class from train_camembert.py)
class FallacyDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_len, metadata, num_labels):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_len = max_len
        self.metadata = metadata
        self.num_labels = num_labels

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
            padding='max_length',
            truncation=True,
            return_attention_mask=True,
            return_tensors='pt',
        )

        # Convert raw_labels to a single integer label for single-label classification
        # Ensure raw_labels is treated as an integer
        if isinstance(raw_labels, (np.integer, np.floating)):
            raw_labels = int(raw_labels)

        return {
            'input_ids': encoding['input_ids'].flatten(),
            'attention_mask': encoding['attention_mask'].flatten(),
            'labels': torch.tensor(raw_labels, dtype=torch.long)
        }

# 3. Initialize Tokenizer and Model
print("Loading fine-tuned tokenizer and model...")
tokenizer = CamembertTokenizer.from_pretrained('./fine_tuned_camembert')
model = CamembertForSequenceClassification.from_pretrained('./fine_tuned_camembert', num_labels=num_labels)

# 4. Prepare Test Dataset
MAX_LEN = 128 # Must be the same as during training

test_dataset = FallacyDataset(
    texts=test_df['text'].values,
    labels=test_df['labels'].values,
    tokenizer=tokenizer,
    max_len=MAX_LEN,
    metadata=metadata,
    num_labels=num_labels
)

# 5. Define Metrics (re-using the function from train_camembert.py)
def compute_metrics(p):
    predictions = p.predictions[0] if isinstance(p.predictions, tuple) else p.predictions
    labels = p.label_ids

    y_pred = np.argmax(predictions, axis=1)
    y_true = labels

    f1_micro = f1_score(y_true=y_true, y_pred=y_pred, average='micro')
    f1_macro = f1_score(y_true=y_true, y_pred=y_pred, average='macro')
    accuracy = accuracy_score(y_true=y_true, y_pred=y_pred)
    
    return {
        'f1_micro': f1_micro,
        'f1_macro': f1_macro,
        'accuracy': accuracy,
    }

# 6. Configure Trainer for Evaluation
print("Configuring Trainer for evaluation...")
trainer = Trainer(
    model=model,
    compute_metrics=compute_metrics,
)

# 7. Perform Evaluation
print("Performing evaluation on the test set...")
results = trainer.evaluate(test_dataset)

# 8. Print Results
print("\n" + "="*50)
print("Benchmark Results on Test Set:")
print("="*50)
for key, value in results.items():
    print(f"{key}: {value:.4f}")
print("="*50)
