const DEFAULT_API_BASE_URL = "http://localhost:8000";
const DEFAULT_API_PREFIX = "/api/v1";
let hasWarnedAboutMissingBaseUrl = false;

function trimTrailingSlash(value: string) {
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

function ensureLeadingSlash(value: string) {
  return value.startsWith("/") ? value : `/${value}`;
}

function normalizePath(path: string) {
  if (!path) {
    return "";
  }

  return path.startsWith("/") ? path : `/${path}`;
}

export function getApiBaseUrl() {
  const configuredBaseUrl = process.env.EXPO_PUBLIC_API_BASE_URL;
  const isStrictMode = process.env.EXPO_PUBLIC_API_STRICT === "true";

  if (!configuredBaseUrl && isStrictMode && process.env.NODE_ENV === "production") {
    throw new Error(
      "EXPO_PUBLIC_API_BASE_URL is required when EXPO_PUBLIC_API_STRICT=true in production"
    );
  }

  if (!configuredBaseUrl && process.env.NODE_ENV !== "test" && !hasWarnedAboutMissingBaseUrl) {
    hasWarnedAboutMissingBaseUrl = true;
    console.warn(
      "EXPO_PUBLIC_API_BASE_URL is not set; defaulting to http://localhost:8000"
    );
  }

  return trimTrailingSlash(configuredBaseUrl || DEFAULT_API_BASE_URL);
}

export function getApiPrefix() {
  const configuredPrefix = process.env.EXPO_PUBLIC_API_PREFIX;
  return trimTrailingSlash(ensureLeadingSlash(configuredPrefix || DEFAULT_API_PREFIX));
}

export default function getApiUrl(path: string) {
  return `${getApiBaseUrl()}${getApiPrefix()}${normalizePath(path)}`;
}