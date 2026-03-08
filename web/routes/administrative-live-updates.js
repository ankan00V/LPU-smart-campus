/**
 * @typedef {Object} RouteModuleContext
 * @property {{subscribe: (handler: (event: any) => void) => () => void}} realtimeBus
 * @property {() => string} getActiveModule
 * @property {() => string} getUserRole
 * @property {() => Promise<void>} refreshAdministrative
 */

let active = false;
let unsub = null;
let pendingTimer = null;
let inFlight = false;
let lastReason = '';

function shouldHandleEvent(eventType) {
  const type = String(eventType || '').trim().toLowerCase();
  return (
    type.startsWith('attendance.')
    || type.startsWith('messages.')
    || type.startsWith('rms.')
    || type.startsWith('food.')
    || type.startsWith('remedial.')
    || type.startsWith('identity.')
    || type.startsWith('admin.')
  );
}

function scheduleRefresh(context, reason) {
  lastReason = reason || lastReason || 'administrative.event';
  if (pendingTimer) {
    return;
  }
  pendingTimer = window.setTimeout(async () => {
    pendingTimer = null;
    if (inFlight) {
      scheduleRefresh(context, lastReason);
      return;
    }
    if (context.getUserRole() !== 'admin' || context.getActiveModule() !== 'administrative') {
      return;
    }
    inFlight = true;
    try {
      await context.refreshAdministrative(lastReason);
    } catch (_) {
      // Keep route worker silent on transient refresh failures.
    } finally {
      inFlight = false;
    }
  }, 250);
}

/**
 * @param {RouteModuleContext} context
 */
export function onActivate(context) {
  if (active || !context?.realtimeBus || typeof context.refreshAdministrative !== 'function') {
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
