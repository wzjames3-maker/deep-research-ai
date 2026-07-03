import client from "./client";
import type {
  Research,
  ResearchReport,
  ResearchTemplate,
  HistoryResponse,
  TokenStats,
} from "@/types";

export const researchApi = {
  async create(topic: string, template: ResearchTemplate): Promise<Research> {
    const resp = await client.post("/research/new", { topic, template });
    return resp.data;
  },

  async get(id: string): Promise<Research> {
    const resp = await client.get(`/research/${id}`);
    return resp.data;
  },

  async revise(id: string, feedback: string): Promise<Research> {
    const resp = await client.post(`/research/${id}/plan/revise`, { feedback });
    return resp.data;
  },

  async confirm(id: string): Promise<{ researchId: string; status: string; streamUrl: string }> {
    const resp = await client.post(`/research/${id}/plan/confirm`);
    return resp.data;
  },

  async cancel(id: string): Promise<void> {
    await client.post(`/research/${id}/cancel`);
  },

  async getReport(id: string): Promise<ResearchReport> {
    const resp = await client.get(`/research/${id}/report`);
    return resp.data;
  },

  async exportPdf(id: string): Promise<Blob> {
    const resp = await client.get(`/research/${id}/export/pdf`, {
      responseType: "blob",
    });
    return resp.data;
  },

  async listHistory(
    page = 1,
    pageSize = 20
  ): Promise<HistoryResponse> {
    const resp = await client.get("/research/history", {
      params: { page, pageSize },
    });
    return resp.data;
  },

  async delete(id: string): Promise<void> {
    await client.delete(`/research/${id}`);
  },

  async getTokenStats(): Promise<TokenStats> {
    const resp = await client.get("/research/stats/tokens");
    return resp.data;
  },
};
