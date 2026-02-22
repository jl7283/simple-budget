import AppContext from "@/app/context/AppContext";
import sharedStyles from "@/styles/shared";
import { useContext, useState } from "react";
import { Button, Text, TextInput } from "react-native-paper";
export function AddExpenseForm() {
    const jwt = useContext(AppContext).jwt;
    const [errorMessage, setErrorMessage] = useState("");
    const [category, setCategory] = useState("");
    const [amount, setAmount] = useState("");
    const [note, setNote] = useState("");
    const handleFormSubmit = async () => {
        console.log("Form Submitted!");
        const url = "http://localhost:8000/api/v1/expenses";
        const options = {
            method: "POST",
            headers: {
                "content-type": "application/json",
                "authorization": `Bearer ${jwt}`,
            },
            body: JSON.stringify({
                amount: parseFloat(amount),
                category: category,
                note: note,
                date: new Date().toISOString().split("T")[0], // Get current date in YYYY-MM-DD format
            }),
        };
        try {
            const response = await fetch(url, options);
            const data = await response.json();
            console.log(data);
            if (response.ok) {
                // Registration successful, handle accordingly (e.g., navigate to login page)
                console.log("Expense Created");
            } else {
                // Handle login failure (e.g., display error message)
                console.error("Expense creation failed:", data);
                setErrorMessage(data.error?.message || "Expense creation failed");
                throw new Error(data.error?.message || "Expense creation failed");
            }
        } catch (error) {
            console.error(error);
        }
    };

    return (
        <>
            {errorMessage ? <Text style={{ color: "red" }}>{errorMessage}</Text> : null}
            <Text variant="displayLarge" style={sharedStyles.centeredText.text} theme={{ colors: { onSurface: "black" } }}>
                Enter a new expense.
            </Text>
            <TextInput
                label="Category"
                value={category}
                onChangeText={text => setCategory(text)}
            />
            <TextInput
                label="Amount"
                value={amount}
                onChangeText={text => setAmount(text)}
            />
            <TextInput
                label="Note"
                value={note}
                onChangeText={text => setNote(text)}
            />
            <Button mode="contained" onPress={handleFormSubmit}>Submit</Button>
        </>
    );
}
export default AddExpenseForm;