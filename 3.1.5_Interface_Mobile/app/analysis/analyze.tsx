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
  AnalysisResponse,
  analyzeText as analyzeTextApi,
  getErrorMessage,
  Argument,
} from "@/services/api";
import { ArgumentCard } from "@/components/ui/ArgumentCard";
import { QualityBadge } from "@/components/ui/QualityBadge";

export default function AnalyzeScreen() {
  const [text, setText] = useState("");
  const [result, setResult] = useState<AnalysisResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const colorScheme = useColorScheme();

  const analyzeText = async () => {
    if (!text.trim()) return;

    setLoading(true);
    setResult(null);
    setError(null);

    try {
      // Call the API service
      const response = await analyzeTextApi(text);
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
            name="doc.text.magnifyingglass"
            color={Colors[colorScheme ?? "light"].tint}
          />
          <ThemedText style={styles.infoText}>
            Enter your argumentative text for a complete analysis of structure,
            claims, and reasoning.
          </ThemedText>
        </ThemedView>

        <ThemedView style={styles.inputContainer}>
          <TextInput
            style={[
              styles.textInput,
              { color: Colors[colorScheme ?? "light"].text },
            ]}
            placeholder="Enter text to analyze..."
            placeholderTextColor={Colors[colorScheme ?? "light"].icon}
            multiline
            value={text}
            onChangeText={setText}
          />

          <ThemedButton
            title="Analyze"
            onPress={analyzeText}
            disabled={!text.trim()}
            loading={loading}
            textColor={Colors[colorScheme ?? "light"].background}
          />
        </ThemedView>

        {(result || error) && (
          <ThemedView
            style={[
              styles.resultContainer,
              error ? styles.errorResult : styles.successResult,
            ]}
          >
            <ThemedView
              style={[styles.resultHeader, { backgroundColor: "transparent" }]}
            >
              <IconSymbol
                size={24}
                name={error ? "xmark.circle.fill" : "checkmark.circle.fill"}
                color={error ? "#FF3B30" : "#34C759"}
              />
              <ThemedText type="subtitle" style={styles.resultTitle}>
                {error ? "Analysis Error" : "Analysis Result"}
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
            ) : result ? (
              <>
                <ThemedText style={styles.resultAnalysis}>
                  <ThemedText type="defaultSemiBold">Analyzed text:</ThemedText>
                </ThemedText>
                <ThemedText style={styles.argumentItem}>
                  {result.text}
                </ThemedText>
                {Object.entries(result.arguments).length > 0 &&
                  result.arguments.map((arg: Argument) => (
                    <ArgumentCard key={arg.id} {...arg} />
                  ))}
                <QualityBadge score={result?.overall_quality} />
              </>
            ) : null}
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
  resultTitle: {
    marginLeft: 8,
  },
  resultAnalysis: {
    marginBottom: 12,
  },
  argumentItem: {
    marginLeft: 16,
    marginBottom: 4,
    lineHeight: 20,
  },
  errorText: {
    fontWeight: "bold",
    marginBottom: 8,
  },
  errorExplanation: {
    lineHeight: 22,
  },
});
