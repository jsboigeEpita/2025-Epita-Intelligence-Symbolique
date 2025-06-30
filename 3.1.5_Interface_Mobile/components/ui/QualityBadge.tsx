import React from "react";
import { View, StyleSheet } from "react-native";
import { ThemedText } from "../ThemedText";

export type QualityBadgeProps = {
  score: number; // 0 to 1
};

function getQualityLabel(score: number) {
  if (score >= 0.85) return "Excellent";
  if (score >= 0.7) return "Good";
  if (score >= 0.5) return "Fair";
  if (score >= 0.3) return "Weak";
  return "Very Weak";
}

function getQualityColor(score: number) {
  if (score >= 0.85) return "#34C759";
  if (score >= 0.7) return "#5AC8FA";
  if (score >= 0.5) return "#FFD60A";
  if (score >= 0.3) return "#FF9500";
  return "#FF3B30";
}

export const QualityBadge: React.FC<QualityBadgeProps> = ({ score }) => {
  const label = getQualityLabel(score);
  const color = getQualityColor(score);
  return (
    <View
      style={[
        styles.badge,
        { backgroundColor: color + "22", borderColor: color },
      ]}
    >
      <ThemedText style={[styles.label, { color }]}>{label}</ThemedText>
      <ThemedText style={[styles.score, { color }]}>
        {(score * 100).toFixed(0)}%
      </ThemedText>
    </View>
  );
};

const styles = StyleSheet.create({
  badge: {
    flexDirection: "row",
    alignItems: "center",
    alignSelf: "flex-start",
    borderRadius: 16,
    borderWidth: 1.5,
    paddingHorizontal: 12,
    paddingVertical: 4,
    marginTop: 8,
    marginBottom: 4,
  },
  label: {
    fontWeight: "bold",
    fontSize: 14,
    marginRight: 8,
  },
  score: {
    fontWeight: "600",
    fontSize: 13,
  },
});
