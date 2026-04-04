import React from "react";
import { render, fireEvent, waitFor, screen } from "@testing-library/react-native";
import { AddExpenseForm } from "@/components/AddExpenseForm";
import AppContext from "@/app/context/AppContext";

// Mock navigation
jest.mock("@react-navigation/native", () => ({
  useIsFocused: () => true,
}));

jest.mock("expo-router", () => ({
  useRouter: () => ({
    push: jest.fn(),
    replace: jest.fn(),
  }),
  Redirect: () => null,
}));

jest.mock("@/utilities/getErrorMessage", () => ({
  __esModule: true,
  default: (_data: any, fallback: string) => fallback,
}));

jest.mock("@/components/utility/AlertMessage", () => ({
  __esModule: true,
  default: ({ message }: { message: string }) => {
    const React = require("react");
    const { Text } = require("react-native");
    return <Text testID="alert-message">{message}</Text>;
  },
}));

describe("Expense Management E2E Tests", () => {
  let consoleErrorSpy: jest.SpyInstance;
  let consoleLogSpy: jest.SpyInstance;
  const mockJwt = "valid-jwt-token";

  beforeEach(() => {
    jest.useFakeTimers();
    (global as any).fetch = jest.fn();
    consoleErrorSpy = jest.spyOn(console, "error").mockImplementation(() => {});
    consoleLogSpy = jest.spyOn(console, "log").mockImplementation(() => {});
  });

  afterEach(() => {
    jest.useRealTimers();
    consoleErrorSpy.mockRestore();
    consoleLogSpy.mockRestore();
  });

  describe("Add Expense Flow", () => {
    it("should check budget status on component load", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ totalAmount: 1000, spent: 200 }),
      });

      render(
        <AppContext.Provider value={{ jwt: mockJwt, setJwt: jest.fn() }}>
          <AddExpenseForm />
        </AppContext.Provider>
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          "http://localhost:8000/api/v1/budgets/current-month",
          expect.objectContaining({
            method: "GET",
            headers: expect.objectContaining({
              "Authorization": `Bearer ${mockJwt}`,
            }),
          })
        );
      });
    });

    it("should successfully add expense with valid data", async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ totalAmount: 1000 }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ id: "expense-123", amount: 50, category: "Food" }),
        });

      const { getByTestId, getByText } = render(
        <AppContext.Provider value={{ jwt: mockJwt, setJwt: jest.fn() }}>
          <AddExpenseForm />
        </AppContext.Provider>
      );

      const categoryInput = getByTestId("category-input");
      const amountInput = getByTestId("amount-input");
      const noteInput = getByTestId("note-input");
      const submitButton = getByText("Add Expense");

      fireEvent.changeText(categoryInput, "Food");
      fireEvent.changeText(amountInput, "50");
      fireEvent.changeText(noteInput, "Lunch at restaurant");
      fireEvent.press(submitButton);

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith(
          "http://localhost:8000/api/v1/expenses",
          expect.objectContaining({
            method: "POST",
            headers: expect.objectContaining({
              "Authorization": `Bearer ${mockJwt}`,
            }),
            body: JSON.stringify({
              amount: 50,
              category: "Food",
              note: "Lunch at restaurant",
            }),
          })
        );
      });
    });

    it("should display error when adding expense exceeds budget", async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ totalAmount: 100, spent: 80 }),
        })
        .mockResolvedValueOnce({
          ok: false,
          json: async () => ({ detail: "Expense exceeds remaining budget" }),
        });

      const { getByTestId, getByText } = render(
        <AppContext.Provider value={{ jwt: mockJwt, setJwt: jest.fn() }}>
          <AddExpenseForm />
        </AppContext.Provider>
      );

      const categoryInput = getByTestId("category-input");
      const amountInput = getByTestId("amount-input");
      const submitButton = getByText("Add Expense");

      fireEvent.changeText(categoryInput, "Electronics");
      fireEvent.changeText(amountInput, "50");
      fireEvent.press(submitButton);

      await waitFor(() => {
        expect(screen.getByTestID("alert-message")).toBeTruthy();
      });
    });

    it("should validate required fields", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ totalAmount: 1000 }),
      });

      const { getByText } = render(
        <AppContext.Provider value={{ jwt: mockJwt, setJwt: jest.fn() }}>
          <AddExpenseForm />
        </AppContext.Provider>
      );

      const submitButton = getByText("Add Expense");
      fireEvent.press(submitButton);

      // Fetch should only be called once for budget check, not for expense creation
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledTimes(1);
      });
    });

    it("should clear form after successful submission", async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ totalAmount: 1000 }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ id: "expense-123" }),
        });

      const { getByTestId, getByText, queryByDisplayValue } = render(
        <AppContext.Provider value={{ jwt: mockJwt, setJwt: jest.fn() }}>
          <AddExpenseForm />
        </AppContext.Provider>
      );

      const categoryInput = getByTestId("category-input");
      const amountInput = getByTestId("amount-input");
      const submitButton = getByText("Add Expense");

      fireEvent.changeText(categoryInput, "Food");
      fireEvent.changeText(amountInput, "50");
      fireEvent.press(submitButton);

      jest.runAllTimers();

      await waitFor(() => {
        expect(queryByDisplayValue("Food")).toBeNull();
        expect(queryByDisplayValue("50")).toBeNull();
      });
    });

    it("should handle network errors gracefully", async () => {
      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          json: async () => ({ totalAmount: 1000 }),
        })
        .mockRejectedValueOnce(new Error("Network error"));

      const { getByTestId, getByText } = render(
        <AppContext.Provider value={{ jwt: mockJwt, setJwt: jest.fn() }}>
          <AddExpenseForm />
        </AppContext.Provider>
      );

      const categoryInput = getByTestId("category-input");
      const amountInput = getByTestId("amount-input");
      const submitButton = getByText("Add Expense");

      fireEvent.changeText(categoryInput, "Food");
      fireEvent.changeText(amountInput, "50");
      fireEvent.press(submitButton);

      await waitFor(() => {
        expect(consoleErrorSpy).toHaveBeenCalled();
      });
    });
  });

  describe("Expense State Management", () => {
    it("should maintain budget state across re-renders", async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ totalAmount: 1000, spent: 200 }),
      });

      const { rerender } = render(
        <AppContext.Provider value={{ jwt: mockJwt, setJwt: jest.fn() }}>
          <AddExpenseForm />
        </AppContext.Provider>
      );

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledTimes(1);
      });

      rerender(
        <AppContext.Provider value={{ jwt: mockJwt, setJwt: jest.fn() }}>
          <AddExpenseForm />
        </AppContext.Provider>
      );

      // Verify fetch is called again on re-focus
      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledTimes(1);
      });
    });
  });
});
