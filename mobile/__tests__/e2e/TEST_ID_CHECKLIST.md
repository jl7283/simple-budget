# Component Test ID Update Checklist

This checklist helps ensure all UI components have the necessary `testID` props for E2E testing. The E2E tests rely on these IDs to find and interact with elements.

## Overview
Test IDs are `string` identifiers added to React Native components that allow automated tests to reliably find and interact with UI elements. They're unaffected by text changes or styling updates, making tests more stable.

## How to Add testID to Components

### Basic Pattern
```tsx
<Button
  onPress={handleLogin}
  testID="login-button"  // Add this
>
  Login
</Button>
```

### For Text Inputs
```tsx
<TextInput
  placeholder="Email"
  testID="email-input"  // Add this
  value={email}
  onChangeText={setEmail}
/>
```

## Components to Update

### LoginPage Component
- [ ] Email TextInput: `testID="email-input"`
- [ ] Password TextInput: `testID="password-input"`
- [ ] Login Button: `testID="login-button"`
- [ ] Forgot Password Link/Button: `testID="forgot-password-link"` (optional)

**File:** `mobile/components/LoginPage.tsx`

```tsx
// Example updates needed:
<TextInput
  testID="email-input"
  placeholder="Enter your email"
  value={email}
  onChangeText={setEmail}
  // ... other props
/>

<TextInput
  testID="password-input"
  placeholder="Enter your password"
  value={password}
  onChangeText={setPassword}
  secureTextEntry
  // ... other props
/>

<Button
  testID="login-button"
  onPress={handleLoginSubmit}
>
  Login
</Button>
```

### RegistrationPage Component
- [ ] Email TextInput: `testID="email-input"`
- [ ] Password TextInput: `testID="password-input"`
- [ ] Confirm Password TextInput: `testID="confirm-password-input"`
- [ ] Register Button: `testID="register-button"`

**File:** `mobile/components/RegistrationPage.tsx`

```tsx
// Example updates needed:
<TextInput
  testID="email-input"
  placeholder="Enter your email"
  value={email}
  onChangeText={setEmail}
/>

<TextInput
  testID="password-input"
  placeholder="Enter your password"
  value={password}
  onChangeText={setPassword}
  secureTextEntry
/>

<TextInput
  testID="confirm-password-input"
  placeholder="Confirm password"
  value={confirmPassword}
  onChangeText={setConfirmPassword}
  secureTextEntry
/>

<Button
  testID="register-button"
  onPress={handleRegister}
>
  Register
</Button>
```

### AddExpenseForm Component
- [ ] Category TextInput: `testID="category-input"`
- [ ] Amount TextInput: `testID="amount-input"`
- [ ] Note TextInput: `testID="note-input"`
- [ ] Submit Button: `testID="add-expense-button"`

**File:** `mobile/components/AddExpenseForm.tsx`

```tsx
// Example updates needed:
<TextInput
  testID="category-input"
  placeholder="Category"
  value={category}
  onChangeText={setCategory}
/>

<TextInput
  testID="amount-input"
  placeholder="Amount"
  value={amount}
  onChangeText={setAmount}
  keyboardType="decimal-pad"
/>

<TextInput
  testID="note-input"
  placeholder="Note (optional)"
  value={note}
  onChangeText={setNote}
  multiline
/>

<Button
  testID="add-expense-button"
  onPress={handleFormSubmit}
>
  Add Expense
</Button>
```

### WelcomePage Component
- [ ] Page Container: `testID="welcome-page"`
- [ ] Login Button: `testID="login-button"`
- [ ] Register Button: `testID="register-button"`

**File:** `mobile/components/WelcomePage.tsx`

```tsx
// Example updates needed:
<View testID="welcome-page">
  {/* content */}
  
  <Button
    testID="login-button"
    onPress={() => router.push("login")}
  >
    Login
  </Button>

  <Button
    testID="register-button"
    onPress={() => router.push("registration")}
  >
    Sign Up
  </Button>
</View>
```

### HomePage Component
- [ ] Page Container: `testID="home-page"`
- [ ] Budget Card: `testID="budget-card"`
- [ ] Expense List: `testID="expense-list"`
- [ ] Loading Indicator: `testID="loading-spinner"`

