import React from "react";
import { View, StyleSheet } from "react-native";
import { ThemedText } from "../ThemedText";
import { ThemedView } from "../ThemedView";
import { IconSymbol } from "./IconSymbol";
import { Colors } from "@/constants/Colors";

export type ArgumentCardProps = {
  id: string;
  text: string;
  premises: string[];
  conclusion: string;
  structure: "deductive" | "inductive" | "analogical" | "abductive" | "other";
  validity: boolean;
  fallacies: string[];
};

const structureColors: Record<string, string> = {
  deductive: "#34C759",
  inductive: "#007AFF",
  analogical: "#AF52DE",
  abductive: "#FF9500",
  other: "#8E8E93",
};

export const ArgumentCard: React.FC<ArgumentCardProps> = ({
  text,
  premises,
  conclusion,
  structure,
  validity,
  fallacies,
}) => {
  return (
    <ThemedView style={styles.card}>
      <View style={styles.headerRow}>
        <IconSymbol
          size={20}
          name={validity ? "checkmark.seal.fill" : "xmark.seal.fill"}
          color={validity ? "#34C759" : "#FF3B30"}
        />
        <ThemedText style={styles.argumentType}>
          {validity ? "Valid" : "Invalid"}
        </ThemedText>
        <View
          style={[
            styles.structureBadge,
            {
              backgroundColor:
                structureColors[structure] || structureColors.other,
            },
          ]}
        >
          <ThemedText style={styles.structureText}>{structure}</ThemedText>
        </View>
      </View>
      <ThemedText type="defaultSemiBold" style={styles.argumentText}>
        {text}
      </ThemedText>
      <ThemedText style={styles.sectionTitle}>Premises:</ThemedText>
      {premises.map((premise, idx) => (
        <ThemedText key={idx} style={styles.premiseItem}>
          • {premise}
        </ThemedText>
      ))}
      <ThemedText style={styles.sectionTitle}>Conclusion:</ThemedText>
      <ThemedText style={styles.conclusionText}>{conclusion}</ThemedText>
      {fallacies && fallacies.length > 0 && (
        <View style={styles.fallaciesRow}>
          {fallacies.map((fallacy, idx) => (
            <View key={idx} style={styles.fallacyTag}>
              <ThemedText style={styles.fallacyText}>{fallacy}</ThemedText>
            </View>
          ))}
        </View>
      )}
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
  argumentType: {
    marginLeft: 8,
    marginRight: 8,
    fontWeight: "600",
    fontSize: 15,
  },
  structureBadge: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginLeft: "auto",
  },
  structureText: {
    color: "#fff",
    fontWeight: "bold",
    fontSize: 13,
    textTransform: "capitalize",
  },
  argumentText: {
    marginBottom: 8,
    fontSize: 16,
  },
  sectionTitle: {
    fontWeight: "600",
    marginTop: 8,
    marginBottom: 2,
    fontSize: 14,
    color: Colors.light.tint,
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
  fallaciesRow: {
    flexDirection: "row",
    flexWrap: "wrap",
    marginTop: 8,
  },
  fallacyTag: {
    backgroundColor: "#FF9500",
    borderRadius: 6,
    paddingHorizontal: 8,
    paddingVertical: 2,
    marginRight: 6,
    marginBottom: 4,
  },
  fallacyText: {
    color: "#fff",
    fontSize: 13,
    fontWeight: "600",
    textTransform: "capitalize",
  },
});
