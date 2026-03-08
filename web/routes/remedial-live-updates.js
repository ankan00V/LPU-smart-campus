/**
 * @typedef {Object} RouteModuleContext
 * @property {{subscribe: (handler: (event: any) => void) => () => void}} realtimeBus
 * @property {() => string} getActiveModule
 * @property {() => string} getUserRole
 * @property {() => Promise<void>} refreshRemedialModule
 */

let active = false;
let unsub = null;
let pendingTimer = null;
let inFlight = false;
let lastReason = '';

function shouldHandleEvent(eventType) {
  return String(eventType || '').trim().toLowerCase().startsWith('remedial.');
}

function scheduleRefresh(context, reason) {
  lastReason = reason || lastReason || 'remedial.event';
  if (pendingTimer) {
    return;
  }
  pendingTimer = window.setTimeout(async () => {
    pendingTimer = null;
    if (inFlight) {
      scheduleRefresh(context, lastReason);
      return;
    }
    if (context.getActiveModule() !== 'remedial') {
      return;
    }
    inFlight = true;
    try {
      await context.refreshRemedialModule(lastReason);
    } catch (_) {
      // Route worker stays quiet on background refresh failures.
    } finally {
      inFlight = false;
    }
  }, 200);
}

/**
 * @param {RouteModuleContext} context
 */
export function onActivate(context) {
  if (active || !context?.realtimeBus || typeof context.refreshRemedialModule !== 'function') {
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
