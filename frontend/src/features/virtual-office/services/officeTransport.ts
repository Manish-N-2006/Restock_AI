import { ServerMessage, ClientMessage } from '../types/office';
import { resolveWsUrl } from '../../../api/config';
import { AUTH_UNAUTHORIZED_EVENT } from '../../../api/client';

export type MessageListener = (msg: ServerMessage) => void;
export type ConnectionListener = (connected: boolean) => void;

class OfficeTransport {
  private ws: WebSocket | null = null;
  private messageListeners = new Set<MessageListener>();
  private connectionListeners = new Set<ConnectionListener>();
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private heartbeatTimer: ReturnType<typeof setInterval> | null = null;
  private reconnectAttempts = 0;
  private isConnecting = false;
  private isManuallyClosed = false;
  private url: string;

  constructor() {
    this.url = resolveWsUrl();
  }

  public connect(customUrl?: string) {
    if (customUrl) {
      this.url = customUrl;
    } else if (!this.url) {
      this.url = resolveWsUrl();
    }

    if (!this.url) return;

    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    this.isManuallyClosed = false;
    this.isConnecting = true;

    try {
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        console.log('[OfficeTransport] WebSocket connected to', this.url);
        this.notifyConnection(true);
        this.send({ type: 'webviewReady' });
        this.startHeartbeat();
      };

      this.ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as ServerMessage;
          this.notifyMessage(msg);
        } catch (e) {
          console.warn('[OfficeTransport] Failed to parse message', e);
        }
      };

      this.ws.onclose = (event) => {
        this.isConnecting = false;
        this.stopHeartbeat();
        this.notifyConnection(false);
        if (event.code === 1008) {
          this.isManuallyClosed = true;
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
          }
          return;
        }
        if (!this.isManuallyClosed) {
          this.scheduleReconnect();
        }
      };

      this.ws.onerror = (err) => {
        console.warn('[OfficeTransport] WebSocket error', err);
        this.isConnecting = false;
      };
    } catch (err) {
      console.warn('[OfficeTransport] Connection exception', err);
      this.isConnecting = false;
      this.stopHeartbeat();
      this.scheduleReconnect();
    }
  }

  public disconnect() {
    this.isManuallyClosed = true;
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
    this.notifyConnection(false);
  }

  public send(msg: ClientMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  public onMessage(listener: MessageListener): () => void {
    this.messageListeners.add(listener);
    return () => this.messageListeners.delete(listener);
  }

  public onConnection(listener: ConnectionListener): () => void {
    this.connectionListeners.add(listener);
    listener(this.isConnected());
    return () => this.connectionListeners.delete(listener);
  }

  public isConnected(): boolean {
    return Boolean(this.ws && this.ws.readyState === WebSocket.OPEN);
  }

  public getIsConnecting(): boolean {
    return this.isConnecting;
  }

  private startHeartbeat() {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.send({ type: 'ping' });
      }
    }, 25000);
  }

  private stopHeartbeat() {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private notifyMessage(msg: ServerMessage) {
    for (const listener of this.messageListeners) {
      try {
        listener(msg);
      } catch (err) {
        console.error('[OfficeTransport] Error in listener', err);
      }
    }
  }

  private notifyConnection(connected: boolean) {
    for (const listener of this.connectionListeners) {
      try {
        listener(connected);
      } catch (err) {
        console.error('[OfficeTransport] Error in connection listener', err);
      }
    }
  }

  private scheduleReconnect() {
    if (this.reconnectTimer || this.isManuallyClosed) return;
    const delayMs = Math.min(2000 * Math.pow(1.5, this.reconnectAttempts), 15000);
    this.reconnectAttempts += 1;
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      console.log(`[OfficeTransport] Reconnecting (attempt ${this.reconnectAttempts})...`);
      this.connect();
    }, delayMs);
  }
}

export const officeTransport = new OfficeTransport();
export const transport = officeTransport;
