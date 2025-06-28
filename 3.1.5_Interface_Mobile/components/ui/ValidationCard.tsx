import React from "react";
import { View, StyleSheet } from "react-native";
import { ThemedText } from "../ThemedText";
import { ThemedView } from "../ThemedView";
import { IconSymbol } from "./IconSymbol";

export type ValidationCardProps = {
  valid: boolean;
  formalization: {
    type: "propositional" | "predicate" | "other";
    premises: string[];
    conclusion: string;
    rule: string;
  };
  explanation: string;
  execution_time: number;
};

const typeColors: Record<string, string> = {
  propositional: "#34C759",
  predicate: "#007AFF",
  other: "#8E8E93",
};

export const ValidationCard: React.FC<ValidationCardProps> = ({
  valid,
  formalization,
  explanation,
  execution_time,
}) => {
  return (
    <ThemedView style={styles.card}>
      <View style={styles.headerRow}>
        <IconSymbol
          size={22}
          name={valid ? "checkmark.shield.fill" : "xmark.shield.fill"}
          color={valid ? "#34C759" : "#FF3B30"}
        />
        <ThemedText
          style={[
            styles.validityText,
            { color: valid ? "#34C759" : "#FF3B30" },
          ]}
        >
          {valid ? "Valid Argument" : "Invalid Argument"}
        </ThemedText>
        <View
          style={[
            styles.typeBadge,
            {
              backgroundColor:
                typeColors[formalization?.type] || typeColors.other,
            },
          ]}
        >
          <ThemedText style={styles.typeText}>{formalization?.type}</ThemedText>
        </View>
        <View style={styles.ruleBadge}>
          <ThemedText style={styles.ruleText}>
            {formalization?.rule?.replace(/_/g, " ")}
          </ThemedText>
        </View>
      </View>
      <ThemedText style={styles.sectionTitle}>Premises:</ThemedText>
      {formalization?.premises?.map((premise, idx) => (
        <ThemedText key={idx} style={styles.premiseItem}>
          • {premise}
        </ThemedText>
      ))}
      <ThemedText style={styles.sectionTitle}>Conclusion:</ThemedText>
      <ThemedText style={styles.conclusionText}>
        {formalization?.conclusion}
      </ThemedText>
      <ThemedText style={styles.sectionTitle}>Explanation:</ThemedText>
      <ThemedText style={styles.explanationText}>{explanation}</ThemedText>
      <ThemedText style={styles.executionTime}>
        <ThemedText type="defaultSemiBold">Execution time:</ThemedText>{" "}
        {execution_time.toFixed(2)}s
      </ThemedText>
    </ThemedView>
  );
};

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderColor: "#E5E5EA",
    borderRadius: 12,
    padding: 16,
    marginBottom: 16,
    backgroundColor: "#fff",
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
  validityText: {
    marginLeft: 8,
    marginRight: 8,
    fontWeight: "600",
    fontSize: 15,
  },
  typeBadge: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginLeft: "auto",
    marginRight: 8,
  },
  typeText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 13,
    textTransform: "capitalize",
  },
  ruleBadge: {
    backgroundColor: "#F2F2F7",
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  ruleText: {
    color: "#007AFF",
    fontWeight: "bold",
    fontSize: 13,
    textTransform: "capitalize",
  },
  sectionTitle: {
    fontWeight: "600",
    marginTop: 8,
    marginBottom: 2,
    fontSize: 14,
    color: "#007AFF",
  },
  premiseItem: {
    marginLeft: 8,
    fontSize: 14,
    color: "#333",
  },
  conclusionText: {
    fontWeight: "bold",
    color: "#007AFF",
    marginBottom: 8,
    fontSize: 15,
  },
  explanationText: {
    fontSize: 14,
    color: "#333",
    fontStyle: "italic",
    marginBottom: 8,
  },
  executionTime: {
    fontSize: 13,
    color: "#8E8E93",
    marginTop: 4,
  },
});
