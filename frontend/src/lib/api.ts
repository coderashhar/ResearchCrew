import { headers } from "next/headers";

import type { SavedRun } from "./types";

/**
 * Absolute base for server-side fetches. On Vercel the services share a
 * domain, so the incoming request's host is the API's host too.
 */
async function baseUrl(): Promise<string> {
  if (process.env.API_PROXY) return process.env.API_PROXY;

  const list = await headers();
  const host = list.get("x-forwarded-host") ?? list.get("host") ?? "localhost:3000";
  const protocol = list.get("x-forwarded-proto") ?? (host.startsWith("localhost") ? "http" : "https");
  return `${protocol}://${host}`;
}

export async function fetchRun(id: string): Promise<SavedRun | null> {
  const response = await fetch(`${await baseUrl()}/api/runs/${id}`, { cache: "no-store" });
  if (response.status === 404) return null;
  if (!response.ok) throw new Error(`The server returned ${response.status}.`);
  return (await response.json()) as SavedRun;
}
