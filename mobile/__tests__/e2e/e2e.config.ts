// E2E Test Configuration and Helper File
// This file documents the expected testIDs and provides utilities for E2E testing

/**
 * Standard testIDs used across E2E tests
 * Components should implement these testIDs to ensure E2E tests can find and interact with them
 */

export const TEST_IDS = {
  // Authentication
  auth: {
    emailInput: "email-input",
    passwordInput: "password-input",
    confirmPasswordInput: "confirm-password-input",
    loginButton: "login-button",
    registerButton: "register-button",
    logoutButton: "logout-button",
  },

  // Expense Form
  expense: {
    categoryInput: "category-input",
    amountInput: "amount-input",
    noteInput: "note-input",
    submitButton: "submit-button",
    addExpenseButton: "add-expense-button",
  },

  // Navigation
  navigation: {
    homeTab: "home-tab",
    homeTabSelected: "home-tab-selected",
    addExpenseTab: "add-expense-tab",
    settingsTab: "settings-tab",
    loginLink: "login-link",
    registerLink: "register-link",
  },

  // Common UI
  ui: {
    alertMessage: "alert-message",
    loadingSpinner: "loading-spinner",
    errorContainer: "error-container",
    successMessage: "success-message",
    retryButton: "retry-button",
  },

  // Welcome/Home
  pages: {
    welcomePage: "welcome-page",
    homePage: "home-page",
    loginPage: "login-page",
    registrationPage: "registration-page",
  },
};

/**
 * Mock API Response Helper
 * Use this to quickly create consistent mock responses for tests
 */
export const mockResponses = {
  loginSuccess: (token: string = "test-jwt-token") => ({
    ok: true,
    status: 200,
    json: async () => ({ access_token: token }),
  }),

  loginFailure: () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: "Invalid credentials" }),
  }),

  registrationSuccess: () => ({
    ok: true,
    status: 201,
    json: async () => ({ message: "User registered successfully", id: "user-123" }),
  }),

  budgetCheck: (totalAmount: number = 1000, spent: number = 0) => ({
    ok: true,
    status: 200,
    json: async () => ({ totalAmount, spent, remaining: totalAmount - spent }),
  }),

  expenseCreated: (id: string = "expense-123") => ({
    ok: true,
    status: 201,
    json: async () => ({ id, created_at: new Date().toISOString() }),
  }),

  expenseExceedsBudget: () => ({
    ok: false,
    status: 400,
    json: async () => ({ detail: "Expense exceeds remaining budget" }),
  }),

  unauthorized: () => ({
    ok: false,
    status: 401,
    json: async () => ({ detail: "Unauthorized" }),
  }),

  serverError: () => ({
    ok: false,
    status: 500,
    json: async () => ({ detail: "Internal server error" }),
  }),

  networkError: () =>
    Promise.reject(new Error("Network error: Failed to fetch")),
};

/**
 * Test Context Provider Helper
 * Creates a consistently configured AppContext for testing
 */
export const createTestContext = (jwt: string = "", setJwt?: jest.Mock) => ({
  jwt,
  setJwt: setJwt || jest.fn(),
});

/**
 * API Endpoint Constants
 * Use these to verify fetch calls in tests
 */
export const API_ENDPOINTS = {
  LOGIN: "http://localhost:8000/api/v1/auth/login",
  REGISTER: "http://localhost:8000/api/v1/auth/register",
  CURRENT_BUDGET: "http://localhost:8000/api/v1/budgets/current-month",
  CREATE_EXPENSE: "http://localhost:8000/api/v1/expenses",
  GET_EXPENSES: "http://localhost:8000/api/v1/expenses",
  GET_INCOME: "http://localhost:8000/api/v1/income",
  GET_REPORTS: "http://localhost:8000/api/v1/reports",
};

/**
 * Common Headers for API Requests
 */
export const getAuthHeaders = (jwt: string) => ({
  "content-type": "application/json",
  "Authorization": `Bearer ${jwt}`,
});

