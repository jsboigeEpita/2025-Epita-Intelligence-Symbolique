import { Platform, type TextStyle } from "react-native";
import { Colors } from "@/constants/Colors";

export type MarkdownStyleMessage = {
  isUser: boolean;
  isError?: boolean;
};

type ColorScheme = "light" | "dark";

export function getMarkdownStyle(
  colorScheme: string | null | undefined,
  getTextColor: (message: MarkdownStyleMessage) => string,
  message: MarkdownStyleMessage
): Record<string, TextStyle> {
  const scheme: ColorScheme = colorScheme === "dark" ? "dark" : "light";
  const baseColor = getTextColor(message);
  return {
    body: {
      color: baseColor,
      fontSize: 16,
      fontWeight: message.isError ? "600" : "normal",
    },
    paragraph: {
      marginTop: 0,
      marginBottom: 0,
    },
    strong: {
      fontWeight: "bold",
    },
    em: {
      fontStyle: "italic",
    },
    code_inline: {
      backgroundColor: Colors[scheme].border,
      borderRadius: 4,
      paddingHorizontal: 4,
      fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
      fontSize: 15,
    },
    code_block: {
      backgroundColor: Colors[scheme].border,
      borderRadius: 6,
      padding: 8,
      fontFamily: Platform.OS === "ios" ? "Menlo" : "monospace",
      fontSize: 15,
    },
    blockquote: {
      borderLeftWidth: 4,
      borderLeftColor: Colors[scheme].tint,
      backgroundColor: Colors[scheme].border,
      paddingHorizontal: 12,
      paddingVertical: 4,
      marginVertical: 4,
    },
    link: {
      color: Colors[scheme].tint,
      textDecorationLine: "underline",
    },
    list_item: {
      flexDirection: "row",
      alignItems: "flex-start",
    },
    bullet_list: {
      marginVertical: 4,
    },
    ordered_list: {
      marginVertical: 4,
    },
    heading1: {
      fontSize: 22,
      fontWeight: "bold",
      marginVertical: 4,
      color: baseColor,
    },
    heading2: {
      fontSize: 20,
      fontWeight: "bold",
      marginVertical: 4,
      color: baseColor,
    },
    heading3: {
      fontSize: 18,
      fontWeight: "bold",
      marginVertical: 4,
      color: baseColor,
    },
  };
}
