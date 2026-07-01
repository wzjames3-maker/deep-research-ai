import client from "./client";
import type { LoginResponse, MeResponse, TicketResponse } from "@/types";

export const authApi = {
  async login(
    username: string,
    password: string,
    rememberMe = false
  ): Promise<LoginResponse> {
    const resp = await client.post("/auth/login", {
      username,
      password,
      rememberMe: rememberMe,
    });
    return resp.data;
  },

  async register(username: string, password: string): Promise<LoginResponse> {
    const resp = await client.post("/auth/register", { username, password });
    return resp.data;
  },

  async getMe(): Promise<MeResponse> {
    const resp = await client.get("/auth/me");
    return resp.data;
  },

  async refreshToken(): Promise<{ token: string }> {
    const resp = await client.post("/auth/refresh");
    return resp.data;
  },

  async getTicket(): Promise<TicketResponse> {
    const resp = await client.post("/auth/ticket");
    return resp.data;
  },
};