**File:** `mobile/components/HomePage.tsx`

```tsx
// Example updates needed:
<View testID="home-page">
  {loading && <ActivityIndicator testID="loading-spinner" />}
  
  <View testID="budget-card">
    {/* budget display */}
  </View>

  <FlatList
    testID="expense-list"
    data={expenses}
    // ... other props
  />
</View>
```

### Navigation/Tabs Layout
- [ ] Home Tab: `testID="home-tab"`
- [ ] Add Expense Tab: `testID="add-expense-tab"`
- [ ] Settings Tab: `testID="settings-tab"` (if exists)

**File:** `mobile/app/(tabs)/_layout.tsx`

```tsx
// Example updates needed for bottom tabs:
<BottomTabNavigationProp.Screen
  name="index"
  component={HomePage}
  options={{
    tabBarTestID: "home-tab",
    // ... other options
  }}
/>

<BottomTabNavigationProp.Screen
  name="addexpense"
  component={AddExpensePage}
  options={{
    tabBarTestID: "add-expense-tab",
    // ... other options
  }}
/>
```

### AlertMessage Component
- [ ] Container: `testID="alert-message"`

**File:** `mobile/components/utility/AlertMessage.tsx`

```tsx
// Example updates needed:
<View testID="alert-message">
  <Text>{message}</Text>
</View>
```

### ExpenseCard Component
- [ ] Card Container: `testID="expense-card"`
- [ ] Delete Button (if exists): `testID="delete-expense-button"`
- [ ] Edit Button (if exists): `testID="edit-expense-button"`

**File:** `mobile/components/utility/ExpenseCard.tsx`

```tsx
// Example updates needed:
<Card testID="expense-card">
  {/* card content */}
  
  <Button
    testID="delete-expense-button"
    onPress={handleDelete}
  >
    Delete
  </Button>
</Card>
```

## Implementation Steps

1. **Priority 1 - Critical Components** (Required for current tests):
   - [ ] LoginPage
   - [ ] RegistrationPage
   - [ ] AddExpenseForm
   - [ ] WelcomePage
   - [ ] HomePage

2. **Priority 2 - Navigation Components**:
   - [ ] Tab Navigation Layout
   - [ ] Tab Buttons

3. **Priority 3 - UI Components**:
   - [ ] AlertMessage
   - [ ] ExpenseCard
   - [ ] Loading indicators

## Testing Your Changes

After adding testIDs:

1. Run the E2E tests:
   ```bash
   npm test -- __tests__/e2e
   ```

2. If tests fail finding elements:
   - Check the testID is spelled correctly
   - Use `render().debug()` to see the rendered tree
   - Ensure the component is actually rendering

3. Verify no console errors with the changes

## Important Notes

- **testID naming**: Use camelCase, be descriptive
- **React Native Paper**: Components like `Button`, `TextInput` support `testID` natively
- **Custom Components**: May need to pass `testID` through props to underlying native components
- **No Performance Impact**: testIDs are compiled out in production builds
- **Version Compatibility**: Ensure your React Native version supports testID (all modern versions do)

## Example: Adding testID to Custom Component

If creating a custom component, pass testID through:

```tsx
interface MyButtonProps {
  testID?: string;
  onPress: () => void;
  title: string;
}

export function MyButton({ testID, onPress, title }: MyButtonProps) {
  return (
    <Pressable testID={testID} onPress={onPress}>
      <Text>{title}</Text>
    </Pressable>
  );
}

// Usage:
<MyButton testID="my-button" onPress={handlePress} title="Click Me" />
```

## Verification Checklist

- [ ] All input fields have testID
- [ ] All action buttons have testID  
- [ ] All page containers have testID
- [ ] All navigation elements have testID
- [ ] E2E tests pass with updated components
- [ ] No console errors or warnings
- [ ] App runs normally on device/simulator

## Resources

- [React Native testID Documentation](https://reactnative.dev/docs/view#testid)
- [React Native Paper Component Props](https://callstack.github.io/react-native-paper/docs/guides/paper-versions)
- [Testing Library React Native](https://testing-library.com/docs/react-native-testing-library/intro)
