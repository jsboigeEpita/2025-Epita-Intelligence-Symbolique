import pandas as pd
import json
import os
import argparse
from classify_with_chatgpt import classify_fallacies_with_chatgpt  # Import the function
from sklearn.metrics import accuracy_score, f1_score
import numpy as np


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark ChatGPT's fallacy classification on the test dataset."
    )
    parser.add_argument(
        "--api_key",
        type=str,
        help="Your OpenAI API Key. If not provided, it will try to read from OPENAI_API_KEY environment variable.",
        default=os.environ.get("OPENAI_API_KEY"),
    )
    parser.add_argument(
        "--n_samples",
        type=int,
        default=0,
        help="Number of samples to test from the dataset. Set to 0 to test all samples.",
    )

    args = parser.parse_args()

    if not args.api_key:
        args.api_key = input("Veuillez entrer votre clé API OpenAI: ")

    if not args.api_key:
        print("Erreur: Clé API OpenAI non fournie. Impossible de procéder.")
        return

    print("Loading test data and metadata...")
    test_df = pd.read_parquet("./data/french_test_data.parquet")
    if args.n_samples > 0:
        test_df = test_df.head(args.n_samples)
    with open("./data/french_metadata.json", "r") as f:
        metadata = json.load(f)

    id_to_label = metadata["label_mapping"]  # This maps int (as string) to label name
    # We need a reverse mapping for comparison
    label_to_id = {v: int(k) for k, v in metadata["label_mapping"].items()}

    true_labels = []
    predicted_labels = []

    print(
        f"Starting benchmark for {len(test_df)} samples. This may take a while and incur costs."
    )

    for index, row in test_df.iterrows():
        text = row["text"]
        true_label_id = row["labels"]
        true_fallacy_name = id_to_label[
            str(true_label_id)
        ]  # Get the string name of the true fallacy

        # Call ChatGPT API
        gpt_response = classify_fallacies_with_chatgpt(text, args.api_key)

        predicted_sophism_display = "No fallacy detected"
        if gpt_response.get("fallacies_detected") and gpt_response.get("fallacies"):
            predicted_fallacy_types = [
                f.get("type", "N/A") for f in gpt_response["fallacies"]
            ]
            predicted_sophism_display = ", ".join(predicted_fallacy_types)

        print(
            f"Sample {index+1}: Expected: '{true_fallacy_name}', Predicted: '{predicted_sophism_display}'"
        )

        # Assume no prediction by default
        gpt_predicted_id = -1  # Use -1 for 'no prediction' or 'incorrect/unmatched'

        if gpt_response.get("fallacies_detected") and gpt_response.get("fallacies"):
            # Check if the true fallacy name is among GPT's predictions
            found_match = False
            for fallacy in gpt_response["fallacies"]:
                gpt_fallacy_type = fallacy.get("type", "")
                # Normalize GPT's output to match our labels as much as possible
                # This is a crucial step for fair comparison
                normalized_gpt_fallacy_type = (
                    gpt_fallacy_type.split(" (")[0].strip().lower()
                )  # Take only French part, lowercase
                normalized_true_fallacy_type = (
                    true_fallacy_name.split(" (")[0].strip().lower()
                )

                if normalized_gpt_fallacy_type == normalized_true_fallacy_type:
                    gpt_predicted_id = (
                        true_label_id  # If GPT predicted the correct one, assign its ID
                    )
                    found_match = True
                    break
            if not found_match:
                # If GPT detected fallacies but none matched the true one, we still count it as incorrect
                # We could assign a specific ID for 'incorrectly predicted fallacy' if needed
                pass  # gpt_predicted_id remains -1

        true_labels.append(true_label_id)
        predicted_labels.append(gpt_predicted_id)

        if (index + 1) % 10 == 0:  # Print progress every 10 samples
            print(f"Processed {index + 1}/{len(test_df)} samples.")

    # Filter out samples where GPT made no relevant prediction (-1) for accuracy calculation
    # For accuracy, we only count exact matches. If GPT predicted something else, it's wrong.
    # If GPT predicted nothing, it's also wrong (unless true_label was 'no fallacy', which is not our case)

    # For accuracy, we need to ensure predicted_labels has the same length and valid IDs
    # Let's re-evaluate predicted_labels to be either the true_label_id (correct) or a distinct 'wrong' ID
    correct_predictions = 0
    for i in range(len(true_labels)):
        if true_labels[i] == predicted_labels[i]:
            correct_predictions += 1

    accuracy = correct_predictions / len(true_labels)

    print("\n" + "=" * 50)
    print("ChatGPT Benchmark Results on Test Set:")
    print("=" * 50)
    print(f"Total samples: {len(test_df)}")
    print(f"Accuracy: {accuracy:.4f}")
    print("=" * 50)


if __name__ == "__main__":
    main()
