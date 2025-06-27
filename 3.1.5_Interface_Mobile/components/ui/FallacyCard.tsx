import React from "react";
import { View, StyleSheet } from "react-native";
import { ThemedText } from "../ThemedText";
import { ThemedView } from "../ThemedView";
import { IconSymbol } from "./IconSymbol";

export type FallacyCardProps = {
  type: string;
  confidence: number;
  span: [number, number];
  explanation: string;
  text?: string;
};

export const FallacyCard: React.FC<FallacyCardProps> = ({
  type,
  confidence,
  span,
  explanation,
  text,
}) => {
  // Highlight the span in the text if provided
  let highlightedText = null;
  if (text && span[0] >= 0 && span[1] > span[0]) {
    highlightedText = (
      <ThemedText style={styles.argumentText}>
        {text.slice(0, span[0])}
        <ThemedText style={styles.highlight}>
          {text.slice(span[0], span[1])}
        </ThemedText>
        {text.slice(span[1])}
      </ThemedText>
    );
  }

  return (
    <ThemedView style={styles.card}>
      <View style={styles.headerRow}>
        <IconSymbol
          size={20}
          name="exclamationmark.triangle.fill"
          color="#FF9500"
        />
        <View style={styles.typeBadge}>
          <ThemedText style={styles.typeText}>
            {type.replace(/_/g, " ")}
          </ThemedText>
        </View>
        <View style={styles.confidenceBarContainer}>
          <View
            style={[
              styles.confidenceBar,
              { width: `${Math.round(confidence * 100)}%` },
            ]}
          />
        </View>
        <ThemedText style={styles.confidenceText}>
          {Math.round(confidence * 100)}%
        </ThemedText>
      </View>
      {highlightedText && (
        <View style={styles.highlightedTextContainer}>{highlightedText}</View>
      )}
      <ThemedText style={styles.sectionTitle}>Explanation:</ThemedText>
      <ThemedText style={styles.explanationText}>{explanation}</ThemedText>
      <ThemedText style={styles.spanText}>
        <ThemedText type="defaultSemiBold">Span:</ThemedText> [{span[0]},{" "}
        {span[1]}]
      </ThemedText>
    </ThemedView>
  );
};

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderColor: "#FFD700",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    backgroundColor: "#fffbe6",
    shadowColor: "#000",
    shadowOpacity: 0.04,
    shadowRadius: 8,
    shadowOffset: { width: 0, height: 2 },
    elevation: 2,
  },
  headerRow: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 8,
    flexWrap: "wrap",
  },
  typeBadge: {
    backgroundColor: "#FF9500",
    borderRadius: 8,
    paddingHorizontal: 10,
    paddingVertical: 2,
    marginLeft: 8,
  },
  typeText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 14,
    textTransform: "capitalize",
  },
  confidenceBarContainer: {
    flex: 1,
    height: 8,
    backgroundColor: "#FFE5B4",
    borderRadius: 4,
    marginLeft: 12,
    marginRight: 8,
    overflow: "hidden",
  },
  confidenceBar: {
    height: 8,
    backgroundColor: "#FF9500",
    borderRadius: 4,
  },
  confidenceText: {
    fontWeight: "600",
    fontSize: 13,
    color: "#FF9500",
    marginLeft: 4,
  },
  highlightedTextContainer: {
    marginVertical: 8,
  },
  argumentText: {
    fontSize: 15,
    color: "#333",
  },
  highlight: {
    fontWeight: "600",
    borderRadius: 4,
    paddingHorizontal: 2,
  },
  sectionTitle: {
    fontWeight: "600",
    marginTop: 8,
    marginBottom: 2,
    fontSize: 14,
    color: "#FF9500",
  },
  explanationText: {
    fontSize: 14,
    color: "#333",
    fontStyle: "italic",
    marginBottom: 8,
  },
  spanText: {
    fontSize: 13,
    color: "#8E8E93",
    marginTop: 4,
  },
});
