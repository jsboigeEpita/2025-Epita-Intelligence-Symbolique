import { Link } from "expo-router";
import { StyleSheet, TouchableOpacity } from "react-native";

import { ThemedText } from "@/components/ThemedText";
import { ThemedView } from "@/components/ThemedView";
import { IconSymbol } from "@/components/ui/IconSymbol";

import { useSafeAreaInsets } from "react-native-safe-area-context";

export default function AnalysisScreen() {
  const insets = useSafeAreaInsets();

  return (
    <ThemedView
      style={{
        paddingTop: insets.top,
        flex: 1,
        paddingHorizontal: 16,
      }}
    >
      <ThemedView style={styles.titleContainer}>
        <IconSymbol size={36} name="brain" color="#0a7ea4" />
        <ThemedText type="title">Argumentative Analysis</ThemedText>
      </ThemedView>

      <ThemedText style={styles.description}>
        Use our powerful tools to analyze arguments, validate reasoning, and
        detect fallacies.
      </ThemedText>

      <ThemedView style={styles.cardsContainer}>
        <Link href="/analysis/analyze" asChild>
          <TouchableOpacity style={styles.card}>
            <ThemedView style={styles.cardContent}>
              <IconSymbol
                size={48}
                name="doc.text.magnifyingglass"
                color="#0a7ea4"
              />
              <ThemedView style={{ width: "80%" }}>
                <ThemedText type="subtitle">Full Analysis</ThemedText>
                <ThemedText>Complete analysis of argumentative text</ThemedText>
              </ThemedView>
            </ThemedView>
          </TouchableOpacity>
        </Link>

        <Link href="/analysis/validate" asChild>
          <TouchableOpacity style={styles.card}>
            <ThemedView style={styles.cardContent}>
              <IconSymbol size={48} name="checkmark.shield" color="#0a7ea4" />
              <ThemedView style={{ width: "80%" }}>
                <ThemedText type="subtitle">Validate Arguments</ThemedText>
                <ThemedText>Check logical validity of arguments</ThemedText>
              </ThemedView>
            </ThemedView>
          </TouchableOpacity>
        </Link>

        <Link href="/analysis/fallacies" asChild>
          <TouchableOpacity style={styles.card}>
            <ThemedView style={styles.cardContent}>
              <IconSymbol
                size={48}
                name="exclamationmark.triangle"
                color="#0a7ea4"
              />
              <ThemedView style={{ width: "80%" }}>
                <ThemedText type="subtitle">Detect Fallacies</ThemedText>
                <ThemedText>Identify logical fallacies in reasoning</ThemedText>
              </ThemedView>
            </ThemedView>
          </TouchableOpacity>
        </Link>
        <Link href="/chat" asChild>
          <TouchableOpacity style={styles.card}>
            <ThemedView style={styles.cardContent}>
              <IconSymbol
                size={48}
                name="bubble.left.and.bubble.right"
                color="#0a7ea4"
              />
              <ThemedView style={{ width: "80%" }}>
                <ThemedText type="subtitle">Chat</ThemedText>
                <ThemedText>Chat with your AI assistant</ThemedText>
              </ThemedView>
            </ThemedView>
          </TouchableOpacity>
        </Link>
      </ThemedView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  headerImage: {
    bottom: -90,
    left: 60,
    position: "absolute",
    opacity: 0.7,
  },
  titleContainer: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    marginBottom: 16,
  },
  description: {
    marginBottom: 24,
    fontSize: 16,
  },
  cardsContainer: {
    gap: 16,
  },
  card: {
    borderRadius: 12,
    borderWidth: 1,
    borderColor: "#E0E0E0",
    padding: 16,
  },
  cardContent: {
    flexDirection: "row",
    alignItems: "center",
    gap: 16,
  },
});
