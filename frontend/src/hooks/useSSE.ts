import { useEffect, useRef, useCallback } from "react";
import { authApi } from "@/api/auth";
import type { SSEEventType } from "@/types";

interface SSECallbacks {
  onSubAgentStart?: (data: Record<string, unknown>) => void;
  onSubAgentRound?: (data: Record<string, unknown>) => void;
  onSubAgentComplete?: (data: Record<string, unknown>) => void;
  onSubAgentFail?: (data: Record<string, unknown>) => void;
  onAggregationStart?: (data: Record<string, unknown>) => void;
  onReportComplete?: (data: Record<string, unknown>) => void;
  onError?: (data: Record<string, unknown>) => void;
  onPlanConfirmed?: (data: Record<string, unknown>) => void;
}

const HEARTBEAT_TIMEOUT = 30_000; // 30 seconds no event → reconnect
const HEARTBEAT_CHECK_INTERVAL = 10_000; // Check every 10 seconds
const MAX_RECONNECT_ATTEMPTS = 10; // Max reconnect attempts before giving up

export function useSSE(researchId: string | null, callbacks: SSECallbacks) {
  const eventSourceRef = useRef<EventSource | null>(null);
  const callbacksRef = useRef(callbacks);
  callbacksRef.current = callbacks;
  const reconnectTimeoutRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);
  const heartbeatCheckRef = useRef<ReturnType<typeof setInterval> | undefined>(undefined);
  const reconnectAttemptRef = useRef(0);
  const isUnmountedRef = useRef(false);
  const lastEventTimeRef = useRef(Date.now());

  const scheduleReconnect = useCallback(() => {
    if (isUnmountedRef.current) return;
    if (reconnectAttemptRef.current >= MAX_RECONNECT_ATTEMPTS) return; // Give up after max attempts
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    const attempt = reconnectAttemptRef.current;
    const delay = Math.min(1000 * Math.pow(2, attempt), 30000);
    reconnectAttemptRef.current = attempt + 1;
    reconnectTimeoutRef.current = setTimeout(() => {
      if (!isUnmountedRef.current) connect();
    }, delay);
  }, []);

  const connect = useCallback(async () => {
    if (!researchId || isUnmountedRef.current) return;

    try {
      // Get ticket first
      const { ticket } = await authApi.getTicket();

      const url = `/api/v1/research/${researchId}/stream?ticket=${ticket}`;
      const es = new EventSource(url);
      eventSourceRef.current = es;
      lastEventTimeRef.current = Date.now();

      const eventTypes: SSEEventType[] = [
        "sub_agent_start",
        "sub_agent_round",
        "sub_agent_complete",
        "sub_agent_fail",
        "report_complete",
        "error",
        "heartbeat",
        "plan_confirm",
      ];

      const handlerMap: Record<SSEEventType, keyof SSECallbacks | undefined> = {
        sub_agent_start: "onSubAgentStart",
        sub_agent_round: "onSubAgentRound",
        sub_agent_complete: "onSubAgentComplete",
        sub_agent_fail: "onSubAgentFail",
        aggregation_start: "onAggregationStart",
        report_complete: "onReportComplete",
        error: "onError",
        heartbeat: undefined,
        plan_confirm: "onPlanConfirmed",
      };

      for (const eventType of eventTypes) {
        es.addEventListener(eventType, (event: MessageEvent) => {
          lastEventTimeRef.current = Date.now();
          try {
            const data = JSON.parse(event.data);
            const cbKey = handlerMap[eventType];
            if (cbKey) {
              const cb = callbacksRef.current[cbKey];
              if (cb) (cb as (d: Record<string, unknown>) => void)(data);
            }
          } catch {
            // ignore parse errors
          }
        });
      }

      es.onopen = () => {
        reconnectAttemptRef.current = 0;

        // Start heartbeat check
        if (heartbeatCheckRef.current) clearInterval(heartbeatCheckRef.current);
        heartbeatCheckRef.current = setInterval(() => {
          if (Date.now() - lastEventTimeRef.current > HEARTBEAT_TIMEOUT) {
            // No events for 30s → assume dead connection
            scheduleReconnect();
          }
        }, HEARTBEAT_CHECK_INTERVAL);
      };

      es.onerror = () => {
        scheduleReconnect();
      };
    } catch {
      // Failed to get ticket - retry with backoff
      scheduleReconnect();
    }
  }, [researchId, scheduleReconnect]);

  useEffect(() => {
    isUnmountedRef.current = false;
    connect();

    return () => {
      isUnmountedRef.current = true;
      eventSourceRef.current?.close();
      eventSourceRef.current = null;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (heartbeatCheckRef.current) {
        clearInterval(heartbeatCheckRef.current);
      }
    };
  }, [connect]);
}
