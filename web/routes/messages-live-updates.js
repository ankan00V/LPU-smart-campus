/**
 * @typedef {Object} RouteModuleContext
 * @property {{subscribe: (handler: (event: any) => void) => () => void}} realtimeBus
 * @property {() => string} getUserRole
 * @property {() => string} getActiveModule
 * @property {() => boolean} isSupportDeskOpen
 * @property {(reason: string) => Promise<void>} refreshSupportDesk
 * @property {(reason: string) => Promise<void>} refreshStudentMessages
 * @property {(reason: string) => Promise<void>} refreshRemedialMessages
 */

let unsub = null;
let active = false;
let pendingTimer = null;
let inFlight = false;
let reasonCache = '';

function shouldHandleEvent(eventType) {
  const type = String(eventType || '').trim().toLowerCase();
  return (
    type.startsWith('messages.')
    || type.startsWith('rms.thread.')
    || type === 'rms.attendance.updated'
  );
}

function scheduleRefresh(context, reason) {
  reasonCache = reason || reasonCache || 'event';
  if (pendingTimer) {
    return;
  }
  pendingTimer = window.setTimeout(async () => {
    pendingTimer = null;
    if (inFlight) {
      scheduleRefresh(context, reasonCache);
      return;
    }
    inFlight = true;
    try {
      const role = context.getUserRole();
      const moduleKey = context.getActiveModule();
      if (role === 'student') {
        await context.refreshStudentMessages(reasonCache);
        if (moduleKey === 'remedial' || moduleKey === 'attendance') {
          await context.refreshRemedialMessages(reasonCache);
        }
      }
      if (role === 'student' || role === 'faculty') {
        await context.refreshSupportDesk(reasonCache);
      }
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
  reasonCache = '';
}
