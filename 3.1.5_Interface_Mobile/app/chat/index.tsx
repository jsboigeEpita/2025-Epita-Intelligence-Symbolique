import { ThemedText } from "@/components/ThemedText";
import { ThemedView } from "@/components/ThemedView";
import { IconSymbol } from "@/components/ui/IconSymbol";
import { Colors } from "@/constants/Colors";
import { useColorScheme } from "@/hooks/useColorScheme";
import { getErrorMessage, sendChatMessage } from "@/services/api";
import React, { useRef, useState } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  TextInput,
  TouchableOpacity,
} from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Markdown from "react-native-markdown-display";
import { getMarkdownStyle } from "@/components/ui/MarkdownStyles";

type Message = {
  id: string;
  text: string;
  isUser: boolean;
  isError?: boolean;
  timestamp: Date;
};

export default function ChatScreen() {
  const insets = useSafeAreaInsets();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      text: "Hello! I am your argumentative analysis assistant. How can I help you today?",
      isUser: false,
      timestamp: new Date(),
    },
  ]);
  const [inputMessage, setInputMessage] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollViewRef = useRef<ScrollView>(null);
  const colorScheme = useColorScheme();

  const handleSend = async () => {
    if (!inputMessage.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      text: inputMessage,
      isUser: true,
      timestamp: new Date(),
    };

    setMessages((prevMessages) => [...prevMessages, userMessage]);
    const currentMessage = inputMessage;
    setInputMessage("");
    setIsLoading(true);

    // Scroll to bottom after sending message
    setTimeout(() => {
      scrollViewRef.current?.scrollToEnd({ animated: true });
    }, 100);

    try {
      // Call the chat API service with context for argument analysis
      const response = await sendChatMessage(currentMessage);

      const botMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: response.message,
        isUser: false,
        timestamp: new Date(),
      };

      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (error) {
      // Create error message with consistent styling
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        text: getErrorMessage(error),
        isUser: false,
        isError: true,
        timestamp: new Date(),
      };

      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setIsLoading(false);
      // Scroll to bottom after receiving response or error
      setTimeout(() => {
        scrollViewRef.current?.scrollToEnd({ animated: true });
      }, 100);
    }
  };

  const getMessageStyle = (message: Message) => {
    if (message.isUser) {
      return {
        backgroundColor: Colors[colorScheme ?? "light"].tint,
      };
    } else if (message.isError) {
      return {
        backgroundColor: "rgba(255, 59, 48, 0.1)",
        borderWidth: 1,
        borderColor: "#FF3B30",
      };
    } else {
      return {
        backgroundColor: "rgba(10, 126, 164, 0.1)",
      };
    }
  };

  const getTextColor = (message: Message) => {
    if (message.isUser) {
      return Colors[colorScheme ?? "light"].background;
    } else if (message.isError) {
      return "#FF3B30";
    } else {
      return Colors[colorScheme ?? "light"].text;
    }
  };

  const getMarkdownTextColor = (msg: { isUser: boolean; isError?: boolean }) =>
    getTextColor(msg as Message);

  return (
    <ThemedView style={styles.container}>
      <KeyboardAvoidingView
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        style={styles.keyboardAvoidingView}
        keyboardVerticalOffset={90}
      >
        <ScrollView
          ref={scrollViewRef}
          style={styles.messagesContainer}
          contentContainerStyle={styles.messagesContent}
        >
          {messages.map((message) => (
            <ThemedView
              key={message.id}
              style={[
                styles.messageBubble,
                message.isUser ? styles.userBubble : styles.botBubble,
                getMessageStyle(message),
              ]}
            >
              {message.isError && (
                <ThemedView
                  style={[
                    styles.errorHeader,
                    { backgroundColor: "transparent" },
                  ]}
                >
                  <IconSymbol
                    name="xmark.circle.fill"
                    size={16}
                    color="#FF3B30"
                  />
                  <ThemedText style={[styles.errorLabel, { color: "#FF3B30" }]}>
                    Error
                  </ThemedText>
                </ThemedView>
              )}
              <Markdown
                style={getMarkdownStyle(
                  colorScheme,
                  getMarkdownTextColor,
                  message
                )}
              >
                {message.text}
              </Markdown>
              <ThemedText
                style={[
                  styles.timestamp,
                  {
                    color: getTextColor(message),
                    opacity: 0.6,
                  },
                ]}
              >
                {message.timestamp.toLocaleTimeString([], {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </ThemedText>
            </ThemedView>
          ))}
          {isLoading && (
            <ThemedView
              style={[
                styles.messageBubble,
                styles.botBubble,
                { backgroundColor: "rgba(10, 126, 164, 0.1)" },
              ]}
            >
              <ActivityIndicator
                size="small"
                color={Colors[colorScheme ?? "light"].tint}
              />
            </ThemedView>
          )}
        </ScrollView>

        <ThemedView
          style={[
            styles.inputContainer,
            {
              paddingTop: 16,
              paddingBottom: insets.bottom === 0 ? 16 : insets.bottom,
              paddingHorizontal: 16,
              borderTopColor: Colors[colorScheme ?? "light"].border,
            },
          ]}
        >
          <TextInput
            style={[
              styles.input,
              {
                color: Colors[colorScheme ?? "light"].text,
                borderColor: Colors[colorScheme ?? "light"].border,
                backgroundColor: Colors[colorScheme ?? "light"].border,
              },
            ]}
            placeholder="Type a message..."
            placeholderTextColor={Colors[colorScheme ?? "light"].icon}
            value={inputMessage}
            onChangeText={setInputMessage}
            multiline
          />
          <TouchableOpacity
            style={[
              styles.sendButton,
              { backgroundColor: Colors[colorScheme ?? "light"].tint },
            ]}
            onPress={handleSend}
            disabled={!inputMessage.trim() || isLoading}
          >
            <IconSymbol
              name="arrow.up"
              size={20}
              color={Colors[colorScheme ?? "light"].background}
            />
          </TouchableOpacity>
        </ThemedView>
      </KeyboardAvoidingView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  keyboardAvoidingView: {
    flex: 1,
  },
  messagesContainer: {
    flex: 1,
    paddingHorizontal: 16,
  },
  messagesContent: {
    paddingTop: 16,
    paddingBottom: 16,
  },
  messageBubble: {
    padding: 12,
    borderRadius: 18,
    marginBottom: 8,
    maxWidth: "80%",
  },
  userBubble: {
    alignSelf: "flex-end",
    borderBottomRightRadius: 4,
  },
  botBubble: {
    alignSelf: "flex-start",
    borderBottomLeftRadius: 4,
  },
  errorHeader: {
    flexDirection: "row",
    alignItems: "center",
    marginBottom: 6,
  },
  errorLabel: {
    fontSize: 12,
    fontWeight: "bold",
    marginLeft: 4,
  },
  messageText: {
    fontSize: 16,
  },
  timestamp: {
    fontSize: 10,
    alignSelf: "flex-end",
    marginTop: 4,
  },
  inputContainer: {
    flexDirection: "row",
    borderTopWidth: 1,
    alignItems: "center",
  },
  input: {
    flex: 1,
    borderWidth: 1,
    borderRadius: 24,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 16,
    maxHeight: 120,
  },
  sendButton: {
    width: 40,
    height: 40,
    borderRadius: 20,
    justifyContent: "center",
    alignItems: "center",
    marginLeft: 8,
  },
});
