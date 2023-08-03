let ctrl;
let requestInProgress;

const sendLongCommand = async (cmd) => {
    ctrl?.abort();
    ctrl = new AbortController();
    const signal = ctrl.signal;
    let first = true;
    while(true) {
        await fetch(`/api/${cmd}`, { method: 'POST'});
        if (first) {
            await new Promise(res => setTimeout(res, 500)); first = false
        }
        if (signal.aborted) {
            break;
        }
    }
}

const sendCommand = async (cmd, arg) => {
    if (requestInProgress) {
        return;
    }
    requestInProgress = true;
    document.body.classList.add('loading');
    const response = await (await fetch(`/api/${ cmd }${ arg ? `/${ arg }` : '' }`, { method: 'POST'})).json();
    document.body.classList.remove('loading');
    requestInProgress = false;
    Array.from(document.querySelectorAll('button')).forEach(btn => {
        const { dataset: {command, commandArg}, classList } = btn;
        if (command === cmd && commandArg === arg) {
            if (response.ok) {
                classList.add('on');
            } else {
                classList.remove('on')
            }
        } else {
            if (cmd === 'power') {
                btn.disabled = !response.ok;
                if (response.ok) {
                    if (command === 'source' && commandArg === response.source) {
                        classList.add('on');
                    } else if (command === 'mute' && response.mute) {
                        classList.add('on');
                    }
                } else {
                    classList.remove('on')
                }
            } else if (cmd === 'source' && command === 'source') {
                classList.remove('on');
            }
        }
    });
}

window.addEventListener('load', (event) => {
    const startEvent = 'ontouchstart' in window ? 'touchstart' : 'mousedown';
    const endEvent = 'ontouchstart' in window ? 'touchend' : 'mouseup';

    Array.from(document.querySelectorAll('button')).forEach(
        btn => {
            btn.addEventListener(startEvent, (event) => {
                event.preventDefault();
                if (!btn.disabled && !requestInProgress) {
                    btn.classList.add('click');
                    const { command, commandType, commandArg } = btn.dataset;
                    if (commandType === 'long') {
                        sendLongCommand(command);
                    } else {
                        sendCommand(command, commandArg);
                    }
                }
            });
            btn.addEventListener(endEvent, (event) => {
                event.preventDefault();
                if (!btn.disabled) {
                    btn.classList.remove('click');
                }
                ctrl?.abort();
            });
        }
    );
});
