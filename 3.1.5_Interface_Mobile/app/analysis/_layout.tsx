import { IconSymbol } from "@/components/ui/IconSymbol";
import { Colors } from "@/constants/Colors";
import { useColorScheme } from "@/hooks/useColorScheme";
import { router, Stack } from "expo-router";
import { TouchableOpacity } from "react-native";

export default function AnalysisLayout() {
  const colorScheme = useColorScheme();

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
        name="analyze"
        options={{
          title: "Full Analysis",
        }}
      />
      <Stack.Screen
        name="validate"
        options={{
          title: "Validate Arguments",
        }}
      />
      <Stack.Screen
        name="fallacies"
        options={{
          title: "Detect Fallacies",
        }}
      />
    </Stack>
  );
}