/**
 * Wait For Utilities
 * Helper functions to wait for specific conditions in tests
 */
export const waitForUtils = {
  /**
   * Wait for fetch to be called
   */
  fetchCalled: async (
    fetchMock: jest.Mock,
    endpoint?: string,
    timeout: number = 3000
  ) => {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      if (endpoint) {
        if (
          fetchMock.mock.calls.some((call) => call[0].includes(endpoint))
        ) {
          return;
        }
      } else if (fetchMock.mock.calls.length > 0) {
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    throw new Error(`Fetch not called within ${timeout}ms`);
  },

  /**
   * Wait for specific function to be called with arguments
   */
  functionCalled: async (
    fn: jest.Mock,
    expectedArgs?: any[],
    timeout: number = 3000
  ) => {
    const startTime = Date.now();
    while (Date.now() - startTime < timeout) {
      if (fn.mock.calls.length > 0) {
        if (!expectedArgs) return;
        if (
          fn.mock.calls.some((call) =>
            JSON.stringify(call) === JSON.stringify(expectedArgs)
          )
        ) {
          return;
        }
      }
      await new Promise((resolve) => setTimeout(resolve, 50));
    }
    throw new Error(
      `Function not called with expected args within ${timeout}ms`
    );
  },
};

/**
 * Test Data Generators
 * Create realistic test data for various scenarios
 */
export const testDataGenerators = {
  user: (overrides?: Partial<any>) => ({
    id: "user-123",
    email: "test@example.com",
    name: "Test User",
    created_at: new Date().toISOString(),
    ...overrides,
  }),

  expense: (overrides?: Partial<any>) => ({
    id: "expense-123",
    amount: 50,
    category: "Food",
    note: "Lunch",
    date: new Date().toISOString(),
    ...overrides,
  }),

  budget: (overrides?: Partial<any>) => ({
    id: "budget-123",
    totalAmount: 1000,
    spent: 300,
    remaining: 700,
    month: new Date().getMonth() + 1,
    year: new Date().getFullYear(),
    ...overrides,
  }),

  income: (overrides?: Partial<any>) => ({
    id: "income-123",
    amount: 3000,
    source: "Salary",
    date: new Date().toISOString(),
    ...overrides,
  }),
};

/**
 * Mock Reset Helper
 * Safely reset all mocks in a test
 */
export const resetAllMocks = () => {
  (global.fetch as jest.Mock).mockClear();
  jest.clearAllMocks();
};

/**
 * Component Testing Wrapper
 * Consistently wrap test components with required providers
 */
import React from "react";
import AppContext from "@/app/context/AppContext";

export const TestWrapper: React.FC<{
  children: React.ReactNode;
  jwt?: string;
  setJwt?: jest.Mock;
}> = ({ children, jwt = "", setJwt }) => (
  <AppContext.Provider value={createTestContext(jwt, setJwt)}>
    {children}
  </AppContext.Provider>
);

/**
 * Setup E2E Test Environment
 * Call this in your test beforeEach block for consistent setup
 */
export const setupE2ETest = () => {
  // Use fake timers for better test control
  jest.useFakeTimers();

  // Mock console to reduce noise
  jest.spyOn(console, "error").mockImplementation(() => {});
  jest.spyOn(console, "log").mockImplementation(() => {});
  jest.spyOn(console, "warn").mockImplementation(() => {});

  // Mock fetch globally
  (global as any).fetch = jest.fn();

  return {
    restore: () => {
      jest.useRealTimers();
      jest.restoreAllMocks();
      resetAllMocks();
    },
  };
};

/**
 * Cleanup E2E Test Environment
 * Call this in your test afterEach block
 */
export const cleanupE2ETest = (
  consoleErrorSpy: jest.SpyInstance,
  consoleLogSpy: jest.SpyInstance,
  consoleWarnSpy: jest.SpyInstance
) => {
  jest.useRealTimers();
  consoleErrorSpy.mockRestore();
  consoleLogSpy.mockRestore();
  consoleWarnSpy.mockRestore();
};
