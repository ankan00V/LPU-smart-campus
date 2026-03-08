/**
 * @typedef {Object} RealtimeEventPayload
 * @property {string} id
 * @property {string} event_type
 * @property {string} created_at
 * @property {Record<string, any>} payload
 * @property {Record<string, any>} actor
 * @property {string[]} topics
 * @property {string[]} scopes
 * @property {string} source
 */

/**
 * @typedef {Object} RealtimeBusController
 * @property {() => void} connect
 * @property {() => void} disconnect
 * @property {(handler: (event: RealtimeEventPayload) => void) => () => void} subscribe
 * @property {() => boolean} isConnected
 */

/**
 * @typedef {Object} RealtimeBusOptions
 * @property {string} url
 * @property {(state: string, detail?: string) => void} [onStatus]
 * @property {(message: string) => void} [onLog]
 * @property {number} [maxReconnectDelayMs]
 */

/**
 * Creates a lightweight SSE bus with auto-reconnect and typed subscribers.
 *
 * @param {RealtimeBusOptions} options
 * @returns {RealtimeBusController}
 */
export function createRealtimeBus(options) {
  const url = String(options?.url || '/events/stream').trim() || '/events/stream';
  const onStatus = typeof options?.onStatus === 'function' ? options.onStatus : () => {};
  const onLog = typeof options?.onLog === 'function' ? options.onLog : () => {};
  const maxReconnectDelayMs = Math.max(2000, Number(options?.maxReconnectDelayMs || 20000));

  /** @type {EventSource | null} */
  let source = null;
  /** @type {Set<(event: RealtimeEventPayload) => void>} */
  const subscribers = new Set();
  let connected = false;
  let manualClose = false;
  let reconnectDelay = 1000;
  let reconnectTimer = null;

  const clearReconnect = () => {
    if (!reconnectTimer) {
      return;
    }
    window.clearTimeout(reconnectTimer);
    reconnectTimer = null;
  };

  const notify = (state, detail = '') => {
    onStatus(state, detail);
    if (detail) {
      onLog(`Realtime bus ${state}: ${detail}`);
      return;
    }
    onLog(`Realtime bus ${state}`);
  };

  const emit = (event) => {
    for (const handler of subscribers) {
      try {
        handler(event);
      } catch (_) {
        // Subscriber errors must not break other handlers.
      }
    }
  };

  const scheduleReconnect = () => {
    if (manualClose) {
      return;
    }
    clearReconnect();
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null;
      connect();
    }, reconnectDelay);
    reconnectDelay = Math.min(maxReconnectDelayMs, Math.floor(reconnectDelay * 1.6));
  };

  const closeSource = () => {
    if (!source) {
      return;
    }
    source.close();
    source = null;
    connected = false;
  };

  const handleMessage = (rawEvent) => {
    if (!rawEvent?.data) {
      return;
    }
    let parsed;
    try {
      parsed = JSON.parse(String(rawEvent.data));
    } catch (_) {
      return;
    }
    if (!parsed || typeof parsed !== 'object') {
      return;
    }
    emit(parsed);
  };

  const connect = () => {
    if (source) {
      return;
    }
    manualClose = false;
    clearReconnect();

    try {
      source = new EventSource(url, { withCredentials: true });
    } catch (error) {
      notify('error', String(error?.message || 'Failed to construct EventSource'));
      scheduleReconnect();
      return;
    }

    source.onopen = () => {
      connected = true;
      reconnectDelay = 1000;
      notify('connected');
    };

    source.onmessage = (event) => {
      handleMessage(event);
    };

    source.onerror = () => {
      connected = false;
      notify('disconnected', 'stream dropped; retrying');
      closeSource();
      scheduleReconnect();
    };
  };

  const disconnect = () => {
    manualClose = true;
    clearReconnect();
    closeSource();
    notify('disconnected', 'manual');
  };

  const subscribe = (handler) => {
    if (typeof handler !== 'function') {
      return () => {};
    }
    subscribers.add(handler);
    return () => {
      subscribers.delete(handler);
    };
  };

  const isConnected = () => connected;

  return {
    connect,
    disconnect,
    subscribe,
    isConnected,
  };
}
