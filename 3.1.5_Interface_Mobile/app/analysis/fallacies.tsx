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
  detectFallacies as detectFallaciesApi,
  getErrorMessage,
  FallacyResponse,
  FallacyInstance,
} from "@/services/api";
import { FallacyCard } from "@/components/ui/FallacyCard";

export default function FallaciesScreen() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<FallacyResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const colorScheme = useColorScheme();

  const detectFallacies = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);

    try {
      // Call the API service
      const response = await detectFallaciesApi(text);
      setResult(response);
    } catch (err) {
      setError(getErrorMessage(err));
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
            name="exclamationmark.triangle"
            color={Colors[colorScheme ?? "light"].tint}
          />
          <ThemedText style={styles.infoText}>
            Submit a text to identify logical fallacies and reasoning errors in
            the argument.
          </ThemedText>
        </ThemedView>

        <ThemedView>
          <TextInput
            style={[
              styles.textInput,
              { color: Colors[colorScheme ?? "light"].text },
            ]}
            placeholder="Enter text to check for fallacies..."
            placeholderTextColor={Colors[colorScheme ?? "light"].icon}
            multiline
            value={text}
            onChangeText={setText}
          />
        </ThemedView>
        <ThemedButton
          title="Detect Fallacies"
          onPress={detectFallacies}
          disabled={!text.trim()}
          loading={loading}
          textColor={Colors[colorScheme ?? "light"].background}
          style={{
            marginBottom: 20,
          }}
        />

        {(result || error) && (
          <ThemedView
            style={[
              styles.resultsContainer,
              error ? styles.errorResult : styles.successResult,
            ]}
          >
            <ThemedView
              style={[styles.resultHeader, { backgroundColor: "transparent" }]}
            >
              <IconSymbol
                size={24}
                name={
                  error
                    ? "xmark.circle.fill"
                    : result && result.fallacies && result.fallacies.length > 0
                    ? "exclamationmark.triangle.fill"
                    : "checkmark.circle.fill"
                }
                color={
                  error
                    ? "#FF3B30"
                    : result && result.fallacies && result.fallacies.length > 0
                    ? "#FF9500"
                    : "#34C759"
                }
              />
              <ThemedText type="subtitle" style={styles.resultsTitle}>
                {error
                  ? "Detection Error"
                  : result && result.fallacies && result.fallacies.length === 0
                  ? "No fallacies detected"
                  : `${result?.fallacies?.length || 0} Fallacies Detected`}
              </ThemedText>
            </ThemedView>

            {error ? (
              <>
                <ThemedText style={styles.errorText}>Error: {error}</ThemedText>
                <ThemedText style={styles.errorExplanation}>
                  Please try again with a different text or check your
                  connection.
                </ThemedText>
              </>
            ) : result && result.fallacies && result.fallacies.length === 0 ? (
              <ThemedView style={styles.noFallaciesContainer}>
                <ThemedText style={styles.noFallaciesText}>
                  No logical fallacies were detected in your text. Good job!
                </ThemedText>
              </ThemedView>
            ) : (
              <>
                <ThemedText style={styles.resultAnalysis}>
                  <ThemedText type="defaultSemiBold">Analyzed text:</ThemedText>
                </ThemedText>
                <ThemedText style={styles.argumentItem}>
                  {result?.text}
                </ThemedText>
                {result?.fallacies?.map(
                  (fallacy: FallacyInstance, idx: number) => (
                    <FallacyCard key={idx} {...fallacy} text={result.text} />
                  )
                )}
                <ThemedText style={styles.executionTime}>
                  <ThemedText type="defaultSemiBold">
                    Execution time:
                  </ThemedText>{" "}
                  {result?.execution_time?.toFixed(2)}s
                </ThemedText>
              </>
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
  resultsContainer: {
    borderWidth: 1,
    borderRadius: 8,
    padding: 16,
  },
  successResult: {
    borderColor: "#34C759",
    backgroundColor: "rgba(52, 199, 89, 0.1)",
  },
  errorResult: {
    borderColor: "#FF3B30",
    backgroundColor: "rgba(255, 59, 48, 0.1)",
  },
  resultHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 12,
  },
  resultsTitle: {
    marginLeft: 8,
  },
  noFallaciesContainer: {
    alignItems: "center",
    padding: 16,
  },
  noFallaciesText: {
    textAlign: "center",
    marginTop: 12,
  },
  resultAnalysis: {
    marginBottom: 12,
  },
  argumentItem: {
    marginBottom: 12,
  },
  executionTime: {
    marginTop: 12,
  },
  errorText: {
    fontWeight: "bold",
    marginBottom: 8,
  },
  errorExplanation: {
    lineHeight: 22,
  },
});
