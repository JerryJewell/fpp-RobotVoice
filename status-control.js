(() => {
  function init() {
    const anchor = document.getElementById('playerStatusTop');
    if (!anchor || document.getElementById('rv-status-switch')) return;
    const box = document.createElement('div');
    box.id = 'rv-status-switch';
    box.className = 'alert alert-secondary d-flex flex-wrap align-items-center gap-2';
    const label = document.createElement('strong');
    label.textContent = "Chad's Voice Changer";
    const status = document.createElement('span');
    status.textContent = 'Checking…';
    status.setAttribute('role', 'status');
    const buttons = ['on', 'off'].map(action => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'btn btn-sm ' + (action === 'on' ? 'btn-primary' : 'btn-secondary');
      button.textContent = action === 'on' ? 'Voice On' : 'Voice Off';
      button.disabled = true;
      button.addEventListener('click', () => refresh(action));
      return button;
    });
    box.append(label, ...buttons, status);
    anchor.before(box);
    const url = 'plugin.php?plugin=fpp-RobotVoice&page=live.php&nopage=1';
    let busy = false;
    let message = '';
    let pending = null;
    async function refresh(action) {
      if (busy) { if (action) pending = action; return; }
      if (!action && document.hidden) return;
      busy = true;
      if (action) {
        buttons.forEach(button => { button.disabled = true; });
        message = '';
      }
      try {
        const response = await fetch(url, action ? {
          method: 'POST',
          headers: {'X-RobotVoice-Control': '1'},
          body: new URLSearchParams({action})
        } : {cache: 'no-store'});
        // Older core versions may include an FPP discovery comment.
        const raw = (await response.text()).trim().replace(/^<!--[^]*?-->\s*/, '');
        const result = JSON.parse(raw);
        if (!response.ok || result.error) throw new Error(result.error || 'Control unavailable.');
        let engine;
        if (result.on) engine = result.engine === 'disabled' ? 'Starting…' : result.engine;
        else engine = result.engine === 'running' ? 'Stopping…' : 'Off';
        status.textContent = message || (result.on && result.detail ? engine + ': ' + result.detail : engine);
        buttons[0].disabled = result.on;
        buttons[1].disabled = !result.on;
      } catch (error) {
        message = action ? error.message : '';
        status.textContent = message || 'Voice controls unavailable.';
        buttons.forEach(button => { button.disabled = !action; });
      } finally {
        busy = false;
        if (pending) {
          const next = pending;
          pending = null;
          refresh(next);
        }
      }
    }
    refresh();
    setInterval(() => refresh(), 2000);
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init, {once:true});
  else init();
})();
