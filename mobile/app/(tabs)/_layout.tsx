import { Tabs } from "expo-router";
import { useContext } from "react";
import AppContext from "../context/AppContext";

export default function TabLayout() {
  const { jwt, setJwt } = useContext(AppContext);
  const userIsLoggedIn = jwt !== "";
  return (
    <Tabs>
      <Tabs.Screen name="index" options={{ title: "Current Month", href: userIsLoggedIn ? "/(tabs)" : null }} />
      <Tabs.Screen name="registration" options={{ title: "Register", href: userIsLoggedIn ? null : "/registration" }} />
      <Tabs.Screen name="home" options={{ title: "Home", href: null}} /> 
      <Tabs.Screen name="addexpense" options={{ title: "Add Expense", href: userIsLoggedIn ? "/(tabs)/addexpense" : null }} />
      <Tabs.Screen name="login" options={{ title: "Login", href: userIsLoggedIn ? null : "/login" }} />
    </Tabs>
  );
}
