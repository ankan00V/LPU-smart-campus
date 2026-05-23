/**
 * @typedef {Object} RouteModuleContext
 * @property {{subscribe: (handler: (event: any) => void) => () => void}} realtimeBus
 * @property {() => string} getUserRole
 * @property {() => string} getActiveModule
 * @property {(reason: string) => Promise<void>} refreshRms
 */

let unsub = null;
let active = false;
let pendingTimer = null;
let inFlight = false;
let lastReason = '';

function shouldHandleEvent(eventType) {
  const type = String(eventType || '').trim().toLowerCase();
  return (
    type.startsWith('rms.')
    || type === 'messages.support.updated'
    || type === 'messages.announcement.sent'
  );
}

function scheduleRefresh(context, reason) {
  lastReason = reason || lastReason || 'event';
  if (pendingTimer) {
    return;
  }
  pendingTimer = window.setTimeout(async () => {
    pendingTimer = null;
    if (inFlight) {
      scheduleRefresh(context, lastReason);
      return;
    }
    inFlight = true;
    try {
      const role = context.getUserRole();
      if (role !== 'admin' && role !== 'faculty') {
        return;
      }
      if (context.getActiveModule() !== 'rms') {
        return;
      }
      await context.refreshRms(lastReason);
    } catch (_) {
      // Keep silent in background route worker.
    } finally {
      inFlight = false;
    }
  }, 200);
}

/**
 * @param {RouteModuleContext} context
 */
export function onActivate(context) {
  if (active || !context?.realtimeBus) {
    return;
  }
  active = true;
  unsub = context.realtimeBus.subscribe((event) => {
    const eventType = String(event?.event_type || '').trim().toLowerCase();
    if (!shouldHandleEvent(eventType)) {
      return;
    }
    scheduleRefresh(context, eventType);
  });
}

export function onDeactivate() {
  active = false;
  if (typeof unsub === 'function') {
    unsub();
  }
  unsub = null;
  if (pendingTimer) {
    window.clearTimeout(pendingTimer);
    pendingTimer = null;
  }
  inFlight = false;
  lastReason = '';
}
