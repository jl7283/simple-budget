import { Stack } from "expo-router";
import React from "react";
import AppContext from "./context/AppContext";

export default function RootLayout() {
  const [jwt, setJwt] = React.useState("");
  return (
    <AppContext.Provider value={{ jwt, setJwt }}>
      <Stack>
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
      </Stack>
    </AppContext.Provider>
  );
}
