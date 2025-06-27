import React from "react";
import {
  ActivityIndicator,
  StyleSheet,
  TouchableOpacity,
  TouchableOpacityProps,
} from "react-native";

import { ThemedText } from "@/components/ThemedText";
import { Colors } from "@/constants/Colors";
import { useColorScheme } from "@/hooks/useColorScheme";

export type ThemedButtonProps = TouchableOpacityProps & {
  title: string;
  loading?: boolean;
  textColor?: string;
};

export function ThemedButton({
  title,
  loading = false,
  disabled,
  style,
  textColor = "#FFFFFF",
  ...rest
}: ThemedButtonProps) {
  const colorScheme = useColorScheme();

  return (
    <TouchableOpacity
      style={[
        styles.button,
        { backgroundColor: Colors[colorScheme ?? "light"].tint },
        disabled && styles.disabledButton,
        style,
      ]}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <ActivityIndicator color={textColor} />
      ) : (
        <ThemedText
          type="button"
          style={{
            color: textColor,
          }}
        >
          {title}
        </ThemedText>
      )}
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  button: {
    borderRadius: 8,
    padding: 14,
    alignItems: "center",
    justifyContent: "center",
  },
  disabledButton: {
    opacity: 0.6,
  },
});
