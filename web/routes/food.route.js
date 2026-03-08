/**
 * @typedef {Object} RouteModuleContext
 * @property {{subscribe: (handler: (event: any) => void) => () => void}} realtimeBus
 * @property {() => string} getActiveModule
 * @property {() => string} getUserRole
 * @property {() => Promise<void>} ensureFoodDeferredAssets
 * @property {() => Promise<void>} refreshFood
 */

let active = false;
let unsub = null;
let pendingTimer = null;
let inFlight = false;
let lastReason = '';

function shouldHandleEvent(eventType) {
  return String(eventType || '').trim().toLowerCase().startsWith('food.');
}

function scheduleRefresh(context, reason) {
  lastReason = reason || lastReason || 'food.event';
  if (pendingTimer) {
    return;
  }
  pendingTimer = window.setTimeout(async () => {
    pendingTimer = null;
    if (inFlight) {
      scheduleRefresh(context, lastReason);
      return;
    }
    if (context.getActiveModule() !== 'food') {
      return;
    }
    inFlight = true;
    try {
      await context.refreshFood(lastReason);
    } catch (_) {
      // Module-level status UI handles errors.
    } finally {
      inFlight = false;
    }
  }, 250);
}

/**
 * @param {RouteModuleContext} context
 */
export function onActivate(context) {
  if (active) {
    return;
  }
  active = true;
  if (context && typeof context.ensureFoodDeferredAssets === 'function') {
    void context.ensureFoodDeferredAssets().catch(() => {
      // Defer failure handling to module-level UI.
    });
  }
  if (context?.realtimeBus && typeof context.refreshFood === 'function') {
    unsub = context.realtimeBus.subscribe((event) => {
      const eventType = String(event?.event_type || '').trim().toLowerCase();
      if (!shouldHandleEvent(eventType)) {
        return;
      }
      scheduleRefresh(context, eventType);
    });
  }
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
