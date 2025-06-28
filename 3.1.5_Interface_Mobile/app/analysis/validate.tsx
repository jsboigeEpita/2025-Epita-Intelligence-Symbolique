import React, { useState } from "react";
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  TextInput,
} from "react-native";

import { ThemedButton } from "@/components/ThemedButton";
import { ThemedText } from "@/components/ThemedText";
import { ThemedView } from "@/components/ThemedView";
import { IconSymbol } from "@/components/ui/IconSymbol";
import { Colors } from "@/constants/Colors";
import { useColorScheme } from "@/hooks/useColorScheme";
import {
  getErrorMessage,
  validateArgument as validateArgumentApi,
  ValidationResponse,
} from "@/services/api";
import { ValidationCard } from "@/components/ui/ValidationCard";

export default function ValidateScreen() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<ValidationResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const colorScheme = useColorScheme();

  const validateArgument = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setResult(null);

    try {
      // Call the API service
      const response = await validateArgumentApi(text);
      setResult(response);
    } catch (error) {
      setError(getErrorMessage(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
    >
      <ScrollView
        style={styles.scrollView}
        contentContainerStyle={styles.contentContainer}
        keyboardShouldPersistTaps="handled"
      >
        <ThemedView style={styles.infoContainer}>
          <IconSymbol
            size={32}
            name="checkmark.shield"
            color={Colors[colorScheme ?? "light"].tint}
          />
          <ThemedText style={styles.infoText}>
            Submit an argument to check its logical validity and structural
            coherence.
          </ThemedText>
        </ThemedView>

        <ThemedView style={styles.inputContainer}>
          <TextInput
            style={[
              styles.textInput,
              { color: Colors[colorScheme ?? "light"].text },
            ]}
            placeholder="Enter argument to validate..."
            placeholderTextColor={Colors[colorScheme ?? "light"].icon}
            multiline
            value={text}
            onChangeText={setText}
          />

          <ThemedButton
            title="Validate"
            onPress={validateArgument}
            disabled={!text.trim()}
            loading={loading}
            textColor={Colors[colorScheme ?? "light"].background}
          />
        </ThemedView>

        {(result || error) && (
          <ThemedView
            style={[
              styles.resultContainer,
              result && result.valid
                ? styles.validResult
                : styles.invalidResult,
            ]}
          >
            <ThemedView
              style={[styles.resultHeader, { backgroundColor: "transparent" }]}
            >
              <IconSymbol
                size={24}
                name={
                  result && result.valid
                    ? "checkmark.circle.fill"
                    : "xmark.circle.fill"
                }
                color={result && result.valid ? "#34C759" : "#FF3B30"}
              />
              <ThemedText type="subtitle" style={styles.resultTitle}>
                {result && result.valid ? "Valid Argument" : "Invalid Argument"}
              </ThemedText>
            </ThemedView>
            {error ? (
              <ThemedText style={styles.resultExplanation}>{error}</ThemedText>
            ) : (
              result && (
                <ValidationCard
                  valid={result.valid}
                  formalization={result.formalization}
                  explanation={result.explanation}
                  execution_time={result.execution_time}
                />
              )
            )}
          </ThemedView>
        )}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollView: {
    flex: 1,
  },
  contentContainer: {
    padding: 16,
    paddingBottom: 40,
  },
  infoContainer: {
    flexDirection: "row",
    alignItems: "center",
    backgroundColor: "rgba(10, 126, 164, 0.1)",
    borderRadius: 8,
    padding: 12,
    marginBottom: 16,
  },
  infoText: {
    marginLeft: 12,
    flex: 1,
  },
  inputContainer: {
    marginBottom: 20,
  },
  textInput: {
    borderWidth: 1,
    borderColor: "#CCCCCC",
    borderRadius: 8,
    padding: 12,
    minHeight: 150,
    textAlignVertical: "top",
    marginBottom: 12,
    fontSize: 16,
  },
  resultContainer: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 16,
  },
  validResult: {
    borderColor: "#34C759",
    backgroundColor: "rgba(52, 199, 89, 0.1)",
  },
  invalidResult: {
    borderColor: "#FF3B30",
    backgroundColor: "rgba(255, 59, 48, 0.1)",
  },
  resultHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },
  resultTitle: {
    marginLeft: 8,
  },
  resultAnalysis: {
    fontWeight: "bold",
    marginBottom: 8,
  },
  resultExplanation: {
    lineHeight: 22,
  },
});
