import { IconSymbol } from "@/components/ui/IconSymbol";
import { Colors } from "@/constants/Colors";
import { useColorScheme } from "@/hooks/useColorScheme";
import { Stack, useRouter } from "expo-router";
import React from "react";
import { TouchableOpacity } from "react-native";

export default function ChatLayout() {
  const colorScheme = useColorScheme();
  const router = useRouter();

  return (
    <Stack
      screenOptions={{
        headerStyle: {
          backgroundColor: Colors[colorScheme ?? "light"].background,
        },
        headerTintColor: Colors[colorScheme ?? "light"].tint,
        headerTitleStyle: {
          fontWeight: "bold",
        },
        headerLeft: () => {
          return (
            <TouchableOpacity onPress={() => router.back()}>
              <IconSymbol
                name="arrow.left"
                size={24}
                color={Colors[colorScheme ?? "light"].tint}
              />
            </TouchableOpacity>
          );
        },
      }}
    >
      <Stack.Screen
        name="index"
        options={{
          title: "AI Assistant",
        }}
      />
    </Stack>
  );
}
